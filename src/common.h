#ifndef MONTECARLO_COMMON_H
#define MONTECARLO_COMMON_H

#include <inttypes.h>
#include <stdbool.h>
#include <stdio.h>

static inline bool parse_unsigned(const char *text, uint64_t *value) {
    if (*text == '\0') {
        return false;
    }

    uint64_t parsed = 0;
    for (; *text != '\0'; ++text) {
        if (*text < '0' || *text > '9') {
            return false;
        }
        unsigned digit = (unsigned)(*text - '0');
        if (parsed > (UINT64_MAX - digit) / 10) {
            return false;
        }
        parsed = parsed * 10 + digit;
    }

    *value = parsed;
    return true;
}

static inline bool parse_arguments_quiet(int argc, char *argv[],
                                         uint64_t *trials, uint64_t *seed) {
    return argc == 3 && parse_unsigned(argv[1], trials) && *trials > 0 &&
           parse_unsigned(argv[2], seed);
}

static inline bool parse_arguments(int argc, char *argv[], uint64_t *trials,
                                   uint64_t *seed) {
    if (parse_arguments_quiet(argc, argv, trials, seed)) {
        return true;
    }

    fprintf(stderr, "Usage: %s TRIALS SEED\n"
                    "TRIALS must be a positive 64-bit unsigned integer. "
                    "SEED must be a 64-bit unsigned integer.\n", argv[0]);
    return false;
}

static inline bool inside_quarter_circle(double x, double y) {
    return x * x + y * y <= 1.0;
}

// SplitMix64 finalizer (Stafford Mix13).
static inline uint64_t mix_bits(uint64_t value) {
    value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

static inline uint64_t worker_seed(uint64_t seed, uint32_t rank, uint32_t thread_id) {
    uint64_t worker = ((uint64_t)rank << 32) | thread_id;
    // Mix the worker ID first so flipping a seed bit does not just swap workers.
    // mix_bits(0) is zero, preserving the sequential stream for worker zero.
    return mix_bits(seed + mix_bits(worker));
}

static inline double uniform_coordinate(uint64_t *state) {
    *state += UINT64_C(0x9e3779b97f4a7c15);
    // Map the top 53 bits to a double in [0, 1).
    return (double)(mix_bits(*state) >> 11) * 0x1p-53;
}

static inline bool sample_hit(uint64_t *state) {
    double x = uniform_coordinate(state);
    double y = uniform_coordinate(state);
    return inside_quarter_circle(x, y);
}

static inline void write_result(FILE *out, const char *mode, uint64_t trials,
                                uint64_t seed, int ranks, int threads_per_rank,
                                uint64_t hits, double seconds) {
    double estimate = 4.0 * (double)hits / (double)trials;
    fprintf(out, "%s,%" PRIu64 ",%" PRIu64 ",%d,%d,%" PRIu64 ",%.17g,%.17g\n",
            mode, trials, seed, ranks, threads_per_rank, hits, estimate, seconds);
}

static inline void write_csv_header(FILE *out) {
    fputs("mode,trials,seed,ranks,threads_per_rank,hits,pi_estimate,seconds\n", out);
}

#endif
