# Recorded benchmark experiments

`2026-11-23/` records Issue #6 on one Intel Core i7-8650U host under WSL2.
The guest exposes four physical cores and eight logical CPUs. Each experiment
uses CPU IDs 0, 2, 4 and 6 (one sibling per core), with at most four workers.
This is a single-host MPI experiment; it does not measure network scaling.
Other host activity and virtual-machine scheduling cannot be fully controlled.

## Build and reproduction

The C source is commit `08b6634`; this PR adds collection and analysis tooling
without changing the estimator. Compiler: GCC 15.2.0; flags:
`-O3 -Wall -Wextra -Wpedantic -std=c17` (plus `-fopenmp` for OpenMP/hybrid).
MPI: MPICH 4.3.2, temporarily extracted under `/tmp/montecarlo-review-mpi/root/usr`.
The launcher/toolchain paths in the records are specific to this machine.
On a machine with MPI installed normally, use `make seq omp mpi hybrid` and
the portable README commands. Exact build commands for this measurement:

```sh
make -B seq omp
make -B mpi hybrid \
  MPICC='cc -I/tmp/montecarlo-review-mpi/root/usr/lib/x86_64-linux-gnu/mpich/include -L/tmp/montecarlo-review-mpi/root/usr/lib/x86_64-linux-gnu -Wl,-rpath-link,/tmp/montecarlo-review-mpi/root/usr/lib/x86_64-linux-gnu' \
  LDLIBS=-l:libmpich.so.12
LD_LIBRARY_PATH=/tmp/montecarlo-review-mpi/root/usr/lib/x86_64-linux-gnu \
  python3 scripts/benchmark.py --output results/new-run \
  --mpiexec /tmp/montecarlo-review-mpi/root/usr/bin/mpiexec.hydra \
  --mpi-args='-bind-to none'
python3 scripts/summarize.py results/new-run
```

The metadata dry-run uses default Makefile variables; the explicit MPI override
above is the build actually used. Every raw invocation records its effective
OpenMP environment and the shared CPU list. MPI ranks take slices of that list
of size threads-per-rank, indexed by rank. The executable's timer excludes Python
and MPI launcher startup; JSONL wall time includes both.

## Experiment design

All ten layouts get a 10⁷-trial pilot. Scaling uses N = 10¹⁰, seed 42,
two repetitions per layout, in repetition-major order:

- Sequential: 1 worker.
- OpenMP: 1, 2 and 4 threads.
- MPI: 1, 2 and 4 ranks.
- Hybrid: 1×4, 2×2 and 4×1 ranks×threads.

Accuracy uses sequential, OpenMP 1×4, MPI 4×1 and hybrid 2×2 at N =
10⁴, 10⁵, 10⁶ and 10⁷, with seeds 0, 1, 2, 3 and 42. This produces
80 accuracy measurements. Accuracy samples use different deterministic streams
across layouts; runtime comparisons still process equal trial counts. Five seeds
provide limited evidence for the expected 1/√N error trend, not a proof of it.
Use aggregate RMSE rather than demanding monotonic error for each seed.

`raw.csv` retains every measured runtime, seed, hit count and estimate.
`runs.jsonl` retains per-invocation stdout/stderr and exact commands.
`scaling_summary.csv` reports medians, ranges, speedup and efficiency.
`accuracy_summary.csv` reports mean absolute error and RMSE across seeds.
`COMPLETE` is evidence that no baseline/configuration was skipped. A directory
without this marker must be treated as an incomplete experiment.

Pilots can estimate total machine time by multiplying each pilot sampling time
by 10¹⁰/10⁷ and summing across layouts and repetitions. These forecasts are
never substituted for measured baseline timings; short pilots are sensitive to
startup, frequency changes and host scheduling. Repeated measurements and their
spread should guide interpretation. Graphs and the final PDF report are subsequent
deliverables using these data.

## Completion and protocol adjustment

All ten layouts completed **two** scaling repetitions at N = 10¹⁰. No baseline
was missed. Collection initially requested three repetitions; the user requested
two after the second round. The third round was stopped. Its completed records
are retained in `excluded_third_repetition.*` and excluded from analysis.
`protocol.json` records the effective protocol; the original metadata preserves
the original invocation rather than rewriting its history.

Accuracy collection resumed separately with `--stages accuracy` into
`2026-11-23-accuracy/`; that directory preserves its own invocation and metadata.
Its 80 raw results and JSONL records are also included in the main directory
for one combined analysis. The main `COMPLETE` marker confirms the final protocol:
10 pilots + 20 scaling measurements + 80 accuracy measurements = 110 retained
runs. The independent audit checked all row counts, successful exits, estimates,
equal trial counts and reproducible hit counts across both scaling repetitions.
Two repetitions give a timing range and median but limited statistical confidence.

## Observations for the report

The sequential median is 129.03 s; OpenMP with four threads is 29.84 s, MPI
with four ranks is 31.70 s, and hybrid 2×2 is 35.02 s. Some calculated speedups
exceed the worker count. Do not clamp these measurements: discuss varying CPU
frequency, scheduling, implementation differences and the limited repetition
count. They do not establish a general superlinear scaling claim.

Across five seeds, RMSE at N = 10⁷ is lower than at N = 10⁴ in every mode.
Intermediate values need not decrease monotonically (OpenMP is one example).
The roughly inverse-square-root expectation is statistical; five seeds are too
few to estimate its constant precisely. No 10¹¹-trial workload was attempted;
that remains optional in the proposal.
