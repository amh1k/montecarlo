# Software requirements and acceptance criteria

The proposal defines the research question for PDC Project #7. How does distributing a fixed Monte Carlo workload across threads, processes, or both affect runtime and efficiency? How does increasing the trial count affect estimation error? The group runs the experiments. The instructor needs enough evidence to reproduce a run and assess the conclusions.

## Scope from the proposal

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R1 | Estimate π from uniform points in the unit square. | For a known set of points, count those satisfying x² + y² ≤ 1 and verify the reported estimate equals 4 × hits / trials within output rounding. |
| R2 | Provide sequential C, OpenMP, MPI and hybrid MPI + OpenMP runs. | Launch each mode on the same workload. Show worker configuration and exactly N completed trials, including when N is unevenly divisible by the number of processes. |
| R3 | Support the baseline of 10¹⁰ trials. | Retain a completed baseline result for each mode with trial count, elapsed time and estimate. Check that counts above the 32-bit range survive aggregation and reporting. |
| R4 | Measure runtime, speedup and efficiency as worker count varies. | Provide raw timings, worker counts and graphs. At equal N, compute speedup as sequential time divided by parallel time, and efficiency as speedup divided by total workers. Discuss scalability and communication costs. |
| R5 | Evaluate accuracy versus trial count. | Compare estimates with π across several trial counts and seeds. Discuss the expected inverse-square-root error trend using aggregate error. |

A 10¹¹-trial experiment depends on available compute. Option pricing is a separate extension if time permits.

## Proposed quality criteria

- A repeated run with the same executable, seed and worker layout reproduces the hit count. Changing the layout may change it. A seed controls sampling, while elapsed time remains a measurement.
- Each worker has private random generator state. The sampling loop uses bounded memory per worker so increasing N can increase runtime without requiring storage for N points.
- Invalid trial counts produce a clear error and a failed exit. In MPI modes all ranks terminate, including ranks with no assigned work on valid small runs.
- A reader can reproduce a small run from the repository instructions and identify the machine, compiler, seed, workload and worker layout used for each reported comparison.

## Submission acceptance

By Wednesday, 25 November 2026, the group leader submits the GitHub repository link, complete PDF report and a 2–3 minute screen recording with voiceover demonstrating the working project and its major components. The submission comment lists every member's name and roll number. The implementation plan includes the roster and final checks.
