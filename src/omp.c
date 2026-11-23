#include "common.h"

#include <omp.h>

int main(int argc, char *argv[]) {
    uint64_t trials;
    uint64_t seed;
    if (!parse_arguments(argc, argv, &trials, &seed)) {
        return 1;
    }

    uint64_t hits = 0;
    int threads = 1;
    double start = omp_get_wtime();

    #pragma omp parallel default(none) shared(trials, seed, threads) reduction(+:hits)
    {
        uint64_t state = worker_seed(seed, 0, (uint32_t)omp_get_thread_num());

        #pragma omp single nowait
        threads = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (uint64_t trial = 0; trial < trials; ++trial) {
            hits += sample_hit(&state);
        }
    }

    double seconds = omp_get_wtime() - start;
    write_csv_header(stdout);
    write_result(stdout, "omp", trials, seed, 1, threads, hits, seconds);
    return 0;
}
