#define _POSIX_C_SOURCE 200809L

#include "common.h"

#include <time.h>

int main(int argc, char *argv[]) {
    uint64_t trials;
    uint64_t seed;
    if (argc != 3 || !parse_unsigned(argv[1], &trials) || trials == 0 ||
        !parse_unsigned(argv[2], &seed)) {
        fprintf(stderr, "Usage: %s TRIALS SEED\n"
                        "TRIALS must be a positive 64-bit unsigned integer. "
                        "SEED must be a 64-bit unsigned integer.\n", argv[0]);
        return 1;
    }

    uint64_t state = worker_seed(seed, 0, 0);
    struct timespec start;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
        perror("clock_gettime");
        return 1;
    }

    uint64_t hits = 0;
    for (uint64_t trial = 0; trial < trials; ++trial) {
        hits += sample_hit(&state);
    }

    struct timespec end;
    if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
        perror("clock_gettime");
        return 1;
    }

    double seconds = (double)(end.tv_sec - start.tv_sec) +
                     (double)(end.tv_nsec - start.tv_nsec) / 1e9;
    write_result(stdout, "seq", trials, seed, 1, 1, hits, seconds);
    return 0;
}
