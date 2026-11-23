# Parallel Monte Carlo π estimation

PDC semester project comparing sequential, OpenMP, MPI and hybrid MPI + OpenMP execution.

## Build and run the sequential estimator

Use GNU Make and a C17 compiler on a POSIX system with `CLOCK_MONOTONIC`.

```sh
make seq
./build/seq 1000000 42
```

Pass the trial count and seed in that order as unsigned decimal integers. The trial count must be positive, and the seed may be zero. With the same seed and trial count, the sequential version reproduces the hit count. Invalid inputs print usage to stderr and exit with status 1.

Each successful run writes a CSV header followed by one result row. The columns are shown in this order.

```csv
mode,trials,seed,ranks,threads_per_rank,hits,pi_estimate,seconds
```

The sequential mode is `seq` and reports one rank and one thread. The runtime measures the sampling loop in elapsed seconds.

## Build and run the OpenMP estimator

Use a C17 compiler with OpenMP support. The Makefile defaults to `-fopenmp`.

```sh
make omp
OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE ./build/omp 1000000 42
```

The OpenMP mode is `omp` and uses the same arguments and CSV columns. It reports one rank and the actual number of threads in the OpenMP team. Its elapsed time includes starting the team, sampling, and summing the counts. One thread reproduces the sequential hit count for the same seed and trial count.

## Build and run the MPI estimator

Use an MPI implementation with a C compiler wrapper and a process launcher.

```sh
make mpi
mpiexec -n 4 ./build/mpi 1000000 42
```

Rank zero reports the `mpi` mode with one thread per rank.

## Build and run the MPI + OpenMP estimator

Build with an MPI compiler wrapper and an OpenMP-capable compiler. The hybrid mode requests `MPI_THREAD_FUNNELED`, checks that support is available, and keeps MPI calls on the main thread.

```sh
make hybrid
OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE mpiexec -n 2 ./build/hybrid 1000000 42
```

MPI divides trials across ranks by quotient and remainder. Each rank distributes its local trials among OpenMP threads. Every rank must use the same actual team size. Rank zero reports that team size and the `hybrid` mode. With one thread per rank, the hit count matches the MPI-only run for the same seed, trial count, and rank count.

## Project documents in reading order

1. [Original proposal](documents/PDC%20Project%20Proposal%20%E2%80%93%20Parallel%20Monte%20Carlo%20Pi%20Estimation%20%281%29.docx) records the topic, team, scope and proposed experiment.
2. [Software requirements](documents/REQUIREMENTS.md) define what the project must demonstrate and how to check each requirement.
3. [Feasibility and constraints](documents/FEASIBILITY.md) identify the hardware, runtime and submission assumptions the team needs to verify.
4. [Software architecture](documents/ARCHITECTURE.md) describes the components, work distribution and measurement boundaries.
5. [Implementation plan](documents/IMPLEMENTATION_PLAN.md) sequences development, verification, benchmarking and submission.

## Reproduce scaling and accuracy measurements

Build all four targets first (`make seq omp mpi hybrid`), with Python 3.9+,
Linux CPU affinity support, `taskset`, and a working MPI launcher available.
Then run:

```sh
python3 scripts/benchmark.py --output results/my-run
python3 scripts/summarize.py results/my-run
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The default experiment runs a 10-million-trial pilot for each layout, then
two repetitions at **10 billion trials**, and an accuracy sweep at 10⁴, 10⁵,
10⁶ and 10⁷ trials over five seeds in each mode. This takes several minutes.
Layouts use at most four physical cores and are filtered to the host capacity.
The accuracy sweep uses the largest available OpenMP and MPI layouts. The
hybrid layout in the default benchmark matrix needs four physical cores.
The runner reserves one logical CPU per physical core, assigns disjoint cores
to ranks, and binds OpenMP threads inside each rank. It supports MPICH and
Open MPI rank environment variables; pass `--mpiexec PATH --mpi-args='OPTIONS'`
for launcher-specific settings. Disable launcher binding if it conflicts with
the explicit worker affinity (MPICH: `--mpi-args='-bind-to none'`). Run on an
otherwise idle host; no other experiment is started concurrently by the runner.

For a short end-to-end check, use a **new** output directory:

```sh
python3 scripts/benchmark.py --output /tmp/mc-smoke --trials 10007 \
  --pilot-trials 1000 --repetitions 1 --accuracy-trials 1000 --seeds 0
```

Output directories are never overwritten. `raw.csv` adds stage and repetition
to the program CSV; `runs.jsonl` preserves exact argument lists, environment,
stdout, stderr and wall time for every invocation. `metadata.json` records
hardware, CPU selection, compiler, source revision and launcher. `COMPLETE` is
created only after every requested measurement succeeds. Missing/malformed
results and unexpected worker counts fail collection; completed earlier rows
are retained. The 30-minute per-invocation timeout is configurable. A failed
run must be investigated and rerun into a new directory.

The summaries compare median parallel runtime with the sequential median at
identical N and seed; efficiency divides speedup by ranks × threads per rank.
Accuracy summaries report aggregate absolute and root mean squared errors;
individual seeds need not improve monotonically as N grows. See
[recorded experiment notes](results/README.md) for the measured environment,
commands and limitations. Plotting and the final report use these CSV files.
