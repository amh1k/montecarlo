#include "common.h"

#include <mpi.h>
#include <omp.h>

int main(int argc, char *argv[]) {
    int provided = MPI_THREAD_SINGLE;
    if (MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided) !=
        MPI_SUCCESS) {
        return 1;
    }

    int rank;
    int ranks;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);

    int supports_funneled = provided >= MPI_THREAD_FUNNELED;
    int all_support_funneled = 0;
    MPI_Allreduce(&supports_funneled, &all_support_funneled, 1, MPI_INT,
                  MPI_MIN, MPI_COMM_WORLD);
    if (!all_support_funneled) {
        if (rank == 0) {
            fprintf(stderr, "MPI implementation does not provide "
                            "MPI_THREAD_FUNNELED.\n");
        }
        MPI_Finalize();
        return 1;
    }

    uint64_t trials = 0;
    uint64_t seed = 0;
    int local_valid = parse_arguments_quiet(argc, argv, &trials, &seed) ? 1 : 0;
    uint64_t root_inputs[2] = {trials, seed};
    MPI_Bcast(root_inputs, 2, MPI_UINT64_T, 0, MPI_COMM_WORLD);
    local_valid = local_valid && trials == root_inputs[0] && seed == root_inputs[1];

    int all_valid = 0;
    MPI_Allreduce(&local_valid, &all_valid, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
    if (!all_valid) {
        if (rank == 0) {
            if (local_valid) {
                fprintf(stderr, "All MPI ranks must use the same valid trial count and seed.\n");
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
    int threads = 1;

    MPI_Barrier(MPI_COMM_WORLD);
    double start = MPI_Wtime();

    #pragma omp parallel default(none) shared(seed, rank, local_trials, threads) reduction(+:local_hits)
    {
        uint64_t state = worker_seed(seed, (uint32_t)rank,
                                     (uint32_t)omp_get_thread_num());

        #pragma omp single nowait
        threads = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (uint64_t trial = 0; trial < local_trials; ++trial) {
            local_hits += sample_hit(&state);
        }
    }

    MPI_Reduce(&local_hits, &total_hits, 1, MPI_UINT64_T, MPI_SUM, 0,
               MPI_COMM_WORLD);
    double local_seconds = MPI_Wtime() - start;
    double max_seconds = 0.0;
    MPI_Reduce(&local_seconds, &max_seconds, 1, MPI_DOUBLE, MPI_MAX, 0,
               MPI_COMM_WORLD);

    int min_threads;
    int max_threads;
    MPI_Allreduce(&threads, &min_threads, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
    MPI_Allreduce(&threads, &max_threads, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    if (min_threads != max_threads) {
        if (rank == 0) {
            fprintf(stderr, "All MPI ranks must use the same OpenMP team size.\n");
        }
        MPI_Finalize();
        return 1;
    }

    if (rank == 0) {
        write_csv_header(stdout);
        write_result(stdout, "hybrid", trials, seed, ranks, threads, total_hits,
                     max_seconds);
    }

    MPI_Finalize();
    return 0;
}
