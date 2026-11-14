import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from src.config import load_config
from src.experiment import run_experiment


class SchemaContractTests(unittest.TestCase):
    def test_all_five_artifacts_24_pm(self):
        config = load_config(Path(__file__).resolve().parents[1] / 'configs/controlled_24.yaml')
        config['genetic_algorithm']['max_generations'] = 1
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            destination = Path(tmp) / 'run'
            with patch('src.experiment.plot_experiment'), patch('src.experiment.plot_saved_results'), patch('src.experiment.document_outputs'):
                run_experiment(config, np.full((288, 5), .1), [str(i) for i in range(5)], [], [], destination)
            counts = {'initial_population_metrics.csv':50, 'per_generation_metrics.csv':2,
                      'operator_metrics.csv':1, 'per_window_metrics.csv':24, 'experiment_summary.csv':4}
            headers = {}
            occurrences = {}
            for filename, expected in counts.items():
                paths = list(destination.rglob(filename))
                self.assertEqual(len(paths), 49 if filename in ('initial_population_metrics.csv','per_generation_metrics.csv','operator_metrics.csv') else 2 if filename == 'per_window_metrics.csv' else 1)
                for path in paths:
                    with path.open() as stream:
                        reader = csv.DictReader(stream)
                        header = reader.fieldnames
                        self.assertEqual(len(list(reader)), expected)
                    self.assertEqual(headers.setdefault(filename,header),header)
                occurrences[filename] = len(paths)
            Path('/tmp/opencode/schema-' + str(config['project']['stream_ids']['static_ga']) + '.json').write_text(json.dumps(headers,indent=2))
