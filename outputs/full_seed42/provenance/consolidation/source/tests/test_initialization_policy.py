"""Small complete-window gates: evaluation never filters initialization."""

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from src.config import load_config
from src.evaluation import evaluate_placement
from src.genetic_algorithm import initialize_population, run_ga


class InitializationPolicyTests(unittest.TestCase):
    def test_fixed_draws_inherited_retention_and_complete_window(self):
        config = load_config(Path(__file__).resolve().parents[1] / "configs/experiment_config.yaml")
        config = copy.deepcopy(config)
        config["infrastructure"]["available_pm_count"] = 24
        config["genetic_algorithm"]["max_generations"] = 0
        inherited = np.ones(24, dtype=int)
        for reference in (None, inherited):
            # Independent transcription of approved fixed draws detects retries/filtering.
            replay = np.random.Generator(np.random.PCG64(42))
            expected = [] if reference is None else [reference.copy()]
            for _ in range(40 if reference is None else 39):
                size = int(replay.integers(1, 24))
                labels = replay.choice(24, size=size, replace=False) + 1
                expected.append(replay.choice(labels, size=24))
            expected.extend(replay.integers(1, 25, size=(10, 24)))
            rng = np.random.Generator(np.random.PCG64(42))
            actual = initialize_population(24, config, rng, reference)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(rng.bit_generator.state, replay.bit_generator.state)
            self.assertEqual(actual.shape, (50, 24))
            self.assertTrue(np.all((actual >= 1) & (actual <= 24)))
            if reference is not None:
                np.testing.assert_array_equal(actual[0], reference)
                # Exactly one inherited slot; random duplicate genotypes must not be filtered.
                self.assertEqual(sum(np.array_equal(p, reference) for p in actual), 1)

        for samples in (12, 288):
            demand = np.zeros((samples, 24))
            demand[-1] = 1
            rng = np.random.Generator(np.random.PCG64(42))
            with patch("src.genetic_algorithm.evaluate_placement", wraps=evaluate_placement) as evaluate:
                result = run_ga(demand, config, rng, "static", inherited=inherited)
            self.assertEqual(evaluate.call_count, 51)  # 50 candidates + final selected placement
            self.assertTrue(all(call.args[0].shape == demand.shape for call in evaluate.call_args_list))
            rows = result["initial_population_metrics"]
            self.assertEqual(len(rows), 50)
            self.assertEqual(rows[0]["status"], "INFEASIBLE")
            self.assertGreater(rows[0]["normalized_cpu_violation"], 0)
            np.testing.assert_array_equal(result["initial_population"][0], inherited)
            self.assertTrue(any(m["status"] == "FEASIBLE" for m in rows[1:40]))
            self.assertTrue(any(m["status"] == "INFEASIBLE" for m in rows[:40]))
            low = run_ga(np.zeros_like(demand), config, np.random.Generator(np.random.PCG64(42)),
                         "static", inherited=inherited)
            self.assertTrue(all(m["status"] == "FEASIBLE" for m in low["initial_population_metrics"]))
            np.testing.assert_array_equal(low["initial_population"], result["initial_population"])
            self.assertEqual(result["evaluation_counts"], {"fitness": 50, "feasibility": 51})


if __name__ == "__main__":
    unittest.main()
