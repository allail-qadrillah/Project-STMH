"""Operators, recorded streams, infeasible continuation, full five-VM acceptance gate."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import yaml

from src.config import load_config
from src.crossover import uniform_crossover
from src.data_loader import load_workload
from src.dynamic_experiment import run_dynamic
from src.evaluation import evaluate_placement
from src.experiment import run_experiment
from src.fitness import calculate_fitness
from src.genetic_algorithm import initialize_population, reproduce, run_ga
from src.randomness import make_stream
from src.reporting import dynamic_summary
from src.selection import elite_indices, tournament


CONFIG = Path(__file__).resolve().parents[1] / "configs/experiment_config.yaml"


class GATests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG)

    def test_reject_unapproved_seeds_streams_and_policies(self):
        original = yaml.safe_load(CONFIG.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            for section, key, value in (("project", "random_seeds", 30), ("project", "master_seed", 43),
                                        ("project", "rng", "MT19937"),
                                        ("project", "stream_ids", {"static_ga": 0}),
                                        ("methodology", "tournament_replacement", False),
                                        ("methodology", "warm_start_inherited_count", 2)):
                config = copy.deepcopy(original)
                config[section][key] = value
                path.write_text(yaml.safe_dump(config))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    load_config(path)

    def test_tournament_replacement_and_random_equal_best_participant(self):
        rng = Mock()
        rng.integers.return_value = np.array([0, 0, 1])
        rng.choice.return_value = 1
        self.assertEqual(tournament([2, 2, 1], rng, 3), 1)
        rng.integers.assert_called_once_with(0, 3, size=3)
        np.testing.assert_equal(rng.choice.call_args.args[0], [0, 0, 1])
        rng.integers.return_value = np.array([0, 1, 2])
        rng.choice.return_value = 2
        self.assertEqual(tournament([1, 2, 3], rng, 3), 2)
        np.testing.assert_equal(rng.choice.call_args.args[0], [2])
        real = np.random.Generator(np.random.PCG64(42))
        selected = [tournament([2, 2, 2], real, 3) for _ in range(100)]
        self.assertEqual(set(selected), {0, 1, 2})

    def test_uniform_crossover_complementarity_trial_and_copies(self):
        a = np.ones(1000, dtype=int)
        b = np.full(1000, 12, dtype=int)
        rng = np.random.Generator(np.random.PCG64(42))
        c, d = uniform_crossover(a, b, rng, 1)
        np.testing.assert_equal(c + d, a + b)
        self.assertEqual(set(c), {1, 12})
        self.assertEqual(c.shape, a.shape)
        c, d = uniform_crossover(a, b, rng, 0)
        np.testing.assert_equal(c, a)
        np.testing.assert_equal(d, b)
        c[0] = 3
        self.assertEqual(a[0], 1)
        mock = Mock()
        mock.random.return_value = 0.9
        uniform_crossover(a, b, mock, 0.8)
        mock.random.assert_called_once_with()
        for x, y, p in (([1], [1, 2], 0.8), ([1.0], [2.0], 0.8), ([1], [2], -1)):
            with self.assertRaises(ValueError):
                uniform_crossover(x, y, rng, p)

    def test_random_elitism_and_exact_population_size(self):
        rng = np.random.Generator(np.random.PCG64(42))
        population = np.tile(np.arange(1, 13), (50, 1))
        population[:, 0] = np.arange(50) % 12 + 1
        fitness = np.arange(50, dtype=float)
        offspring = reproduce(population, fitness, self.config, rng)
        self.assertEqual(offspring.shape, (50, 12))
        np.testing.assert_equal(offspring[:2], population[[49, 48]])
        self.assertTrue(np.all((offspring >= 1) & (offspring <= 12)))
        winners = {tuple(elite_indices(np.ones(50), rng, 2)) for _ in range(30)}
        self.assertGreater(len(winners), 1)
        elite = elite_indices([3, 1, 3, 2], rng, 2)
        self.assertEqual(set(elite), {0, 2})

    def test_warm_population_one_inherited_plus_49_independent_draws(self):
        inherited = np.full(7, 5, dtype=int)
        rng, _ = make_stream(self.config, "warm_start", 2)
        actual = initialize_population(7, self.config, rng, inherited)
        replay, _ = make_stream(self.config, "warm_start", 2)
        expected_random = replay.integers(1, 13, size=(49, 7))
        self.assertEqual(actual.shape, (50, 7))
        np.testing.assert_equal(actual[0], inherited)
        np.testing.assert_equal(actual[1:], expected_random)
        actual[0, 0] = 12
        np.testing.assert_equal(inherited, 5)

    def test_streams_reproducible_order_independent_and_distinct(self):
        roles = [("static_baseline", 0), ("static_ga", 0), ("dynamic_initial", 0),
                 ("cold_start", 1), ("warm_start", 1), ("cold_start", 2)]
        draws = {}
        for role, window in roles:
            rng, record = make_stream(self.config, role, window)
            self.assertEqual(record["master_seed"], 42)
            self.assertEqual(record["bit_generator"], "PCG64")
            draws[role, window] = rng.integers(0, 2**31, 100)
        for role, window in reversed(roles):
            rng, _ = make_stream(self.config, role, window)
            np.testing.assert_equal(rng.integers(0, 2**31, 100), draws[role, window])
        self.assertEqual(len({a.tobytes() for a in draws.values()}), len(roles))

    def test_best_so_far_first_seen_and_101_evaluations(self):
        # All placements tie on one active PM; mutation/crossover cannot improve.
        population = np.repeat((np.arange(50) % 12 + 1)[:, None], 5, axis=1)
        config = copy.deepcopy(self.config)
        config["genetic_algorithm"]["mutation"]["per_gene_probability"] = 0
        config["genetic_algorithm"]["crossover"]["probability"] = 0
        rng, _ = make_stream(config, "static_ga")
        with patch("src.genetic_algorithm.initialize_population", return_value=population.copy()):
            result = run_ga(np.full((3, 5), 0.4), config, rng, "static")
        self.assertEqual([h["generation"] for h in result["history"]], list(range(101)))
        self.assertTrue(all(h["population_size"] == 50 for h in result["history"]))
        np.testing.assert_equal(result["best_chromosomes"], np.ones((101, 5), dtype=int))
        self.assertAlmostEqual(result["metrics"]["fitness"], 1 + 1 / (1 + 1 / 12))
        np.testing.assert_equal(result["loads_vcpu"][:, 0], 2)

    def test_complete_ga_replays_exactly(self):
        config = copy.deepcopy(self.config)
        config["genetic_algorithm"]["max_generations"] = 5
        demand = np.full((12, 7), 0.4)
        reference = np.arange(7) + 1
        a = run_ga(demand, config, make_stream(config, "cold_start", 1)[0], "dynamic", reference)
        b = run_ga(demand, config, make_stream(config, "cold_start", 1)[0], "dynamic", reference)
        for key in ("placement", "loads_vcpu", "initial_population", "best_chromosomes"):
            np.testing.assert_equal(a[key], b[key])
        self.assertEqual(a["history"], b["history"])
        self.assertEqual(a["metrics"], b["metrics"])

    def test_infeasible_windows_continue_with_selected_minimum_violation(self):
        config = copy.deepcopy(self.config)
        config["genetic_algorithm"]["max_generations"] = 1
        # 169 vCPU exceeds total safe capacity 153.6; no chromosome can be feasible.
        demand = np.ones((288, 169))
        results = run_dynamic(demand, config)
        for method in ("cold_start", "warm_start"):
            windows = results[method]
            self.assertEqual(len(windows), 24)
            for index, result in enumerate(windows):
                self.assertEqual(result["metrics"]["status"], "INFEASIBLE")
                expected_reference = results["initial_placement"] if index == 0 else windows[index - 1]["placement"]
                np.testing.assert_equal(result["reference"], expected_reference)
                if method == "warm_start" and index > 0:
                    np.testing.assert_equal(result["initial_population"][0], expected_reference)
                initial_v = [evaluate_placement(demand[:12], p, config, expected_reference)[0]["normalized_cpu_violation"]
                             for p in result["initial_population"]]
                self.assertLessEqual(result["metrics"]["normalized_cpu_violation"], min(initial_v))
                self.assertGreater(result["metrics"]["normalized_cpu_violation"], 0)
            summary = dynamic_summary(method, windows, 169, 42)
            self.assertEqual(summary["infeasible_windows"], 24)
            self.assertEqual(summary["status"], "INFEASIBLE")
            self.assertEqual(summary["transitions"], 24)
            self.assertAlmostEqual(summary["migration_rate"], summary["migration_count"] / (169 * 24))

    def test_five_vm_full_pipeline_100_updates_24_windows_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "input"
            data.mkdir()
            for index, percentage in enumerate((40, 60, 20, 30, 50)):
                (data / f"vm{index}").write_text(f"{percentage}\n" * 288)
            config = copy.deepcopy(self.config)
            config["dataset"]["path"] = str(data)
            config["dataset"]["expected_vm_count"] = 5
            matrix, ids, manifest, actions = load_workload(config)
            output = root / "experiment"
            results = run_experiment(config, matrix, ids, manifest, actions, output)
            self.assertEqual(matrix.shape, (288, 5))
            static = results["static"]
            experiments = output / "experiments"
            all_results = [(experiments / "static" / "ga", static["ga"], matrix, static["baseline"]["placement"], "static")]
            dynamic = results["dynamic"]
            for method in ("cold_start", "warm_start"):
                self.assertEqual(len(dynamic[method]), 24)
                reference = dynamic["initial_placement"]
                for index, result in enumerate(dynamic[method]):
                    window = index + 1
                    self.assertEqual((result["sample_start"], result["sample_end"]), (index * 12 + 1, window * 12))
                    np.testing.assert_equal(result["reference"], reference)
                    replay_rng, _ = make_stream(config, method, window)
                    inherited = reference if method == "warm_start" and index > 0 else None
                    expected_initial = initialize_population(5, config, replay_rng, inherited)
                    np.testing.assert_equal(result["initial_population"], expected_initial)
                    all_results.append((experiments / "dynamic" / method / f"window_{window:02d}", result,
                                        matrix[index * 12:window * 12], reference.copy(), "dynamic"))
                    reference = result["placement"]
                with (experiments / "dynamic" / method / "per_window_metrics.csv").open() as stream:
                    self.assertEqual(len(list(csv.DictReader(stream))), 24)
                summary = dynamic_summary(method, dynamic[method], 5, 42)
                self.assertAlmostEqual(summary["migration_rate"], summary["migration_count"] / 120)
            self.assertFalse(np.array_equal(dynamic["cold_start"][0]["initial_population"],
                                            dynamic["warm_start"][0]["initial_population"]))
            for directory, result, demand, reference, mode in all_results:
                self.assertEqual(result["metrics"]["status"], "FEASIBLE")
                self.assertEqual(result["metrics"]["overload_events"], 0)
                self.assertEqual(result["initial_population"].shape, (50, 5))
                self.assertEqual(result["best_chromosomes"].shape, (101, 5))
                self.assertEqual([h["generation"] for h in result["history"]], list(range(101)))
                self.assertTrue(all(h["population_size"] == 50 for h in result["history"]))
                scores = [h["best_fitness"] for h in result["history"]]
                self.assertTrue(np.all(np.diff(scores) >= 0))
                for generation, (chromosome, history) in enumerate(zip(result["best_chromosomes"], result["history"])):
                    metrics, _ = evaluate_placement(demand, chromosome, config, reference)
                    self.assertEqual(calculate_fitness(metrics, config, mode), history["best_fitness"])
                    for key, value in metrics.items():
                        self.assertEqual(value, history[key])
                    if generation and scores[generation] == scores[generation - 1]:
                        np.testing.assert_equal(chromosome, result["best_chromosomes"][generation - 1])
                # Independent hand calculation from known 0.4+0.6+0.2+0.3+0.5 = 2 vCPU/sample.
                np.testing.assert_allclose(result["loads_vcpu"].sum(axis=1), 2)
                active = len(set(result["placement"]))
                migrations = int(np.count_nonzero(result["placement"] != reference))
                cost = active / 12 if mode == "static" else 0.70 * active / 12 + 0.30 * migrations / 5
                self.assertAlmostEqual(result["metrics"]["fitness"], 1 + 1 / (1 + cost))
                self.assertAlmostEqual(result["metrics"]["mean_active_pm_utilization_ratio"], 2 / (16 * active))
                self.assertEqual(result["metrics"]["migration_count"], migrations)
                raw = np.load(directory / "raw.npz")
                for key in ("placement", "loads_vcpu", "initial_population", "best_chromosomes"):
                    np.testing.assert_equal(raw[key], result[key])
                np.testing.assert_equal(raw["utilization_ratio"], result["loads_vcpu"] / 16)
                self.assertTrue((directory / "placement.csv").is_file())
                with (directory / "fitness_history.csv").open() as stream:
                    self.assertEqual(len(list(csv.DictReader(stream))), 101)
            self.assertEqual(json.loads((output / "summaries/execution_status.json").read_text())["status"], "COMPLETED")
            metadata = json.loads((output / "summaries/experiment_config.json").read_text())
            self.assertEqual(metadata["random_seed_list"], [42])
            self.assertEqual(metadata["run_count_per_method"], 1)
            self.assertEqual(metadata["stage"], "EXPERIMENT")
            self.assertEqual(metadata["observed_dataset"]["observed_vms"], 5)
            self.assertIn("matplotlib", metadata["environment"])
            records = json.loads((output / "summaries/random_streams.json").read_text())
            self.assertEqual(len(records), 51)
            self.assertEqual(len({tuple(r["spawn_key"]) for r in records}), 51)
            self.assertTrue(all("initial_state" in r and "final_state" in r for r in records))
            self.assertGreaterEqual(len(list((output / "visualizations").rglob("*.png"))), 23)
            for image in (output / "visualizations").rglob("*.png"):
                self.assertGreater(image.stat().st_size, 1000)
            with (output / "summaries/experiment_summary.csv").open() as stream:
                rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), 4)
                self.assertTrue(all("std" not in key for key in rows[0]))
            with self.assertRaises(FileExistsError):
                run_experiment(config, matrix, ids, manifest, actions, output)


if __name__ == "__main__":
    unittest.main()
