# Genetic Algorithm for Server Consolidation with PlanetLab Workload Traces

**Technical specification for implementation by an AI coding agent**

- Project: Sistem Terinspirasi Makhluk Hidup
- Document: GA_Server_Consolidation_EN.md
- Version: 4.0
- Language: Plain technical English, based on ASD-STE100 principles
- Main method: Genetic Algorithm (GA)
- Workload source: PlanetLab CPU utilization traces
- CPU unit: vCPU

---

## 1. Purpose

Build and test a Genetic Algorithm (GA) for Virtual Machine (VM)
placement on Physical Machines (PMs).

The GA must assign each VM to one PM. It must keep the CPU load of every
PM within a safe limit. It must use as few active PMs as possible.

The project has two experiments:

1. **Static placement.** Find one VM placement for the full day.
    Evaluate this placement with all 288 workload samples.
2. **Dynamic placement.** Find one VM placement for each one-hour
    window. Compare cold-start GA with warm-start GA. Measure the number
    of VM migrations between windows.

This project is an offline simulation. It does not control a real data
center. It does not predict future workload.

The workload trace is input data. The GA changes only the VM-to-PM
assignment. The GA must not change the workload values.

## 2. Scope and system assumptions

Use the following assumptions in the first implementation:

- Each VM keeps the same workload trace after a migration.
- A migration does not change the CPU demand of a VM.
- A migration does not add CPU overhead.
- A migration does not add network overhead.
- PM capacity stays fixed during an experiment.
- Workload is external input. It does not depend on the placement.
- The simulation uses historical workload samples.
- The simulation does not use a workload prediction method.
- A PM is active if it hosts at least one VM.
- The simulation does not use a PM power or energy model.
- The simulation does not use a network bandwidth constraint.

Do not add migration overhead, network constraints, energy models, or
workload prediction in this version.

## 3. Dataset and workload

### 3.1 Configurable dataset input

The implementation must not depend on one fixed dataset folder, file
name, date, or machine-specific path.

The user must set the dataset location and data format in the
configuration file. The data loader must read the configured path. Do
not hard-code a dataset path in Python source files.

The implementation must support a configurable input path and a
documented input layout. Examples include one file per VM or one matrix
file. Select the input layout through configuration. If the configured
layout is not supported, report the issue and ask the user before
changing the data format or adding an assumption.

The current experiment expects a workload matrix with 1,033 VM traces
and 288 samples per VM. These are expected dataset properties, not
hidden constants. The code must inspect the actual input and report the
observed shape. Put expected counts and sample interval in the
configuration file.

Use a stable VM order. Keep the VM identifiers with the processed data.

The matrix has one row for each timestamp and one column for each VM:

\[ U = [u_i(t)] \]

where:

- \(i\) is the VM index.
- \(t\) is the timestamp index.
- \(u_i(t)\) is the CPU utilization ratio of VM \(i\) at time \(t\).

For a full day, \(t\) has 288 values.

### 3.2 Data scale and preprocessing

The raw trace values are in the range 0 to 100. Convert them to a ratio
in the range 0 to 1 by dividing by 100.

For example:

\[ 40\% = 0.40 \]

The data loader must check the input scale before it converts the
values. Do not divide data by 100 more than once.

The data loader must:

1. Read the selected VM trace files.
2. Keep a stable VM order.
3. Parse CPU samples as numeric values.
4. Check for missing and invalid values.
5. Check for negative values.
6. Check that raw percentage values are not greater than 100.
7. Check that each selected VM has 288 samples.
8. Align all VM traces by timestamp or sample index.
9. Convert percentage values to ratios from 0 to 1.
10. Report the final number of VMs and samples.
11. Save the processed workload matrix.

Do not silently replace invalid values. Record every data-cleaning
action.

If a VM trace does not have the required 288 samples, exclude that VM
from the first experiment and record its identifier and reason. Use the
same final VM set for every method and every seed.

### 3.3 Observed workload summary

The current data inspection produced these values after conversion to
ratios:

| Metric | Observed value |
|---|---:|
| Minimum VM utilization | 0.00 |
| Maximum VM utilization | 0.99 |
| Mean VM utilization | 0.10431 |
| Mean aggregate CPU demand | 107.75302 vCPU |
| Maximum aggregate CPU demand | 123.88 vCPU |
| Minimum aggregate CPU demand | 93.37 vCPU |

The mean VM utilization is the mean across the VM-time observations. The
aggregate CPU demand is the sum of the VM demands at one timestamp.

