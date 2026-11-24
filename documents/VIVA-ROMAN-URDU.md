# Monte Carlo π estimation — Roman Urdu viva guide

## 1. Project kis problem ko solve kar raha hai?

Is project ke do sawal hain. Pehla, random points ki madad se π ka estimate kaise nikal sakte hain aur trials barhane se error kaise badalta hai? Doosra, agar **utne hi trials** ek worker ki jagah multiple threads ya processes mein baant dein, to runtime kitna badalta hai?

π yahan experiment ke liye acha example hai kyun ke iska reference value maloom hai aur har trial alag se calculate ho sakta hai. Is liye hum estimate ka error bhi measure kar sakte hain aur workers ke darmiyan kaam bhi baant sakte hain. Project ka maqsad π ke digits nikalne ka sab se tez tareeqa banana nahi hai. Maqsad ek hi workload par parallel execution ko samajhna aur measure karna hai.

**Viva mein shuru aise karo:** “Hum unit square mein random points generate karte hain, phir quarter circle ke andar walay points count karte hain. Yehi calculation chaar modes mein chalate hain aur dekhte hain ke trials baantne se time aur efficiency kitni change hoti hai.”

## 2. Program ke andar kya ho raha hai?

`TRIALS, SEED → random points → hit count → sab workers ke hits ka sum → π estimate aur elapsed time → CSV`

Unit square ka area `1` hai. Radius `1` ke quarter circle ka area `π/4` hai. Agar points uniformly sample hon to ek point ke andar aane ki probability `π/4` hai. Isi liye `hits / trials` se `π/4` ka estimate milta hai aur `4.0 * hits / trials` se π ka.

```c
return x * x + y * y <= 1.0;
```

`x*x + y*y` origin se squared distance hai. Radius `1` hai, is liye square root calculate karne ki zaroorat nahi. `(0,0)` aur `(1,0)` hits hain, `(0.9,0.9)` miss hai. Agar 10 trials mein 8 hits hon to estimate `3.2` hai. Chhote sample mein bada error normal hai.

## 3. Shared code kaise kaam karta hai?

Chaaron executables [src/common.h](../src/common.h) ke helpers use karte hain.

| Code | Is line ya function ka kaam |
|---|---|
| `#ifndef`, `#define`, `#endif` | Header guard ek compilation unit mein definitions ko do baar include hone se bachata hai. |
| `static inline` | Helper is compilation unit tak limited rehta hai. Compiler call ko inline kar sakta hai. |
| `parse_unsigned` | String digit by digit parhta hai. Empty input, non-digit aur overflow reject karta hai. `\0` string ka end hai. |
| `parsed > (UINT64_MAX - digit) / 10` | Multiply aur add karne se **pehle** check karta hai ke agla `parsed * 10 + digit` 64-bit range se bahar to nahi jayega. |
| `*value = parsed` | Pointer ke zariye parsed number caller ke variable mein likhta hai. |
| `argc == 3 && ...` | `argv[0]` program ka naam hai, `argv[1]` trials aur `argv[2]` seed. `&&` short-circuit karta hai, is liye ghalat argument count par aagay access nahi hota. Trials positive aur seed zero bhi ho sakta hai. |
| `parse_arguments` | Shared validation ko call karta hai aur invalid input par `stderr` mein usage print karta hai. MPI modes quiet version use karte hain taake error rank zero se aaye. |
| `mix_bits` | SplitMix64 finalizer XOR, right shifts aur fixed multipliers se bits mix karta hai. Unsigned arithmetic ka wraparound yahan intentional hai. |
| `((uint64_t)rank << 32) \| thread_id` | Rank upper 32 bits aur thread ID lower 32 bits mein pack hoti hai. Dono milkar worker ko identify karte hain. |
| `worker_seed` | Seed aur worker ID mix karke worker ki starting RNG state banata hai. Worker `(0,0)` ka stream sequential aur one-worker parallel run mein same rehta hai. |
| `uniform_coordinate` | State update karta hai, mixed value ki top 53 bits leta hai aur `0x1p-53` yani `2^-53` se scale karke `[0,1)` mein `double` banata hai. |
| `sample_hit(&state)` | Ek hi worker ki state se do coordinates leta hai aur `bool` hit return karta hai. `hits += ...` mein `true` ka matlab 1 aur `false` ka matlab 0 hai. |
| `write_result` | Floating-point division se estimate banata hai. `PRIu64` 64-bit unsigned numbers ka portable format hai, `%.17g` floating values ko 17 significant digits tak likhta hai. |
| `write_csv_header` | CSV columns ke naam ek baar print karta hai. Successful invocation mein header aur ek result row hoti hai. |

