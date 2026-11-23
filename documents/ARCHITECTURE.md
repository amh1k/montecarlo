# Architecture for parallel Monte Carlo π estimation

PDC Project #7 studies how runtime changes when the same sampling algorithm runs sequentially, across shared-memory threads, across MPI processes, and with both forms of parallelism. The proposal sets the baseline at 10 billion trials. A 100-billion-trial run and option pricing are optional extensions.

## Sampling and data flow

Each executable accepts a positive 64-bit trial count and a base seed. For each trial, draw two uniform coordinates in [0,1) and count a hit when x² + y² ≤ 1. Generate and discard each point immediately. Only counts pass between workers. The final estimate is 4.0 × hits / trials.

| Executable | Work assignment | Count aggregation |
|---|---|---|
| Sequential | One worker samples all N points | Local count |
| OpenMP | Static parallel loop over N trials | OpenMP integer sum reduction |
| MPI | Rank r receives floor(N/P) trials plus one when r < N mod P | MPI_Reduce sums rank counts on rank 0 |
| Hybrid | MPI uses the same partition, then each rank threads its local loop | OpenMP reduction followed by MPI_Reduce |

Proposed implementation choices are C17, a Makefile and a shared sampling header. Give each worker private SplitMix64 state initialized by mixing the base seed with the packed rank and thread ID. Fixed configurations support repeatable runs. Changing the worker layout changes the sampled points. Use unsigned 64-bit counters and MPI_UINT64_T for counts. A rank assigned zero trials still participates in collectives. In hybrid mode only the main thread calls MPI, requesting and checking MPI_THREAD_FUNNELED support.

## Measurement boundary

Time sampling through final count aggregation, excluding startup, argument parsing and printing. Synchronize MPI ranks before starting MPI_Wtime and report the maximum elapsed rank time. Use POSIX CLOCK_MONOTONIC for the sequential executable and omp_get_wtime for OpenMP. Emit one CSV row per run with mode, N, seed, ranks, actual threads per rank, hits, π estimate and seconds. Require uniform thread counts for hybrid benchmarks. Analysis scripts read these rows and generate the report figures. A single multicore host supports all four modes. Record host count and placement so the report can distinguish local MPI costs from inter-host communication.