The value **123.88 vCPU is the peak aggregate demand of all 1,033 VMs at
one timestamp**. It is not the demand of one VM. It is not the capacity
of one PM.

Recalculate these summary values from the actual input files. Do not
hard-code them as workload data. If the recalculated values differ,
report the new values and investigate the difference.

## 4. VM and PM capacity configuration

The PlanetLab trace does not provide the VM CPU capacity and PM CPU
capacity that this experiment needs. Use the following values as
simulation assumptions.

| Parameter | Value | Status |
|---|---:|---|
| CPU capacity of each VM | 1 vCPU | Simulation assumption |
| CPU capacity of each PM | 16 vCPU | Simulation assumption |
| Number of available PMs | 12 | Experiment setting |
| Safe CPU threshold | 0.80 | Design choice |
| Effective safe capacity per PM | 12.8 vCPU | Derived value |

Do not describe the VM or PM capacities as values supplied by PlanetLab.

### 4.1 Convert utilization to CPU demand

Let:

- \(u_i(t)\) be the utilization ratio of VM \(i\) at time \(t\).
- \(C_i^{VM}\) be the configured CPU capacity of VM \(i\).
- \(d_i(t)\) be the CPU demand of VM \(i\) at time \(t\).

Use:

\[ d_i(t)=u_i(t)C_i^{VM} \]

For this experiment:

\[ C_i^{VM}=1\text{ vCPU} \]

Therefore:

\[ d_i(t)=u_i(t)\text{ vCPU} \]

Example:

\[ u_i(t)=0.40 \]

\[ d_i(t)=0.40\times1=0.40\text{ vCPU} \]

This conversion is a modeling assumption. It treats the utilization
ratio as a fraction of the configured 1 vCPU capacity of each VM. The
dataset does not confirm that every real VM had an allocation of exactly
1 vCPU.

Use vCPU for every CPU capacity and CPU demand value in the code, logs,
tables, and plots. Do not mix vCPU with MIPS.

### 4.2 PM safe capacity

Each PM has a configured capacity of 16 vCPU. The safe CPU threshold is
80%.

The effective safe capacity of one PM is:

\[
C_{\text{safe}}^{PM}=0.80\times16=12.8\text{ vCPU}
\]

The total safe capacity of 12 available PMs is:

\[
C_{\text{safe,total}}=12\times12.8=153.6\text{ vCPU}
\]

The peak aggregate workload is 123.88 vCPU. The aggregate headroom is:

\[ 153.6-123.88=29.72\text{ vCPU} \]

The aggregate lower bound for the number of PMs is:

\[ N_{\text{lower bound}}=
\left\lceil\frac{123.88}{12.8}\right\rceil=10
\]

This value is only an aggregate lower bound. It does not prove that 10
PMs can host all VMs. Each VM must be assigned to one PM. Each PM must
satisfy the safe CPU limit at every required timestamp.

Use **12 PMs as the available PM set**. Allow the GA to activate between
1 and 12 PMs. The objective is to minimize the number of active PMs. Do
not force the GA to use all 12 PMs.

## 5. Problem formulation

### 5.1 Sets and indices

| Symbol | Meaning |
|---|---|
| \(V\) | Set of VMs |
| \(H\) | Set of available PMs |
| \(n\) | Number of VMs |
| \(m\) | Number of available PMs; \(m=12\) |
| \(T\) | Number of workload samples in the evaluation window |
| \(i\) | VM index |
| \(j\) | PM index |
| \(t\) | Time-sample index |

### 5.2 Decision variable

Define:

\[ x_{ij}=

\begin{cases}
1 & \text{if VM }i\text{ is placed on PM }j\\
0 & \text{otherwise}
\end{cases}

\]

Every VM must be assigned to exactly one PM:

\[ \sum_{j=1}^{m}x_{ij}=1 \qquad\forall i \]

Define \(y_j=1\) if PM \(j\) hosts at least one VM. Otherwise, \(y_j=0\).

The following relation links VM placement to PM activation:

\[ x_{ij}\leq y_j \qquad\forall i,j \]

The binary variables describe the mathematical model. The GA chromosome
uses integer encoding.

### 5.3 PM CPU load

The CPU load of PM \(j\) at time \(t\) is:

\[ L_j(t)=\sum_{i=1}^{n}x_{ij}d_i(t) \]

The PM CPU utilization is:

\[ U_j(t)=\frac{L_j(t)}{16} \]

The safe capacity constraint is:

