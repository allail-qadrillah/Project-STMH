"""Compare completed, independently verified single-seed artifacts; no GA execution."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1]
WORKTREES = BASE.parent
ROOTS = {
    'Original': BASE/'outputs/full_seed42/original',
    'Initialization': BASE/'outputs/full_seed42/initialization',
    'Relocation': WORKTREES/'ga-feasible-relocation/outputs/full_seed42/relocation',
    'Consolidation': WORKTREES/'ga-consolidation-mutation/outputs/full_seed42/consolidation',
}
COLORS = dict(zip(ROOTS, ['#59636e','#2674c7','#c87717','#288a63']))


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    target = BASE/'outputs'
    plots = target/'consolidation_comparison_figures'
    plots.mkdir(exist_ok=False)
    records, histories, costs, loads, initial = {}, {}, {}, {}, {}
    for variant, root in ROOTS.items():
        assert json.loads((root/'summaries/execution_status.json').read_text())['status'] == 'COMPLETED'
        for track in ('static','cold_start','warm_start'):
            directories = [root/'experiments/static/ga'] if track == 'static' else [root/f'experiments/dynamic/{track}/window_{w:02d}' for w in range(1,25)]
            key = (variant,track)
            records[key] = [read(d/'metrics.csv')[0] for d in directories]
            histories[key] = [read(d/'per_generation_metrics.csv') for d in directories]
            costs[key] = [json.loads((d/'cost.json').read_text()) for d in directories]
            loads[key] = [np.load(d/'raw.npz')['loads_vcpu'] for d in directories]
            initial[key] = [read(d/'initial_population_metrics.csv') for d in directories]
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(plots/(name+'.png'),dpi=160)
        plt.close(fig)
    for field, title, name in [('best_feasible_active_pm_count','Best feasible active PMs','active_convergence'),
                               ('feasible_population_count','Feasible population','feasible_convergence'),
                               ('best_fitness','Best fitness','fitness_convergence')]:
        fig, axes = plt.subplots(1,3,figsize=(14,4),sharey=True)
        for ax,track in zip(axes,('static','cold_start','warm_start')):
            for variant in ROOTS:
                series = [[float(h[field]) if h[field] else np.nan for h in window] for window in histories[variant,track]]
                ax.plot(np.nanmean(series,axis=0),label=variant,color=COLORS[variant])
            ax.set(title=track,xlabel='Generation',ylabel=title)
        axes[0].legend(fontsize=8)
        save(fig,name)
    for track in ('static','cold_start','warm_start'):
        fig, axes = plt.subplots(4,1,figsize=(12,10),sharex=True,sharey=True)
        for ax,variant in zip(axes,ROOTS):
            values=np.concatenate(loads[variant,track]) / 16
            ax.plot(values,linewidth=.4,alpha=.65)
            ax.axhline(.8,color='black',linestyle='--')
            ax.set(title=variant,ylabel='CPU ratio',ylim=(0,1.05))
        axes[-1].set_xlabel('Sample index (0–287)')
        save(fig,track+'_workload')
    fig,axes=plt.subplots(1,3,figsize=(14,4),sharey=True)
    for ax,track in zip(axes,('static','cold_start','warm_start')):
        for variant in ROOTS:
            ax.plot(range(1,len(records[variant,track])+1),[float(r['maximum_pm_utilization_ratio']) for r in records[variant,track]],label=variant,color=COLORS[variant],marker='.')
        ax.axhline(.8,color='black',linestyle='--'); ax.set(title=track,ylabel='Maximum CPU ratio',xlabel='Window',ylim=(0,1.05))
    axes[0].legend(fontsize=8); save(fig,'maximum_utilization')
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True)
    for ax,track in zip(axes,('cold_start','warm_start')):
        for variant in ROOTS:
            ax.plot(range(1,25),[int(r['migration_count']) for r in records[variant,track]],label=variant,color=COLORS[variant])
        ax.set(title=track,xlabel='Window / transition',ylabel='Migrations',ylim=(0,1033))
    axes[0].legend(fontsize=8); save(fig,'migrations')
    fig,axes=plt.subplots(4,3,figsize=(14,11),sharex=True,sharey=True)
    for row,variant in enumerate(ROOTS):
        for col,track in enumerate(('static','cold_start','warm_start')):
            grid=np.zeros((24,101))
            for window in histories[variant,track]:
                for g,h in enumerate(window):
                    for k in map(int,h['population_active_pm_counts'].split(';')):
                        grid[k-1,g]+=1/(50*len(histories[variant,track]))
            axes[row,col].imshow(grid,origin='lower',aspect='auto',extent=(-.5,100.5,.5,24.5),vmin=0,vmax=1,cmap='Blues')
            axes[row,col].set(title=variant+' / '+track,xlabel='Generation',ylabel='Active PMs')
    save(fig,'population_distribution')
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    variants=list(ROOTS)
    wall=[json.loads((ROOTS[v]/'summaries/execution_status.json').read_text())['wall_seconds'] for v in variants]
    axes[0].bar(variants,wall,color=[COLORS[v] for v in variants]); axes[0].set_ylabel('Total wall seconds')
    rates=[]
    for v in ('Relocation','Consolidation'):
        ops=[c['operator_metrics'] for t in ('static','cold_start','warm_start') for c in costs[v,t]]
        attempts=sum(o['attempts'] for o in ops)
        successes=sum(o['reducing_active_pm'] if v=='Relocation' else o['successful'] for o in ops)
        rates.append(100*successes/attempts if attempts else 0)
    axes[1].bar(['Relocation','Consolidation'],rates,color=[COLORS[v] for v in ('Relocation','Consolidation')]); axes[1].set_ylabel('Active-PM reducing attempts (%)')
    save(fig,'runtime_success')
    lines=['# GA consolidation experiment evaluation','', '**Single-run observations: seed 42. No statistical significance, global-optimality or statistically established winner claim.**','',
      '## 1. Configuration and experimental design','',
      'All variants: 1,033 VMs, 288 samples, 24 PMs, 1 vCPU/VM, 16 vCPU/PM, threshold 0.80, tolerance 1e-9. Population 50; 100 reproduction updates plus generation 0; tournament k=3 with replacement; uniform crossover 0.80; mutation trigger 0.02 per gene; two elites; PCG64 seed 42.',
      '', 'Original uses uniform initialization and random reassignment. Initialization (controlled baseline) uses 40 compact + 10 uniform candidates; warm windows 2–24 use 1 inherited + 39 compact + 10 uniform. Relocation/consolidation use identical initialization policy, replacing mutation independently. Infeasible initial candidates and inherited placements are retained. Compact sampling is random-subset assignment, without feasibility repair.',
      '', 'Full runs executed sequentially with fresh output paths. Exact frozen source snapshots, working-tree diffs and HEAD hashes are under `full_seed42/provenance/`. All use common committed foundation `21cf4c1c9125cde31ca758f45fc4d8c812fb8fe9`; snapshot hashes identify uncommitted implementations. Baseline core source remained unchanged; runtime observer was validated against uninstrumented behavior.',
      '', '## 2. Overall and static results','', '| Variant | Feasibility | Active PMs | Reduction (%) | Overload events | GA runtime (s) |','|---|---|---:|---:|---:|---:|']
    for v in ROOTS:
        r=records[v,'static'][0]; a=int(r['active_pm_count'])
        lines.append(f"| {v} | {r['status']} | {a} | {(24-a)/24*100:.2f} | {r['overload_events']} | {float(r['runtime_seconds']):.3f} |")
    lines+=['','## 3. Dynamic results','', '| Variant | Track | Feasible windows | Mean active | Min–max active | Mean reduction (%) | Migrations | Mean migrations/transition | Overloads |','|---|---|---:|---:|---|---:|---:|---:|---:|']
    for v in ROOTS:
        for t in ('cold_start','warm_start'):
            rs=records[v,t]; a=[int(r['active_pm_count']) for r in rs]; migrations=sum(int(r['migration_count']) for r in rs)
            lines.append(f"| {v} | {t} | {sum(r['status']=='FEASIBLE' for r in rs)}/24 | {np.mean(a):.3f} | {min(a)}–{max(a)} | {(24-np.mean(a))/24*100:.2f} | {migrations} | {migrations/24:.3f} | {sum(int(r['overload_events']) for r in rs)} |")
    lines+=['','All 24 transitions include common initial placement to window 1. Later references are each variant’s previous selected placement. Static migrations are descriptive differences from random static reference, excluded from static fitness; initialization uses static-reference role 500 versus role 0 for other arms, so static migration counts are not a matched-reference comparison. Dynamic reference role 2 is identical across all arms. Optimization roles are disjoint (1/3/4; 501/503/504; 601/603/604; 701/703/704).', '', '## 4. Initial population quality','', '| Variant | Track | Mean feasible initial candidates / 50 | Mean initial active PMs |','|---|---|---:|---:|']
    for v in ROOTS:
        for t in ('static','cold_start','warm_start'):
            batches=initial[v,t]
            lines.append(f"| {v} | {t} | {np.mean([sum(r['status']=='FEASIBLE' for r in b) for b in batches]):.3f} | {np.mean([int(r['active_pm_count']) for b in batches for r in b]):.3f} |")
    lines+=['','## 5. Operator effectiveness and cost','', '| Variant | Attempts | Accepted / successful | Rejected / failed | PM-reducing attempts | Extra feasibility checks | Operator seconds |','|---|---:|---:|---:|---:|---:|---:|']
    for v in ROOTS:
        ops=[c['operator_metrics'] for t in ('static','cold_start','warm_start') for c in costs[v,t]]
        total=lambda k:sum(o[k] for o in ops)
        lines.append(f"| {v} | {total('attempts')} | {total('accepted')+total('successful')} | {total('rejected')+total('failed')} | {total('reducing_active_pm')+total('pms_emptied')} | {total('feasibility_evaluations')} | {total('runtime_seconds'):.3f} |")
    lines+=['','Zero counters for original/initialization mean no new relocation/consolidation operator, not zero random gene mutations. Consolidation counts tentative and discarded moves separately; failed attempts restore input chromosome. Feasibility-preserving operators can still receive infeasible offspring from crossover.', '', '| Variant | Total wall seconds | Peak RSS (MiB) | Fitness evaluations | Feasibility evaluations |','|---|---:|---:|---:|---:|']
    for v in ROOTS:
        s=json.loads((ROOTS[v]/'summaries/execution_status.json').read_text()); cs=[c for t in ('static','cold_start','warm_start') for c in costs[v,t]]
        lines.append(f"| {v} | {s['wall_seconds']:.3f} | {s['peak_rss_kib']/1024:.2f} | {sum(c['evaluation_counts']['fitness'] for c in cs)} | {sum(c['evaluation_counts']['feasibility'] for c in cs)} |")
    lines+=['','Counts cover 49 GA optimizations (one static + 24 cold + 24 warm); random static reference evaluation and post-run verification are excluded. Total wall time includes loading, persistence and plotting. Equal generation counts are not equal computational budgets. Reproduction timing includes selection/crossover/mutation and differs from operator-only time. Peak RSS is process high-water mark, Linux KiB converted to MiB.', '', '## 6. Convergence and visualizations','', 'Dynamic convergence panels show means across windows; they are descriptive temporal aggregates, not independent-run statistics. Population heatmaps show chromosome fractions by active count, averaged over windows. Use feasible active count with feasibility curves; fitness alone does not establish consolidation. CPU workload figures share 0–1.05 utilization limits; threshold shown at 0.80.']
    for name in ('active_convergence','feasible_convergence','fitness_convergence','population_distribution','maximum_utilization','static_workload','cold_start_workload','warm_start_workload','migrations','runtime_success'):
        lines+=['',f'![{name}](consolidation_comparison_figures/{name}.png)']
    lines+=['','## 7. Interpretation and limitations','', 'Compare initialization against original to observe initialization effects; compare relocation/consolidation against initialization to observe operator effects. Independent optimization streams and a single seed mean differences also include sampling variation. No causal certainty, statistical significance or general superiority can be inferred. Low feasible active counts must be weighed against extra CPU checks, wall time, and dynamic migration costs. No power model or optimality proof exists. Full per-window and per-generation CSVs retain failures and feasible-population information.', '', '## 8. Raw artifact locations','']
    for v,p in ROOTS.items(): lines.append(f'- **{v}**: `{p}`')
    (target/'consolidation_experiment_evaluation.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    main()
