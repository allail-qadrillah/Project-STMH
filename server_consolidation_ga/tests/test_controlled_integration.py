"""Synthetic 24-PM integration; never loads PlanetLab."""
import csv
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
import numpy as np
from src.config import load_config
from src.genetic_algorithm import run_ga
from src.dynamic_experiment import run_dynamic
from src.evaluation import evaluate_placement
from src.reporting import save_result
from src.randomness import make_stream
from src.diagnostics import observe


class ControlledIntegrationTests(unittest.TestCase):
    def test_24_pm_static_dynamic_and_artifacts(self):
        c = load_config(Path(__file__).resolve().parents[1] / 'configs/experiment_config.yaml')
        c['infrastructure']['available_pm_count'] = 24
        c['genetic_algorithm']['max_generations'] = 1
        # 1,033 genes exercised without expensive full optimization; 24 windows use 13 VMs.
        result = run_ga(np.zeros((288, 1033)), c, make_stream(c, 'static_ga')[0], 'static')
        self.assertEqual(result['initial_population'].shape, (50, 1033))
        self.assertTrue(np.all((result['initial_population'] >= 1) & (result['initial_population'] <= 24)))
        demand = np.full((288, 13), .1)
        dynamic = run_dynamic(demand, c)
        expected = np.random.Generator(np.random.PCG64(np.random.SeedSequence(42, spawn_key=(2, 0)))).integers(1,25,size=13)
        np.testing.assert_array_equal(dynamic['initial_placement'], expected)
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            for track in ('cold_start', 'warm_start'):
                self.assertEqual(len(dynamic[track]), 24)
                reference = expected.copy()
                for i, r in enumerate(dynamic[track]):
                    np.testing.assert_array_equal(r['reference'], reference)
                    metrics, loads = evaluate_placement(demand[i*12:(i+1)*12], r['placement'], c, reference)
                    for key, value in metrics.items():
                        self.assertEqual(r['metrics'][key], value)
                    if track == 'warm_start' and i:
                        np.testing.assert_array_equal(r['initial_population'][0], reference)
                    directory = Path(tmp) / track / str(i)
                    save_result(directory, r, [str(v) for v in range(13)], c)
                    for filename, rows in [('initial_population_metrics.csv',50),('per_generation_metrics.csv',2),('operator_metrics.csv',1)]:
                        with (directory / filename).open() as stream:
                            self.assertEqual(len(list(csv.DictReader(stream))), rows)
                    reference = r['placement'].copy()

    def test_original_baseline_observer_rng_and_execution_equality(self):
        source = subprocess.check_output(['git','show','21cf4c1c9125cde31ca758f45fc4d8c812fb8fe9:server_consolidation_ga/src/genetic_algorithm.py'], text=True)
        module = types.ModuleType('src._baseline_validation')
        module.__package__ = 'src'
        exec(compile(source, '<committed-baseline>', 'exec'), module.__dict__)
        c = load_config(Path(__file__).resolve().parents[1] / 'configs/experiment_config.yaml')
        c['infrastructure']['available_pm_count'] = 24
        c['genetic_algorithm']['max_generations'] = 3
        demand = np.full((288, 13), .1)
        for mode in ('static', 'dynamic'):
            a, b = np.random.default_rng(42), np.random.default_rng(42)
            reference = np.ones(13,dtype=int)
            original = module.run_ga(demand, c, a, mode, reference)
            monitored = observe(module.run_ga, module)(demand, c, b, mode, reference)
            self.assertEqual(a.bit_generator.state,b.bit_generator.state)
            for key in ('placement','initial_population','best_chromosomes','loads_vcpu'):
                np.testing.assert_array_equal(original[key],monitored[key])
            self.assertEqual(original['metrics'],monitored['metrics'])
            for x,y in zip(original['history'],monitored['history']):
                self.assertEqual(x,{k:y[k] for k in x})