\[ L_j(t)\leq12.8 \qquad\forall j,t \]

A placement is feasible only if every PM satisfies this constraint at
every sample in the evaluation window.

Use a numerical tolerance of \(10^{-9}\) when the code checks
floating-point values.

## 6. Optimization objectives and fitness

### 6.1 Active PM objective

Minimize the number of active PMs:

\[ f_1(X)=\sum_{j=1}^{m}y_j \]

A lower value is better.

### 6.2 CPU overload measure

Define normalized overload at PM \(j\) and time \(t\):

\[ e_j(t)=
\max\left(0,\frac{U_j(t)-0.80}{1-0.80}\right)
\]

Define the normalized overload cost:

\[ V(X)=\frac{1}{mT}
\sum_{j=1}^{m}\sum_{t=1}^{T}e_j(t)^2 \]

A placement is feasible when \(V(X)\) is zero within the numerical
tolerance.

Also record:

- Number of PM-time pairs above the safe threshold.
- Maximum PM utilization.
- Maximum overload above the safe threshold.
- Total overload magnitude.
- Normalized overload cost \(V(X)\).

The overload cost helps rank infeasible placements. It does not replace
the hard CPU constraint.

### 6.3 Migration measure

Let:

- \(p_i\) be the reference PM of VM \(i\).
- \(a_i\) be the selected PM of VM \(i\).

The migration count is:

\[ M(X)=\sum_{i=1}^{n}\mathbb{1}(a_i\neq p_i) \]

The normalized migration cost is:

\[ C_{\text{migration}}(X)=\frac{M(X)}{n} \]

Do not count a mutation operation as a migration. Count a migration only
when the selected placement differs from the reference placement.

### 6.4 Constraint-dominant fitness

The GA maximizes fitness.

Every feasible chromosome must rank above every infeasible chromosome.

For feasible chromosomes, define:

\[ C_{\text{server}}(X)=\frac{\sum_{j=1}^{m} y_j}{m} \]

For the dynamic experiment, use:

\[ J_f(X)=0.70C_{\text{server}}(X)
+0.30C_{\text{migration}}(X) \]

For the static experiment, use:

\[ J_{\text{static}}(X)=C_{\text{server}}(X) \]

Convert the cost to fitness:

\[ Fitness(X)=

\begin{cases}
1+\dfrac{1}{1+J_f(X)}, & \text{if feasible}\\[8pt]
\dfrac{1}{1+V(X)}, & \text{if infeasible}
\end{cases}

\]

For the static experiment, use \(J_{\text{static}}\) in the
feasible branch.

This fitness rule gives these results:

- Feasible fitness is greater than 1.
- Infeasible fitness is less than or equal to 1.
- Every feasible chromosome ranks above every infeasible chromosome.
- Among feasible chromosomes, a lower objective cost gives a higher
    fitness.
- Among infeasible chromosomes, a lower normalized violation gives a
    higher fitness.

Do not replace this rule with a simple weighted sum of PM count and
overload. A weighted sum can select an unsafe placement because it can
trade a constraint violation for a lower PM count.

### 6.5 Result when no feasible chromosome is found

If a GA run does not find a feasible chromosome within 100 generations:

1. Mark the run as INFEASIBLE.
2. Save the chromosome with the smallest normalized CPU violation
    \(V(X)\).
3. Save its overload metrics and PM placement.
4. Do not report it as a successful feasible placement.
5. Do not hide the infeasible status in summary tables.

If a run finds a feasible chromosome, return the best feasible
chromosome according to the objective for that experiment.

## 7. Chromosome encoding

Use integer encoding.

For \(n\) VMs and \(m=12\) available PMs:

\[ C = [a_1,a_2,\ldots,a_n] \]

where:

\[ a_i\in\{1,2,\ldots,12\} \]

Gene \(i\) gives the PM index for VM \(i\).

Example:

\[ C = [1,1,2,2,3] \]

This means:

- VM 1 is on PM 1.
- VM 2 is on PM 1.
- VM 3 is on PM 2.
- VM 4 is on PM 2.
- VM 5 is on PM 3.

Repeated PM indices are valid. Many VMs can use one PM.

This is not permutation encoding. Do not use permutation-only operators
such as Order Crossover (OX) or PMX.

A PM is active if at least one chromosome gene contains its PM index.

## 8. Initial population

Use a population size of 50 chromosomes.

For a random chromosome, assign each VM to one random PM from 1 to 12.

The initial population can contain infeasible placements. The fitness
function must rank them.