`uint64_t` trials aur hits ke liye chahiye kyun ke `10,000,000,000` trials 32-bit unsigned maximum `4,294,967,295` se zyada hain. Har worker sirf apni state aur counter rakhta hai. Points ka array banane ki zaroorat nahi.

## 4. Chaar modes ka execution flow

### Sequential (`seq.c`)

1. `_POSIX_C_SOURCE 200809L` POSIX declarations expose karta hai. `<time.h>` se `timespec` aur clock API milti hai.
2. `parse_arguments(..., &trials, &seed)` input validate karta hai. `return 1` failure hai aur `return 0` success.
3. `worker_seed(seed, 0, 0)` single worker ki state banata hai. `CLOCK_MONOTONIC` sampling se pehle start time deta hai. Clock call fail ho to `perror` reason print karta hai.
4. Loop exactly `trials` baar chalta hai. Har dafa `sample_hit` state update karta hai aur hit ya miss deta hai.
5. End time mein se start time minus hota hai. Seconds ka difference direct add hota hai aur nanoseconds ka difference `1e9` se divide hota hai. Print hone wala layout `1 rank × 1 thread` hai.

[Sequential source](../src/seq.c)

### OpenMP (`omp.c`)

```c
#pragma omp parallel default(none) shared(trials, seed, threads) reduction(+:hits)
```

1. `omp_get_wtime()` parallel block se pehle start time leta hai. `parallel` threads ki team banata hai. `default(none)` ke saath relevant outer variables ka sharing explicitly batana parta hai.
2. `trials` aur `seed` sab threads read karte hain. Har thread block ke andar apni `state` banata hai aur `omp_get_thread_num()` se apni ID leta hai.
3. `single nowait` mein team ka sirf ek thread actual team size record karta hai. Baqi threads ko is assignment par rukna nahi parta. `threads` block khatam hone ke baad read hota hai.
4. `omp for schedule(static)` iterations pehle se threads mein baant deta hai. Har trial ka kaam lagbhag same hai. `reduction(+:hits)` har thread ko private counter deta hai aur akhir mein sab counts add karta hai. Shared `hits++` ki race is tarah avoid hoti hai.
5. Team join hone ke baad timer stop hota hai. Runtime mein team start, sampling aur reduction shamil hain.

[OpenMP source](../src/omp.c)

### MPI (`mpi.c`)

1. `MPI_Init` MPI setup karta hai. `MPI_COMM_WORLD` sab launched ranks ka group hai. `MPI_Comm_rank` process ki ID aur `MPI_Comm_size` total ranks deta hai.
2. Har rank input validate karta hai. `MPI_Bcast` rank zero ke trials aur seed sab ko deta hai. Ranks apni values unse compare karte hain. `MPI_Allreduce` with `MPI_MIN` sab ke `0/1` flags ka minimum **har rank** ko deta hai. Ek rank invalid ho to sab finalize karke exit karte hain. Ye is liye zaroori hai ke koi rank akela aagay collective call mein wait na karta rahe.
3. `quotient = trials / ranks` aur `remainder = trials % ranks`. Pehle `remainder` ranks ko ek extra trial milta hai. `10 / 3` ka split `4, 3, 3` hai. `2 / 4` ka split `1, 1, 0, 0` hai. Zero-work ranks ka sampling loop skip hota hai, lekin woh collectives mein phir bhi participate karte hain.
4. `MPI_Barrier` ke baad har rank `MPI_Wtime()` se apna timer start karta hai. Rank-specific RNG state ke saath local sampling hoti hai.
5. `MPI_Reduce` with `MPI_SUM` sab `local_hits` rank zero par jama karta hai. `MPI_UINT64_T` C counter ka MPI datatype hai. Har rank hit reduction ke baad apna elapsed time leta hai. Alag `MPI_MAX` reduction slowest measured rank ka time root tak pohanchata hai. Time wali reduction khud reported interval mein shamil nahi hai.
6. Sirf rank zero CSV print karta hai. Sab ranks `MPI_Finalize` call karte hain.

[MPI source](../src/mpi.c)

### Hybrid (`hybrid.c`)

1. `MPI_Init_thread` se `MPI_THREAD_FUNNELED` request hota hai. Program multi-threaded chal sakta hai aur MPI calls sirf woh thread karti hai jis ne MPI initialize kiya. `provided` check hota hai aur flags sab ranks par reduce hote hain.
2. Input validation aur rank-level split MPI mode jaisa hai. Farq ye hai ke **har rank apne** `local_trials` OpenMP threads mein dobara divide karta hai. `2 ranks × 2 threads` ka matlab 4 workers hai.
3. `worker_seed(seed, rank, thread_id)` dono IDs use karta hai. OpenMP pehle thread counts ko rank ke `local_hits` mein add karta hai. Parallel block ke baad `MPI_Reduce` rank counts ko global `total_hits` mein add karta hai.
4. `MPI_MIN` aur `MPI_MAX` se actual team sizes compare hote hain. Agar sizes different hon to program error deta hai kyun ke CSV mein `threads_per_rank` ek hi value hai. Valid layout par root row print karta hai aur sab finalize karte hain.

