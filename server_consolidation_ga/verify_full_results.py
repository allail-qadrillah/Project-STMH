"""Read-only reconstruction of full-run raw artifacts; never executes GA."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from src.evaluation import evaluate_placement
from src.fitness import calculate_fitness


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def verify(root):
    config = json.loads((root/'summaries/experiment_config.json').read_text())['configuration']
    demand = np.load(root/'data/workload_matrix.npy')
    assert demand.shape == (288,1033)
    assert config['infrastructure']['available_pm_count'] == 24
    initial = np.array([int(r['pm_id']) for r in rows(root/'experiments/dynamic/initial_placement.csv')])
    expected = np.random.Generator(np.random.PCG64(np.random.SeedSequence(42,spawn_key=(2,0)))).integers(1,25,1033)
    np.testing.assert_array_equal(initial,expected)
    static_reference = np.load(root/'experiments/static/baseline/raw.npz')['placement']
    cases = [(root/'experiments/static/ga',demand,static_reference,'static')]
    for track in ('cold_start','warm_start'):
        reference = initial
        for w in range(1,25):
            directory=root/f'experiments/dynamic/{track}/window_{w:02d}'
            cases.append((directory,demand[(w-1)*12:w*12],reference,'dynamic'))
            reference=np.load(directory/'raw.npz')['placement']
    for directory,window,reference,mode in cases:
        raw=np.load(directory/'raw.npz')
        saved=rows(directory/'metrics.csv')[0]
        metrics,loads=evaluate_placement(window,raw['placement'],config,reference)
        np.testing.assert_allclose(loads,raw['loads_vcpu'],rtol=0,atol=1e-12)
        for k,v in metrics.items():
            if isinstance(v,str): assert saved[k]==v,(directory,k)
            elif v is not None: assert np.isclose(float(saved[k]),v,rtol=1e-12,atol=1e-12),(directory,k)
        assert np.isclose(float(saved['fitness']),calculate_fitness(metrics,config,mode))
        initial_rows=rows(directory/'initial_population_metrics.csv')
        assert raw['initial_population'].shape==(50,1033)
        for chromosome,row in zip(raw['initial_population'],initial_rows):
            m,_=evaluate_placement(window,chromosome,config,reference)
            assert m['status']==row['status']
            assert m['active_pm_count']==int(row['active_pm_count'])
            assert np.isclose(m['normalized_cpu_violation'],float(row['normalized_cpu_violation']))
        history=rows(directory/'fitness_history.csv')
        assert len(history)==101
        for chromosome,row in zip(raw['best_chromosomes'],history):
            m,_=evaluate_placement(window,chromosome,config,reference)
            assert m['status']==row['status']
            assert m['active_pm_count']==int(row['active_pm_count'])
            assert np.isclose(calculate_fitness(m,config,mode),float(row['best_fitness']))
        cost=json.loads((directory/'cost.json').read_text())
        assert cost['evaluation_counts']['fitness']==5050
        assert cost['evaluation_counts']['feasibility']==5051+cost['operator_metrics']['feasibility_evaluations']
    return {'root':str(root),'optimizations_verified':len(cases),'initial_chromosomes_verified':len(cases)*50,
            'best_chromosomes_verified':len(cases)*101,'status':'PASSED'}


if __name__=='__main__':
    for path in sys.argv[1:]:
        print(json.dumps(verify(Path(path))),flush=True)