Do not add a repair method in the first implementation unless the user
approves this change.

For warm-start, include the previous window's best chromosome in the new
population. Add mutated copies and random chromosomes to fill the
remaining population slots. Keep random chromosomes to maintain
diversity.

## 9. Genetic operators

### 9.1 Selection: tournament selection

Use tournament selection with:

\[ k=3 \]

Procedure:

1. Select three chromosomes at random.
2. Compare their fitness values.
3. Return the chromosome with the highest fitness.
4. Repeat to select the next parent.

### 9.2 Crossover: uniform crossover

Use uniform crossover.

For each gene position:

- Select the gene from Parent 1 or Parent 2 for Child 1.
- Give the other parent's gene to Child 2.

Use:

\[ P_c=0.80 \]

Every child gene remains a valid PM index. A child can still break a CPU
constraint. Evaluate the child after crossover.

### 9.3 Mutation: random reassignment

Use random reassignment mutation.

For each gene, use the per-gene mutation probability:

\[ P_m=0.02 \]

When mutation occurs:

1. Read the current PM index.
2. Select a different PM index from 1 to 12.
3. Replace the gene with the new PM index.

Do not use swap mutation as the main mutation operator.

### 9.4 Elitism

Keep the best two chromosomes from the current generation without
changes.

Use:

\[ E=2 \]

Copy these chromosomes to the next generation before adding offspring.

## 10. GA parameters

Use the following initial settings:

| Parameter | Value |
|---|---:|
| Population size | 50 |
| Maximum generations | 100 |
| Tournament size | 3 |
| Crossover type | Uniform |
| Crossover probability | 0.80 |
| Mutation type | Random reassignment |
| Per-gene mutation probability | 0.02 |
| Elitism count | 2 |
| Available PMs | 12 |
| VM CPU capacity | 1 vCPU |
| PM CPU capacity | 16 vCPU |
| Safe CPU threshold | 0.80 |
| Repeated runs per method | 30 random seeds |

These are experiment settings. Do not describe them as optimal parameter
values.

Use a fixed and recorded seed for every run. Use the same list of 30
seeds for methods that must be compared.

## 11. GA procedure

For each optimization window:

1. Load the workload samples for the window.
2. Create the initial population.
3. Decode each chromosome into a VM-to-PM placement.
4. Calculate the CPU load of each PM at every sample.
5. Check the CPU capacity constraint.
6. Calculate the active PM count.
7. Calculate migration count when a reference placement exists.
8. Calculate fitness.
9. Select parents with tournament selection.
10. Apply uniform crossover with probability 0.80.
11. Apply random reassignment mutation with probability 0.02 per gene.
12. Evaluate the offspring.
13. Copy the best two chromosomes to the next population.
14. Continue until the algorithm completes 100 generations.
15. Return the best feasible chromosome. If no feasible chromosome
    exists, return the chromosome with the smallest normalized violation
    and mark the run INFEASIBLE.

Store the best-so-far chromosome and its metrics at every generation. Do
not lose the best solution found in an earlier generation.

## 12. Experiment 1: static VM placement

### 12.1 Goal

Find one VM placement that minimizes the number of active PMs and
satisfies the CPU capacity constraint for the full day.

### 12.2 Workload horizon

Use all 288 daily samples:

\[ T=288 \]

One chromosome must be evaluated against all 288 samples. The chromosome
must not change during this evaluation.

### 12.3 Random baseline

For each random seed:

1. Generate one random VM-to-PM placement.
2. Keep this placement fixed for all 288 samples.
3. Evaluate it against all 288 samples.
4. Record its feasibility and metrics.

Do not generate a new random placement at each timestamp.

### 12.4 Static GA

For each of the same 30 random seeds:

1. Run GA with all 288 samples.
2. Use the same VM set and PM configuration as the random baseline.
3. Return one best placement for the full day.
4. Evaluate this placement against all 288 samples.
5. Record its feasibility and metrics.

The static objective is:

\[ \min_X \sum_j y_j \]

subject to:

\[ \sum_{i=1}^{n} x_{ij}d_i(t)\leq12.8
\qquad\forall j,t \]

Do not include migration in the static fitness objective. Report the
number of VMs that move from the random baseline placement to the GA
placement as an additional metric.

### 12.5 Static outputs

For every seed, save:

