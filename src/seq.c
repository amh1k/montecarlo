#define _POSIX_C_SOURCE 200809L

#include "common.h"

#include <time.h>

static int get_time(struct timespec *time) {
#ifdef CLOCK_MONOTONIC
    return clock_gettime(CLOCK_MONOTONIC, time);
#else
    return timespec_get(time, TIME_UTC) == TIME_UTC ? 0 : -1;
#endif
}

int main(int argc, char *argv[]) {
    uint64_t trials;
    uint64_t seed;
    if (!parse_arguments(argc, argv, &trials, &seed)) {
        return 1;
    }

    uint64_t state = worker_seed(seed, 0, 0);
    struct timespec start;
    if (get_time(&start) != 0) {
        perror("get_time");
        return 1;
    }

    uint64_t hits = 0;
    for (uint64_t trial = 0; trial < trials; ++trial) {
        hits += sample_hit(&state);
    }

    struct timespec end;
    if (get_time(&end) != 0) {
        perror("get_time");
        return 1;
    }

    double seconds = (double)(end.tv_sec - start.tv_sec) +
                     (double)(end.tv_nsec - start.tv_nsec) / 1e9;
    write_csv_header(stdout);
    write_result(stdout, "seq", trials, seed, 1, 1, hits, seconds);
    return 0;
}
