# Feasibility and experiment constraints

The main uncertainty is whether the group can finish repeated 10¹⁰-trial measurements on its available hardware before the submission deadline. The proposal supplies the workload. Machine capacity and runtime still need measurement.

| Question | Evidence to collect | Decision it informs |
|---|---|---|
| Can the intended host run all four modes? | Record compiler, OpenMP and MPI versions, physical core count and available hosts. Build and run a small hybrid case once implementation reaches that stage. | Select feasible rank and thread counts. If only one host is available, identify MPI measurements as single-host results. |
| How much machine time is needed? | On the benchmark host, measure a pilot of known size for each configuration. Estimate baseline seconds as pilot seconds × 10¹⁰ / pilot trials. Sum over configurations and repetitions and reserve time for reporting. | Schedule the sequential baseline early. Trim optional configurations and extensions first if the projected schedule is tight. Report any missed baseline explicitly. |
| Will timings support a fair comparison? | Record actual ranks, threads per rank, placement, compiler flags and concurrent load. Keep N fixed across each speedup comparison. | Use configurations that fit the allocated cores. Document noisy measurements and retain individual repetitions. |
| Can accuracy be evaluated independently of speed? | Use several seeds at each trial count and record the errors against π. | Use a separate accuracy sweep so a lucky seed cannot determine the conclusion. |
| Who will submit and when? | Confirm the group leader and exact portal cutoff with the team. The assignment gives the date only. | Reserve time to check repository access, PDF rendering and video playback before the leader submits. |

Proceed with the four-mode architecture as the proposed design. Record actual hardware and pilot measurements in the report when available. A measured slowdown is a valid result and should be explained alongside any speedup.

## Sequential baseline environment

The development host has one Intel Core i7-8650U with 4 physical cores and 8 logical CPUs. The sequential build uses GCC 15.2.0, GNU Make 4.4.1, and the default flags `-O3 -Wall -Wextra -Wpedantic -std=c17`. GCC defines `_OPENMP=201511` when invoked with `-fopenmp`. Neither `mpicc` nor `mpiexec` was on `PATH` during this check. Record the MPI runtime and actual host configuration when running the parallel benchmarks.

A single baseline run with `./build/seq 10000000000 42` counted 7,853,999,959 hits, estimated π as 3.1415999836, and took 57.0013 seconds. Use repeated measurements on the same host as the parallel runs when calculating speedup.