- Random baseline placement.
- GA placement.
- Active PM count.
- Mean CPU utilization of active PMs.
- Maximum PM CPU utilization.
- Number of PM-time overload events.
- Total overload magnitude.
- Normalized overload cost.
- Number of VMs that differ from the baseline placement.
- Runtime.
- Best fitness by generation.
- Feasibility status.

## 13. Experiment 2: dynamic VM placement

### 13.1 Goal

Find a VM placement for each one-hour workload window. Compare
cold-start GA with warm-start GA.

### 13.2 Window definition

Each sample represents five minutes. Use 12 samples per window:

\[ 12\times5=60\text{ minutes} \]

The 288 daily samples form 24 windows:

\[ 288/12=24 \]

Use all 12 samples in each window to evaluate a chromosome.

- Window 1 uses samples 1 to 12.
- Window 2 uses samples 13 to 24.
- Continue until Window 24 uses samples 277 to 288.

### 13.3 Initial placement and fair comparison

For each random seed, create one common initial random placement.

Use this same initial placement for cold-start and warm-start in
Window 1. Use it as the migration reference for Window 1 in both
methods.

Use the same workload windows, VM set, PM configuration, GA parameters,
and random seed list for both methods.

### 13.4 Cold-start GA

For each window:

1. Create a new random population.
2. Run GA on the current 12 workload samples.
3. Return the best placement for the window.
4. Use the selected placement as the migration reference for the next
    window.

Do not use the previous window's best chromosome to initialize the next
cold-start population.

### 13.5 Warm-start GA

For Window 1, use the same initial placement and initialization basis as
cold-start.

For every later window:

1. Insert the previous window's best chromosome into the new
    population.
2. Add mutated copies of that chromosome.
3. Add random chromosomes.
4. Run GA on the current 12 workload samples.
5. Return the best placement for the current window.

The previous chromosome is an initial search candidate. It is not a
fixed answer. GA can change it through crossover and mutation.

### 13.6 Migration count

Let \(a_i^{(w)}\) be the PM of VM \(i\) in window \(w\).

For Window 1, compare the selected placement with the common initial
placement (a_i^{(0)}).

For later windows, compare the selected placement with the selected
placement from the previous window:

\[ M_w=\sum_{i=1}^{n}
\mathbb{1}(a_i^{(w)}\neq a_i^{(w-1)}) \]

Total migration count:

\[ M_{\text{total}}=\sum_{w=1}^{24}M_w \]

A VM can count as a migration more than once if it moves in more than
one window. This is correct because each change is a separate migration
event.

Do not count a mutation operation as a migration.

### 13.7 Dynamic fitness

For feasible placements, use:

\[ J_f(X)=0.70C_{\text{server}}(X)
+0.30C_{\text{migration}}(X) \]

The migration reference is the common initial placement in Window 1. For
every later window, it is the selected placement from the previous
window.

Use the constraint-dominant fitness from Section 6.

### 13.8 Offline evaluation rule

This dynamic experiment is an offline, retrospective simulation.

For each window, GA uses the 12 actual historical workload samples in
that same window. It does not predict those samples.

Do not describe this experiment as a real-time controller or a
predictive system.

### 13.9 Dynamic outputs

For each seed, method, and window, save:

- Window index and sample range.
- Selected VM-to-PM placement.
- Feasibility status.
- Active PM count.
- Mean CPU utilization of active PMs.
- Maximum PM CPU utilization.
- Number of overload events.
- Total overload magnitude.
- Migration count.
- Runtime.
- Best fitness by generation.

Also save the total migration count and total runtime for each daily
run.

## 14. Repeated runs and statistical reporting

Run each method with 30 random seeds.

The methods are:

1. Static random baseline.
2. Static GA.
3. Dynamic cold-start GA.
4. Dynamic warm-start GA.

Use the same 30-seed list for the compared methods.

For dynamic cold-start and warm-start, use the same initial placement
for each matching seed. This gives both methods the same starting
placement.

Report the mean and standard deviation across the 30 runs for the main
metrics.

Also report the number of feasible and infeasible runs. Do not calculate
a successful feasible-placement average without stating how many runs
were feasible.

Keep per-seed results. Do not save only the mean.

## 15. Evaluation metrics

Report the following metrics.

### 15.1 Active PM count

\[ PM_{\text{active}}=\sum_j y_j \]

For static placement, report the active PM count for each run.

For dynamic placement, report the mean, minimum, and maximum active PM
count across the 24 windows.

### 15.2 CPU utilization

For each PM and sample:

\[ U_j(t)=\frac{L_j(t)}{16} \]

Report:

