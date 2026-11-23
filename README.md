# Parallel Monte Carlo π estimation

PDC semester project comparing sequential, OpenMP, MPI and hybrid MPI + OpenMP execution.

## Build and run the sequential estimator

Use GNU Make and a C17 compiler on a POSIX system with `CLOCK_MONOTONIC`.

```sh
make seq
./build/seq 1000000 42
```

Pass the trial count and seed in that order as unsigned decimal integers. The trial count must be positive, and the seed may be zero. With the same seed and trial count, the sequential version reproduces the hit count. Invalid inputs print usage to stderr and exit with status 1.

Each successful run writes one headerless CSV row with these columns in order.

```csv
mode,trials,seed,ranks,threads_per_rank,hits,pi_estimate,seconds
```

The sequential mode is `seq` and reports one rank and one thread. The runtime measures the sampling loop in elapsed seconds.

## Project documents in reading order

1. [Original proposal](documents/PDC%20Project%20Proposal%20%E2%80%93%20Parallel%20Monte%20Carlo%20Pi%20Estimation%20%281%29.docx) records the topic, team, scope and proposed experiment.
2. [Software requirements](documents/REQUIREMENTS.md) define what the project must demonstrate and how to check each requirement.
3. [Feasibility and constraints](documents/FEASIBILITY.md) identify the hardware, runtime and submission assumptions the team needs to verify.
4. [Software architecture](documents/ARCHITECTURE.md) describes the components, work distribution and measurement boundaries.
5. [Implementation plan](documents/IMPLEMENTATION_PLAN.md) sequences development, verification, benchmarking and submission.
