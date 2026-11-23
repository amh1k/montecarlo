#include "common.h"

#include <mpi.h>

int main(int argc, char *argv[]) {
    if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
        return 1;
    }

    int rank;
    int ranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);

    // A zero trial count tells every rank that argument validation failed.
    uint64_t inputs[2] = {0, 0};
    if (rank == 0 && !parse_arguments(argc, argv, &inputs[0], &inputs[1])) {
        inputs[0] = 0;
    }
    MPI_Bcast(inputs, 2, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    uint64_t trials = inputs[0];
    uint64_t seed = inputs[1];
    if (trials == 0) {
        MPI_Finalize();
        return 1;
    }

    uint64_t local_trials = trials / (uint64_t)ranks;
    if ((uint64_t)rank < trials % (uint64_t)ranks) {
        ++local_trials;
    }
    uint64_t state = worker_seed(seed, (uint32_t)rank, 0);

    MPI_Barrier(MPI_COMM_WORLD);
    double start = MPI_Wtime();
    uint64_t local_hits = 0;
    for (uint64_t trial = 0; trial < local_trials; ++trial) {
        local_hits += sample_hit(&state);
    }

    uint64_t hits = 0;
    MPI_Reduce(&local_hits, &hits, 1, MPI_UINT64_T, MPI_SUM, 0, MPI_COMM_WORLD);
    double local_seconds = MPI_Wtime() - start;
    double seconds = 0.0;
    MPI_Reduce(&local_seconds, &seconds, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        write_csv_header(stdout);
        write_result(stdout, "mpi", trials, seed, ranks, 1, hits, seconds);
    }
    return MPI_Finalize() == MPI_SUCCESS ? 0 : 1;
}
