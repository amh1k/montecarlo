#include "../src/common.h"

int main(void) {
    // Equal-sized workers reused the same four streams for seeds 42 and 43.
    for (uint32_t i = 0; i < 4; ++i) {
        for (uint32_t j = 0; j < 4; ++j) {
            if (worker_seed(42, 0, i) == worker_seed(43, 0, j)) {
                fprintf(stderr, "Seeds 42 and 43 share a worker stream\n");
                return 1;
            }
        }
    }
    return 0;
}