- Mean utilization of active PMs.
- Maximum PM utilization.
- Utilization distribution.
- Per-window utilization for dynamic placement.

State whether a utilization mean includes inactive PMs. The main mean
active-PM utilization must include active PMs only.

### 15.3 Overload frequency

An overload event occurs when:

\[ U_j(t)>0.80 \]

Count all PM-time pairs that exceed the safe threshold:

\[ N_{\text{overload}}=
\sum_j\sum_t\mathbb{1}(U_j(t)>0.80) \]

Report the count and the percentage of PM-time pairs.

### 15.4 Overload magnitude

Report total overload magnitude:

\[ O_{\text{total}}=
\sum_j\sum_t\max(0,U_j(t)-0.80) \]

Also report the normalized overload cost \(V(X)\).

### 15.5 Migration count

For dynamic placement, report:

- Migration count per window.
- Total migration count per day.
- Mean migrations per window.
- Migration rate, calculated as total migrations divided by the number
    of VMs and the number of transitions.

For static placement, report the number of VMs that differ from the
random baseline placement. Do not include this value in the static
fitness objective.

### 15.6 Runtime

Measure each GA optimization call.

For static placement, report runtime per run.

For dynamic placement, report:

- Total runtime for 24 windows.
- Mean runtime per window.
- Runtime distribution across windows.

Report the 30-run mean and standard deviation.

### 15.7 Fitness convergence

Store the best-so-far fitness at every generation.

Plot best fitness against generation. Create separate plots or clearly
labeled series for the methods.

## 16. Implementation architecture and project structure

Build a reusable Python application. Separate the algorithm from the
dataset location and experiment settings.

The user must be able to change the dataset path and experiment
parameters by editing one configuration file. The user must not need to
edit Python source code to select another dataset path or change a
documented experiment parameter.

Do not hard-code dataset paths, file names, dates, expected VM or sample
counts, CPU capacities, PM count, safe threshold, GA parameters,
experiment mode, random seed count, or output directory in Python source
files.

Read these values from the configuration file. Validate the
configuration before the experiment starts. If a required setting is
missing or invalid, stop and show a clear error. Do not silently use a
different value.

### 16.1 Suggested project structure

Use this project structure:

```text
server_consolidation_ga/
|
|-- configs/
|   |-- experiment_config.yaml
|
|-- src/
|   |-- __init__.py
|   |-- config.py
|   |-- data_loader.py
|   |-- data_validation.py
|   |-- workload.py
|   |-- placement.py
|   |-- fitness.py
|   |-- selection.py
|   |-- crossover.py
|   |-- mutation.py
|   |-- genetic_algorithm.py
|   |-- static_experiment.py
|   |-- dynamic_experiment.py
|   |-- evaluation.py
|   |-- visualization.py
|   |-- reporting.py
|
|-- tests/
|   |-- test_config.py
|   |-- test_data_loader.py
|   |-- test_workload.py
|   |-- test_placement.py
|   |-- test_fitness.py
|   |-- test_operators.py
|   |-- test_feasibility.py
|
|-- outputs/
|   |-- data/
|   |-- static/
|   |-- dynamic/
|   |-- plots/
|   |-- summaries/
|
|-- main.py
|-- requirements.txt
|-- README.md
```

The raw dataset does not need to be inside the project directory. The
user can store it anywhere and set its path in experiment_config.yaml.

### 16.2 Configuration file

Use one configuration file as the single source of experiment settings.

The following YAML is an example. The implementation must read these
values. Do not copy them into Python constants.

```yaml
project:
  name: "GA Server Consolidation"
  random_seeds: 30

dataset:
  path: "/path/to/your/dataset"
  format: "planetlab_per_vm_files"
  input_scale: "percentage"
  expected_vm_count: 1033
  expected_samples_per_vm: 288
  sample_interval_minutes: 5
  date_label: "20110420"
  file_pattern: null
  timestamp_column: null
  vm_id_column: null

preprocessing:
  missing_value_policy: "exclude_vm"
  invalid_value_policy: "error"
  stable_vm_order: true

infrastructure:
  vm_cpu_capacity_vcpu: 1.0
  pm_cpu_capacity_vcpu: 16.0
  available_pm_count: 12
  safe_cpu_threshold: 0.80

genetic_algorithm:
  population_size: 50
  max_generations: 100
  tournament_size: 3
  crossover:
    type: "uniform"
    probability: 0.80
  mutation:
    type: "random_reassignment"
    per_gene_probability: 0.02
  elitism_count: 2

fitness:
  server_weight: 0.70
  migration_weight: 0.30
  feasibility_tolerance: 1.0e-9

experiments:
  static:
    enabled: true
    evaluate_all_samples: true
    include_migration_in_objective: false
  dynamic:
    enabled: true
    window_size_samples: 12
    compare_cold_start: true
    compare_warm_start: true
    same_initial_placement: true

output:
  directory: "outputs"
  save_placements: true
  save_per_generation_history: true
  save_per_seed_metrics: true
  save_plots: true
```

