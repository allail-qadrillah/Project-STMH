"""Hand-calculated tests, not experiment runs or GA acceptance tests."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import yaml

from src.config import load_config
from src.consolidation_mutation import consolidate_one_pm
from src.data_loader import load_workload
from src.evaluation import evaluate_placement
from src.fitness import calculate_fitness
from src.mutation import mutate
from src.placement import pm_loads_vcpu, validate_placement
from src.reporting import save_validation
from src.workload import cpu_demand_vcpu


CONFIG = Path(__file__).resolve().parents[1] / "configs" / "experiment_config.yaml"


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG)

    def evaluate(self, demand, placement, reference=None):
        return evaluate_placement(demand, placement, self.config, reference)[0]

    def test_config_matches_specification(self):
        c = self.config
        self.assertEqual(c["infrastructure"], {
            "vm_cpu_capacity_vcpu": 1.0, "pm_cpu_capacity_vcpu": 16.0,
            "available_pm_count": 12, "safe_cpu_threshold": 0.8})
        self.assertEqual(c["project"]["random_seeds"], 1)
        self.assertEqual(c["project"]["master_seed"], 42)
        self.assertEqual(c["project"]["rng"], "PCG64")
        self.assertEqual(c["genetic_algorithm"], {
            "population_size": 50, "max_generations": 100, "tournament_size": 3,
            "crossover": {"type": "uniform", "probability": 0.8},
            "mutation": {"type": "random_reassignment", "per_gene_probability": 0.02},
            "elitism_count": 2})
        self.assertEqual(c["fitness"]["feasibility_tolerance"], 1e-9)

    def test_config_rejects_missing_invalid_and_nonfinite(self):
        original = yaml.safe_load(CONFIG.read_text())
        bad_configs = []
        c = copy.deepcopy(original)
        del c["infrastructure"]["pm_cpu_capacity_vcpu"]
        bad_configs.append(c)
        c = copy.deepcopy(original)
        c["fitness"]["feasibility_tolerance"] = float("nan")
        bad_configs.append(c)
        c = copy.deepcopy(original)
        c["genetic_algorithm"]["mutation"]["per_gene_probability"] = 2
        bad_configs.append(c)
        c = copy.deepcopy(original)
        c["experiments"]["dynamic"]["window_size_samples"] = 13
        bad_configs.append(c)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            for config in bad_configs:
                with self.subTest(config=config):
                    path.write_text(yaml.safe_dump(config))
                    with self.assertRaises(ValueError):
                        load_config(path)

    def test_vcpu_conversion_and_invalid_ratio(self):
        np.testing.assert_equal(cpu_demand_vcpu([[0.4, 1]], 1), [[0.4, 1]])
        for values in ([[40]], [[-0.1]], [[float("nan")]], [[]]):
            with self.assertRaises(ValueError):
                cpu_demand_vcpu(values, 1)

    def test_placement_encoding_and_loads(self):
        demand = np.array([[0.4, 0.6, 0.2, 0.3, 0.5], [1, 0, 0.1, 0.2, 0.3]])
        placement = [1, 1, 2, 2, 3]
        loads = pm_loads_vcpu(demand, placement, 12)
        np.testing.assert_allclose(loads[:, :3], [[1, 0.5, 0.5], [1, 0.3, 0.3]])
        np.testing.assert_equal(loads[:, 3:], 0)
        metrics = self.evaluate(demand, placement)
        self.assertEqual(metrics["active_pm_count"], 3)
        self.assertAlmostEqual(metrics["mean_active_pm_utilization_ratio"], 3.6 / (6 * 16))
        for invalid in ([0, 1], [1, 13], [1], [1.0, 2.0], [[1, 2]]):
            with self.assertRaises(ValueError):
                validate_placement(invalid, 2, 12)

    def test_safe_capacity_and_all_timestamps(self):
        # 13 VMs needed: <=10 VMs of 1 vCPU cannot overload a 12.8-vCPU PM.
        demand = np.array([[1.0] * 12 + [0.8], [0.0] * 13])
        metrics = self.evaluate(demand, [1] * 13)
        self.assertEqual(metrics["status"], "FEASIBLE")
        self.assertAlmostEqual(metrics["maximum_pm_load_vcpu"], 12.8)
        demand[1] = [1] * 13
        metrics = self.evaluate(demand, [1] * 13)
        self.assertEqual(metrics["status"], "INFEASIBLE")
        self.assertEqual(metrics["overload_events"], 1)
        self.assertAlmostEqual(metrics["overload_percentage_pm_time_pairs"], 100 / 24)
        self.assertAlmostEqual(metrics["maximum_pm_utilization_ratio"], 13 / 16)
        self.assertAlmostEqual(metrics["total_overload_utilization_ratio"], 0.0125)
        self.assertAlmostEqual(metrics["normalized_cpu_violation"], (0.0125 / 0.2) ** 2 / 24)

    def test_small_averaged_violation_does_not_override_hard_constraint(self):
        demand = np.zeros((288, 13))
        demand[0] = [1] * 12 + [0.80001]
        metrics = self.evaluate(demand, [1] * 13)
        self.assertLess(metrics["normalized_cpu_violation"], 1e-9)
        self.assertEqual(metrics["status"], "INFEASIBLE")

    def test_fitness_ordering(self):
        demand = np.ones((2, 13))
        good = self.evaluate(demand, [1] * 12 + [2])
        worse_feasible = self.evaluate(demand, [1] * 11 + [2, 3])
        bad = self.evaluate(demand, [1] * 13)
        good_fit = calculate_fitness(good, self.config, "static")
        bad_fit = calculate_fitness(bad, self.config, "static")
        self.assertGreater(good_fit, 1)
        self.assertLessEqual(bad_fit, 1)
        self.assertGreater(good_fit, bad_fit)
        self.assertGreater(good_fit, calculate_fitness(worse_feasible, self.config, "static"))
        lower_violation = self.evaluate(np.full((2, 13), 0.99), [1] * 13)
        self.assertGreater(calculate_fitness(lower_violation, self.config, "static"), bad_fit)

    def test_migration_objective_not_mutations(self):
        demand = np.full((12, 5), 0.4)
        metrics = self.evaluate(demand, [1, 1, 2, 2, 3], [1, 1, 2, 3, 3])
        self.assertEqual(metrics["migration_count"], 1)
        self.assertAlmostEqual(metrics["normalized_migration_cost"], 0.2)
        self.assertAlmostEqual(calculate_fitness(metrics, self.config, "dynamic"),
                               1 + 1 / (1 + 0.70 * 3 / 12 + 0.30 / 5))
        without_reference = self.evaluate(demand, [1, 1, 2, 2, 3])
        self.assertEqual(calculate_fitness(metrics, self.config, "static"),
                         calculate_fitness(without_reference, self.config, "static"))
        with self.assertRaises(ValueError):
            calculate_fitness(without_reference, self.config, "dynamic")

    def test_mutation_changes_to_different_valid_pm(self):
        original = np.tile(np.arange(1, 13), 100)
        # Seed belongs to this isolated operator test, not an experimental run.
        mutated = mutate(original, np.random.default_rng(42), 12, 1)
        self.assertTrue(np.all(mutated != original))
        self.assertTrue(np.all((mutated >= 1) & (mutated <= 12)))
        np.testing.assert_equal(mutate(original, np.random.default_rng(42), 12, 0), original)
        np.testing.assert_equal(original, np.tile(np.arange(1, 13), 100))

    def test_consolidation_is_transactional_on_failure_and_feasibility_checked(self):
        config = copy.deepcopy(self.config)
        config["infrastructure"]["available_pm_count"] = 2
        demand = np.full((2, 4), 7.0)
        source = np.array([1, 1, 2, 2])
        counters = {}
        result = consolidate_one_pm(source, demand, config, np.random.default_rng(42), counters=counters)
        np.testing.assert_equal(result, source)
        self.assertEqual(counters["attempts"], 1)
        self.assertEqual(counters["failed"], 1)
        self.assertEqual(counters.get("successful", 0), 0)
        self.assertGreater(counters["feasibility_evaluations"], 0)

    def test_loader_exclusions_scale_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.config["dataset"]["path"] = str(root)
            (root / "z_vm").write_text("40\n" * 288)
            (root / "a_vm").write_text("0.5\n" * 288)
            (root / "short_vm").write_text("10\n")
            (root / "missing_vm").write_text("\n" + "10\n" * 287)
            matrix, ids, manifest, actions = load_workload(self.config)
            self.assertEqual(matrix.shape, (288, 2))
            self.assertEqual(ids, ["a_vm", "z_vm"])
            self.assertEqual(len(actions), 2)
            self.assertEqual(len(manifest), 4)
            np.testing.assert_equal(matrix[0], [0.005, 0.4])
            (root / "z_vm").write_text("0.4\n" * 288)
            (root / "short_vm").write_text("0.1\n")
            (root / "missing_vm").write_text("\n" + "0.1\n" * 287)
            self.config["dataset"]["input_scale"] = "ratio"
            matrix, *_ = load_workload(self.config)
            np.testing.assert_equal(matrix[0], [0.5, 0.4])

    def test_loader_rejects_invalid_without_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.config["dataset"]["path"] = str(root)
            for value in ("nan", "inf", "-1", "101", "bad"):
                with self.subTest(value=value):
                    (root / "vm").write_text((value + "\n") * 288)
                    with self.assertRaises(ValueError):
                        load_workload(self.config)

    def test_five_vm_validation_pipeline_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            for i, percentage in enumerate((40, 60, 20, 30, 50)):
                (root / f"vm{i}").write_text(f"{percentage}\n" * 288)
            self.config["dataset"]["path"] = str(root)
            self.config["dataset"]["expected_vm_count"] = 5
            matrix, ids, manifest, actions = load_workload(self.config)
            demand = cpu_demand_vcpu(matrix, self.config["infrastructure"]["vm_cpu_capacity_vcpu"])
            metrics = self.evaluate(demand, [1, 1, 2, 2, 3])
            self.assertEqual(metrics["status"], "FEASIBLE")
            self.assertAlmostEqual(metrics["maximum_pm_load_vcpu"], 1)
            self.assertAlmostEqual(metrics["mean_active_pm_utilization_ratio"], 2 / (3 * 16))
            self.assertAlmostEqual(calculate_fitness(metrics, self.config, "static"), 1.8)
            destination = Path(tmp) / "output"
            summary = save_validation(self.config, matrix, ids, manifest, actions, destination)
            self.assertAlmostEqual(summary["mean_aggregate_demand_vcpu"], 2)
            np.testing.assert_equal(np.load(destination / "data/workload_matrix.npy"), matrix)
            effective = json.loads((destination / "summaries/experiment_config.json").read_text())
            self.assertEqual(effective["stage"], "DATA_VALIDATION_ONLY")
            self.assertIsNone(effective["random_seed_list"])
            self.assertTrue((destination / "summaries/run_status.csv").is_file())
            self.assertTrue((destination / "data/dataset_files.csv").is_file())
            with self.assertRaises(FileExistsError):
                save_validation(self.config, matrix, ids, manifest, actions, destination)


if __name__ == "__main__":
    unittest.main()
