# Parallel Monte Carlo π estimation implementation plan

Complete the implementation, core measurements and written project report in one working day, Monday 23 November 2026. The schedule assumes the team can work in parallel on code, experiments and report preparation. The four C17 modes and sampling behavior follow [the architecture plan](ARCHITECTURE.md). The required submission includes the GitHub repository and complete PDF report. This plan omits the video deliverable.

## One-day schedule

### 08:00–09:00 · Confirm the build environment and divide work

- [ ] Record compiler, OpenMP and MPI versions, CPU/core count and available hosts in the report notes.
- [ ] Check that the compiler and MPI toolchain are installed. Assign one member to the shared sampling/serial code, one to OpenMP, and one to MPI/hybrid integration. Assign report and benchmark coordination to the group leader.
- [ ] Create the Makefile targets `seq`, `omp`, `mpi` and `hybrid` with consistent optimization flags and output paths.

### 09:00–12:00 · Implement the four modes

- [x] Implement shared argument validation, point-in-quarter-circle test, per-worker random generator initialization and result output in `src/common.h`.
- [x] Implement and build `src/seq.c` as the reference mode. Use 64-bit trial and hit counts.
- [ ] Implement `src/omp.cpp` with a private random generator per thread and a sum reduction.
- [ ] Implement `src/mpi.cpp` with quotient/remainder trial partitioning and a 64-bit count reduction to rank zero.
- [ ] Implement `src/hybrid.cpp` by combining the MPI partition with the OpenMP loop. Keep MPI calls on the main thread and check the provided thread support.
- [ ] Resolve integration and compilation errors before starting large runs.

### 12:00–13:00 · Verify small runs

- [ ] Check the point predicate using points `(0,0)`, `(1,0)` and `(0.9,0.9)`.
- [ ] Run every mode with one million trials and verify `0 ≤ hits ≤ N`, the estimate formula, and one result row per invocation.
- [ ] Check MPI work splits for 10 trials over 3 ranks and 2 trials over 4 ranks. Confirm all ranks finish when some receive zero trials.
- [ ] Compare serial, one-thread OpenMP, one-rank MPI and one-rank/one-thread hybrid for the same seed. Confirm repeated fixed-layout runs reproduce the hit count.

### 13:00–15:00 · Run the feasible benchmark set

- [ ] Run a short pilot for each mode and estimate whether the 10¹⁰-trial baseline fits the remaining machine time.
- [ ] Prioritize the sequential baseline and equal-work comparisons at one and four workers. Use configurations supported by the host, such as 1, 2, 4 and 8 workers where available. Avoid oversubscription.
- [ ] Run the 10¹⁰-trial workload for configurations that fit the time budget. If a run cannot finish, record the pilot size and measured time, and clearly label any scaled result. Do not present extrapolated times as measured results.
- [ ] Save each raw timing with mode, trial count, seed, ranks, threads per rank, hits, estimate and elapsed seconds. Record machine and compiler details.

### 15:00–17:00 · Analyze results and prepare the report

- [ ] Calculate speedup as sequential time divided by parallel time and efficiency as speedup divided by total workers for equal trial counts.
- [ ] Produce runtime, speedup and efficiency graphs from measured data. If multiple repetitions fit, retain the individual measurements and report the median.
- [ ] Compare estimate error with π at several feasible trial counts. Explain that the expected error trend is proportional to `1/√N`, while noting the number of seeds and trials actually measured.
- [ ] Complete the report with objective, algorithm, architecture, implementation, experiment setup, results, graphs, limitations and conclusion. Export it as PDF and check that tables and graphs are legible.

### 17:00–18:00 · Finalize repository and written deliverable

- [ ] Update the root README with build/run instructions and links to the project documents. Include benchmark commands and clarify which results were measured.
- [ ] Confirm the repository contains source, build instructions, raw measurements, analysis scripts, figures and the complete PDF report.
- [ ] Rebuild from a clean checkout and run a small case for each available mode. Verify the PDF opens and the GitHub repository is accessible to the group.
- [ ] The group leader prepares the submission with the repository link, report PDF, and the member names and roll numbers below. Submit before the course deadline on Wednesday, 25 November 2026.

> Huzaifa Abdul Rehman — 23K-0782
>
> Abdul Moiz Hussain — 23K-0553
>
> Muhammad Abdullah Khan — 23K-0607

## Completion criteria for today

The code for all four modes builds and passes the small-run checks, benchmark evidence and its limitations are recorded, and the complete written report is exported as a readable PDF. The 10¹¹-trial run and option-pricing extension remain optional as stated in the proposal.
