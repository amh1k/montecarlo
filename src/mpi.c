#include "common.h"

#include <mpi.h>

int main(int argc, char *argv[]) {
    int rank;
    int ranks;
    int init_status = MPI_Init(&argc, &argv);
    if (init_status != MPI_SUCCESS) {
        return 1;
    }

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);

    uint64_t trials = 0;
    uint64_t seed = 0;
    int local_valid = parse_arguments_quiet(argc, argv, &trials, &seed) ? 1 : 0;
    int all_valid = 0;
    MPI_Allreduce(&local_valid, &all_valid, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
    if (!all_valid) {
        if (rank == 0) {
            if (local_valid) {
                fprintf(stderr, "Invalid arguments supplied to one or more MPI ranks.\n");
            } else {
                fprintf(stderr, "Usage: %s TRIALS SEED\n"
                                "TRIALS must be a positive 64-bit unsigned integer. "
                                "SEED must be a 64-bit unsigned integer.\n", argv[0]);
            }
        }
        MPI_Finalize();
        return 1;
    }

    uint64_t quotient = trials / (uint64_t)ranks;
    uint64_t remainder = trials % (uint64_t)ranks;
    uint64_t local_trials = quotient + ((uint64_t)rank < remainder ? 1 : 0);
    uint64_t local_hits = 0;
    uint64_t total_hits = 0;

    MPI_Barrier(MPI_COMM_WORLD);
    double start = MPI_Wtime();

    uint64_t state = worker_seed(seed, (uint32_t)rank, 0);
    for (uint64_t trial = 0; trial < local_trials; ++trial) {
        local_hits += sample_hit(&state);
    }

    MPI_Reduce(&local_hits, &total_hits, 1, MPI_UINT64_T, MPI_SUM, 0,
               MPI_COMM_WORLD);
    double local_seconds = MPI_Wtime() - start;
    double max_seconds = 0.0;
    MPI_Reduce(&local_seconds, &max_seconds, 1, MPI_DOUBLE, MPI_MAX, 0,
               MPI_COMM_WORLD);

    if (rank == 0) {
        write_csv_header(stdout);
        write_result(stdout, "mpi", trials, seed, ranks, 1, total_hits,
                     max_seconds);
    }

    MPI_Finalize();
    return 0;
}