[Hybrid source](../src/hybrid.c)

## 5. Build se report tak

Laptop Windows par tha. GCC, Make aur MPI Ubuntu WSL ke andar chale. Ye commands Ubuntu terminal mein chalti hain.

```sh
make seq omp mpi hybrid
./build/seq 1000000 42
OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE ./build/omp 1000000 42
mpiexec -n 4 ./build/mpi 1000000 42
OMP_NUM_THREADS=2 OMP_DYNAMIC=FALSE mpiexec -n 2 ./build/hybrid 1000000 42
```

Makefile sequential aur OpenMP ke liye C compiler aur MPI modes ke liye `mpicc` use karta hai. `-fopenmp` OpenMP directives enable karta hai. `mpiexec -n` rank count set karta hai, `OMP_NUM_THREADS` har process ki requested team size. `OMP_DYNAMIC=FALSE` dynamic team adjustment band karta hai.

| File | Output tak iska role |
|---|---|
| [`benchmark.py`](../scripts/benchmark.py) | Workload aur worker layouts select karta hai, physical cores ke hisaab se placement set karta hai, executables chalata hai aur CSV validate karta hai. `raw.csv`, `runs.jsonl` aur metadata save hote hain. `COMPLETE` successful run ke akhir mein likha jata hai. |
| [`summarize.py`](../scripts/summarize.py) | Equal trials aur seed wali scaling timings compare karta hai. Accuracy ke liye multiple seeds ki errors aggregate karta hai. |
| [`plot_results.py`](../scripts/plot_results.py) | Summaries se runtime, speedup, efficiency aur accuracy graphs banata hai. |
| [`build_report.py`](build_report.py) | Recorded results aur graphs ko final PDF mein assemble karta hai. |

## 6. Results ko viva mein kaise explain karein?

- **Speedup** `T_seq / T_parallel` hai. **Efficiency** `speedup / (ranks × threads_per_rank)` hai. Comparison ke liye same trials aur seed use hue.
- Four-core WSL2 host par 10 layouts ki do retained scaling repetitions per layout hui. Har scaling run mein 10 billion trials the. Reported medians sequential `129.03 s`, four-thread OpenMP `29.84 s`, four-rank MPI `31.70 s` aur hybrid `2×2` `35.02 s` the.
- Four-thread OpenMP ka measured speedup `129.03 / 29.84 ≈ 4.32` hai. Isko general superlinear scaling ka proof mat bolo. Excluded third sequential run `69.08 s` tha, jo baseline ki variability dikhata hai. MPI ranks ek hi host par the, is liye result network scaling establish nahi karta.
- Accuracy mein pehle har seed ki error `estimate − π` li, phir **RMSE** yani squared errors ke mean ka square root nikala. Ideal sampling mein expected error ka scale `1/√N` hai. `N` 100 guna barhe to expected scale takreeban 10 guna kam hota hai. Har individual seed ka error har step par kam hona zaroori nahi.
- Clean-build check mein same seed `42`, one million trials aur ek worker ke saath chaaron modes ne **785,674 hits** diye. MPI aur hybrid ne uneven splits `10/3` aur `2/4` bhi complete kiye. Ye correctness checks hain. Large benchmark timings alag experimental evidence hain.

## 7. Viva practice aur references

1. Code dekhe baghair `10 trials, 3 ranks` ka workload split karo. Phir batao har rank ka local result global result mein kaise jata hai.
2. Hybrid `2×2` ko do levels par draw karo. Har rank ke do thread counters ko pehle OpenMP aur phir MPI se add karke dikhao.
3. Samjhao ke `MPI_Bcast`, `MPI_Reduce` aur `MPI_Allreduce` mein result kis ko milta hai.
4. Agar professor random generator par ruk jaye to `worker_seed → uniform_coordinate → sample_hit` ka flow bolo. Same input aur layout repeat karke hits verify karo.
5. Har mode ke liye batao timer kahan start aur stop hota hai aur CSV kaun print karta hai.

- [Build aur run commands](../README.md)
- [Requirements](REQUIREMENTS.md) · [Architecture](ARCHITECTURE.md) · [Final report](Monte-Carlo-Report.pdf)
- [Experiment method aur limitations](../results/README.md) · [Raw CSV](../results/2026-11-23/raw.csv) · [Scaling summary](../results/2026-11-23/scaling_summary.csv) · [Accuracy summary](../results/2026-11-23/accuracy_summary.csv) · [Figures](../results/figures/)