The example values reflect the current experiment decisions. The path
`/path/to/your/dataset` is a placeholder. The user must replace it with
the actual path.

The loader must support a clear, documented schema for each configured
dataset format. Do not guess file structure from file names alone. If
the actual files do not match the configured format, report the mismatch
and ask the user.

The code must write a copy of the effective configuration to the output
directory for every experiment. This copy must include the resolved
dataset path, observed dataset dimensions, and random seed list. Do not
overwrite the original configuration file.

### 16.3 Module responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Read, validate, and expose configuration values |
| `data_loader.py` | Read files from the configured dataset path |
| `data_validation.py` | Validate values, shape, timestamps, and VM identifiers |
| `workload.py` | Convert utilization ratios to CPU demand in vCPU |
| `placement.py` | Encode, decode, and inspect VM-to-PM placements |
| `fitness.py` | Calculate feasibility, objective costs, and fitness |
| `selection.py` | Implement tournament selection |
| `crossover.py` | Implement uniform crossover |
| `mutation.py` | Implement random reassignment mutation |
| `genetic_algorithm.py` | Run one GA optimization |
| `static_experiment.py` | Run static baseline and static GA |
| `dynamic_experiment.py` | Run cold-start and warm-start experiments |
| `evaluation.py` | Calculate all evaluation metrics |
| `visualization.py` | Create the required plots |
| `reporting.py` | Save tables, summaries, and run status |

Keep data loading, workload calculation, GA operators, experiment
control, and reporting separate. Do not place the full implementation in
one Python file.

### 16.4 Command-line use

Run the application from the project root:

```bash
python main.py --config configs/experiment_config.yaml
```

The application must load all paths and parameters from the selected
configuration file.

The implementation can support command-line overrides. However, the
configuration file must remain the source of default experiment
settings. Record every override in the effective configuration saved
with the results.

## 17. Required output files

Save enough information to reproduce and inspect every run.

Suggested output structure:

```text
outputs/
|
|-- data/
|   |-- dataset_summary.csv
|   |-- data_validation.txt
|   |-- workload_matrix.npy
|   |-- vm_order.csv
|
|-- static/
|   |-- per_seed_metrics.csv
|   |-- baseline_placements.csv
|   |-- ga_placements.csv
|   |-- fitness_history.csv
|
|-- dynamic/
|   |-- cold_start_per_window.csv
|   |-- warm_start_per_window.csv
|   |-- cold_start_placements.csv
|   |-- warm_start_placements.csv
|   |-- migration_summary.csv
|   |-- fitness_history.csv
|
|-- plots/
|   |-- workload_timeseries.png
|   |-- ga_convergence_static.png
|   |-- ga_convergence_dynamic.png
|   |-- pm_utilization_heatmap_static.png
|   |-- pm_utilization_heatmap_dynamic.png
|   |-- static_comparison.png
|   |-- dynamic_comparison.png
|   |-- runtime_comparison.png
|
|-- summaries/
|   |-- experiment_config.json
|   |-- experiment_summary.csv
|   |-- run_status.csv
```

The code must also save the exact random seed for every run and the
exact dataset file names used.

## 18. Validation and testing

Do not start the full 1,033-VM experiment before the small tests pass.

### 18.1 Data tests

- Load a small set of VM traces.
- Confirm the number of samples.
- Confirm the utilization scale.
- Confirm conversion from percentage to ratio.
- Confirm the workload matrix shape.
- Confirm the stable VM order.

### 18.2 Placement tests

Use a small hand-built example.

Check that:

- Every VM has exactly one PM.
- Every gene has a PM index from 1 to 12.
- Active PM count is correct.
- PM load is the sum of the demand of VMs assigned to that PM.

### 18.3 Capacity tests

Use a small hand-calculated workload.

Check that:

- A PM load of 12.8 vCPU is feasible.
- A PM load above 12.8 vCPU is infeasible.
- The code checks every timestamp.
- An overload at one timestamp makes the placement infeasible.

