"""Single approved full run; writes fresh artifacts, never overwrites historical runs."""
import argparse
import hashlib
import json
import resource
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

from src.config import load_config
from src.data_loader import load_workload
from src.reporting import save_validation, save_result, write_csv, dynamic_summary
from src.workload import cpu_demand_vcpu


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--original', action='store_true')
    args = parser.parse_args()
    started = perf_counter()
    config = load_config(args.config)
    assert config['infrastructure'] == dict(vm_cpu_capacity_vcpu=1., pm_cpu_capacity_vcpu=16., available_pm_count=24, safe_cpu_threshold=.8)
    assert config['genetic_algorithm']['population_size'] == 50
    assert config['genetic_algorithm']['max_generations'] == 100
    assert config['project']['master_seed'] == 42
    destination = Path(args.destination)
    if destination.exists():
        raise FileExistsError(destination)
    # Baseline source is unchanged; validated observer added at runtime before imports.
    if args.original:
        import src.genetic_algorithm as ga
        from src.diagnostics import observe
        ga.run_ga = observe(ga.run_ga, ga)
    from src.static_experiment import run_static
    from src.dynamic_experiment import run_dynamic
    from src.visualization import plot_experiment
    matrix, ids, manifest, actions = load_workload(config)
    assert matrix.shape == (288, 1033) and len(ids) == 1033
    assert ids == sorted(ids)
    save_validation(config, matrix, ids, manifest, actions, destination, experiment=True)
    summary = destination / 'summaries'
    metadata_path = summary / 'experiment_config.json'
    metadata = json.loads(metadata_path.read_text())
    metadata.update(variant=args.variant, stage='EXPERIMENT', random_seed_list=[42],
                    initialization_policy='original_uniform' if args.original else '40 compact + 10 uniform; warm 1 inherited + 39 compact + 10 uniform',
                    acceptance='evaluate every candidate; retain infeasible; no resampling')
    metadata_path.write_text(json.dumps(metadata, indent=2))
    status = summary / 'execution_status.json'
    status.write_text(json.dumps({'status':'RUNNING'}))
    try:
        demand = cpu_demand_vcpu(matrix, 1.)
        results, streams, rows = {}, [], []
        experiments = destination / 'experiments'
        static = run_static(demand, config)
        results['static'] = static
        streams.extend(static['streams'])
        for method in ('baseline', 'ga'):
            row = save_result(experiments / 'static' / method, static[method], ids, config)
            rows.append({'method':'static_' + method, **row})
        def extra(directory, result):
            (directory / 'cost.json').write_text(json.dumps({'evaluation_counts':result['evaluation_counts'],
                'operator_metrics':result['operator_metrics'], 'runtime_seconds':result['runtime_seconds'],
                'reproduction_runtime_seconds':result['reproduction_runtime_seconds']}, indent=2))
        extra(experiments / 'static' / 'ga', static['ga'])
        print(json.dumps({'variant':args.variant,'track':'static',**static['ga']['metrics']}), flush=True)
        def window(method, result):
            directory = experiments / 'dynamic' / method / f"window_{result['window']:02d}"
            save_result(directory, result, ids, config)
            extra(directory, result)
            print(json.dumps({'variant':args.variant,'track':method,'window':result['window'],**result['metrics']}), flush=True)
        dynamic = run_dynamic(demand, config, on_window=window)
        results['dynamic'] = dynamic
        streams.extend(dynamic['streams'])
        write_csv(experiments / 'dynamic' / 'initial_placement.csv',
            [{'vm_id':vm,'pm_id':int(pm)} for vm, pm in zip(ids,dynamic['initial_placement'])], ['vm_id','pm_id'])
        for method in ('cold_start','warm_start'):
            windows = dynamic[method]
            window_rows = [{'seed':42,'window':r['window'],'sample_start':r['sample_start'],
                'sample_end':r['sample_end'],**r['metrics'],'runtime_seconds':r['runtime_seconds']} for r in windows]
            write_csv(experiments / 'dynamic' / method / 'per_window_metrics.csv',window_rows,list(window_rows[0]))
            rows.append(dynamic_summary(method,windows,1033,42))
        write_csv(summary / 'experiment_summary.csv',rows,list(dict.fromkeys(k for row in rows for k in row)))
        (summary / 'random_streams.json').write_text(json.dumps(streams,indent=2))
        plot_experiment(destination,matrix,results,config)
        status.write_text(json.dumps({'status':'COMPLETED','wall_seconds':perf_counter()-started,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
    except BaseException as exc:
        status.write_text(json.dumps({'status':'FAILED','error':repr(exc),'wall_seconds':perf_counter()-started,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
        raise


if __name__ == '__main__':
    main()
