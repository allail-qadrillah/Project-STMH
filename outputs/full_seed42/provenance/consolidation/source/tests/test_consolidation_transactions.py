import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import numpy as np
from src.config import load_config
from src.consolidation_mutation import consolidate_one_pm
from src.genetic_algorithm import reproduce


class TransactionTests(unittest.TestCase):
    def test_success_partial_failure_and_single_pm(self):
        c = load_config(Path(__file__).resolve().parents[1] / 'configs/experiment_config.yaml')
        c['infrastructure']['available_pm_count'] = 24
        rng = Mock()
        rng.choice.return_value = 1
        rng.permutation.side_effect = lambda values: np.asarray(values)
        source = np.array([1, 1] + [2] * 11)
        counts = {}
        failed = consolidate_one_pm(source, np.ones((288, 13)), c, rng, counters=counts)
        np.testing.assert_array_equal(failed, source)
        self.assertEqual(counts['discarded_moves'], 1)
        self.assertEqual(counts['feasibility_evaluations'], 2)
        success = consolidate_one_pm(source, np.full((288, 13), .1), c, rng, counters=counts)
        self.assertEqual(len(np.unique(success)), 1)
        self.assertEqual(counts['vms_moved'], 2)
        unchanged = consolidate_one_pm(success, np.full((288, 13), .1), c, rng, counters=counts)
        np.testing.assert_array_equal(unchanged, success)
        self.assertEqual(counts['attempts'], counts['successful'] + counts['failed'])
        self.assertEqual(counts['attempts'], 3)
        self.assertEqual(counts['tentative_moves'], counts['vms_moved'] + counts['discarded_moves'])

    def test_each_marked_gene_initiates_attempt(self):
        c = load_config(Path(__file__).resolve().parents[1] / 'configs/experiment_config.yaml')
        c['genetic_algorithm']['mutation']['per_gene_probability'] = 1
        population = np.ones((50, 5), dtype=int)
        with patch('src.genetic_algorithm.consolidate_one_pm', side_effect=lambda child, *a: child) as operation:
            reproduce(population, np.ones(50), c, np.random.default_rng(42), np.zeros((288, 5)), counters={})
        self.assertEqual(operation.call_count, 48 * 5)