### 18.4 Fitness tests

Check that:

- Every feasible chromosome has fitness greater than 1.
- Every infeasible chromosome has fitness less than or equal to 1.
- A feasible chromosome ranks above an infeasible chromosome.
- A lower-cost feasible chromosome has higher fitness.
- A lower-violation infeasible chromosome has higher fitness.

### 18.5 Operator tests

Check that:

- Tournament selection returns a member of the population.
- Uniform crossover returns valid chromosome lengths and PM indices.
- Mutation changes a gene to a different valid PM when it occurs.
- Elitism keeps the best two chromosomes.
- The population size stays at 50 after every generation.

### 18.6 End-to-end test

First run the full pipeline with 5 to 10 VMs.

Check the data, placement, CPU load, feasibility, fitness, and saved
output files. Compare selected calculations with manual calculations.

Only start the full 1,033-VM experiment after these checks pass.

## 19. Experimental comparison and interpretation

Use the same VM set, workload samples, PM configuration, and GA
parameter values for fair comparisons.

The main comparisons are:

| Comparison | Main question |
|---|---|
| Static random vs static GA | Does GA reduce active PM count and keep the full-day placement feasible? |
| Dynamic cold-start vs dynamic warm-start | Does warm-start reduce migration or runtime while it keeps placements feasible? |

Do not claim that fewer active PMs always means lower energy. This
experiment does not include a PM power model.

Do not claim a global optimum from a GA result. GA is a stochastic
metaheuristic.

Report infeasible runs. Do not hide them or treat them as successful
placements.

Do not claim real-time control. The dynamic experiment uses historical
samples from the window being optimized.

## 20. Implementation order

The coding agent must follow this order:

1. Inspect and validate the PlanetLab data.
2. Build the 288 × 1,033 workload matrix.
3. Apply the vCPU capacity assumptions.
4. Implement placement encoding and decoding.
5. Implement PM load calculation and feasibility checks.
6. Implement the fitness function.
7. Implement selection, crossover, mutation, and elitism.
8. Run hand-calculated unit tests.
9. Run the 5-to-10-VM end-to-end test.
10. Run the static experiment with 30 seeds.
11. Run the dynamic cold-start experiment with 30 seeds.
12. Run the dynamic warm-start experiment with 30 seeds.
13. Save all metrics, placements, fitness histories, configurations, and
    plots.
14. Create summary tables and compare the methods.

Do not skip the validation stages.

## 21. Source basis

Use the project course materials and the supplied book reference as the
theoretical basis for the GA design:

- Week 1 --- Introduction to Optimization: decision variables,
    objective functions, and constraints.
- Week 2 --- Cycle GA and Encoding: chromosome representation and the
    GA cycle.
- Week 3 --- Selection: selection methods and tournament selection.
- Week 3 and 4 --- Crossover: crossover concepts and operator design.
- Week 5 --- Mutation and Update Generation: mutation and generation
    update.
- Week 6 --- Swarm Intelligence: PSO. This is background material. PSO
    is not the main method in this project.
- Yang, X.-S. (2014). *Nature-Inspired Optimization Algorithms*.
    Elsevier. Chapter 5, "Genetic Algorithms", especially Sections
    5.2--5.4, pages 78--83.

Dataset references:

- CloudSim: https://github.com/Cloudslab/cloudsim
- PlanetLab workload traces:
    https://github.com/beloglazov/planetlab-workload-traces

The implementation must record the exact repository, file names, date,
and commit or download version used for the experiment. Do not invent
missing dataset provenance.

## 22. Final instructions to the AI coding agent

Build a reproducible Python implementation of this specification.

Follow the stated assumptions and parameter values. Do not change the
CPU unit from vCPU. Do not change the VM capacity, PM capacity, number
of available PMs, safe threshold, GA operators, GA parameters,
experiment definitions, or repeated-run count.

Do not add new optimization objectives or simulation constraints.

If an implementation detail is not specified and it can change the
methodology or experiment result, do not make a silent decision. Report
the missing detail and ask the user before you implement it.

Use modular code. Keep parameters in a configuration file. Record all
random seeds. Save raw per-run results, placements, fitness histories,
run status, summary tables, and plots.

A run is successful only when it returns a feasible placement. If no
feasible placement is found, mark the run INFEASIBLE and save the
placement with the smallest normalized CPU violation.

First implement and test the small 5-to-10-VM case. Start the full
PlanetLab experiment only after the hand-calculated tests pass.
