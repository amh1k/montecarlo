# Issue #6 implementation plan

Goal: retain reproducible measured scaling and accuracy results from all four modes.
Spec: https://github.com/amh1k/montecarlo/issues/6; depends on completed #5.

Use Python standard-library tooling around the existing C executables. Preserve
raw program CSV, exact commands and environment, CPU placement, machine/toolchain
metadata and repetitions. Pin workers to distinct physical cores. Benchmark at
10^10 trials with seed 42, after pilots; sweep smaller trial counts and seeds for
accuracy. Execute configurations sequentially to avoid competing experiments.

- [x] Implement scripts/benchmark.py: metadata capture, pilots, scaling and accuracy
  stages, strict CSV validation, incremental durable output, explicit failure records.
- [x] Add tests/test_benchmark.py for malformed results, configuration limits,
  placement and runner failure handling. Run actual small cases in every mode.
- [x] Run measured experiments on this host; retain raw output and commands in results/.
- [x] Document reproduction, observed limitations and completion evidence; review,
  commit, push and open a PR referencing #6.

Review focus: reject wrong worker counts and malformed CSV; never overwrite prior
experiments; fail on missing binaries/runtime; require distinct physical cores;
retain completed runs if a later invocation fails. Full-scale results are measured,
not extrapolated; pilots only forecast runtime.
