#include <math.h>
#include <stdlib.h>
#include <omp.h>
#include "monte_carlo.h"
#include "rng.h"

MonteCarloResult monte_carlo_classic(const TestFunction *test_function, long long n,
                                     uint64_t seed, int thread_count) {
    double interval_length = test_function->interval_end - test_function->interval_start;
    double sum = 0.0;
    double sum_of_squares = 0.0;

    omp_set_num_threads(thread_count);
    double t0 = omp_get_wtime();
    // Każdy wątek liczy swój fragment pętli i ma swoje własne zmienne sum i sum_of_squares, 
    // Na końcu pętli automatycznie dodaje (redukuje) wyniki ze wszystkich wątków
    #pragma omp parallel for reduction(+:sum,sum_of_squares) schedule(static)
    for (long long i = 0; i < n; i++) {
        // Losowanie punktu x w przedziale [a, b]
        double x = test_function->interval_start + rng_uniform(seed, (uint64_t)i) * interval_length;
        double value = test_function->function(x); // f(x)
        //suma wartości funkcji w wylosowanych punktach
        sum += value;
        sum_of_squares += value * value; // kwadraty do liczenia wariancji
    }
    double t1 = omp_get_wtime();

    double mean = sum / n;
    double variance = (sum_of_squares - sum * sum / n) / (n - 1);

    MonteCarloResult result;
    result.estimate = interval_length * mean;
    result.standard_error = interval_length * sqrt(variance / n);
    result.time_seconds = t1 - t0;
    return result;
}

MonteCarloResult monte_carlo_stratified(const TestFunction *test_function, long long n,
                                        int layer_count, uint64_t seed, int thread_count) {
    long long samples_per_layer = n / layer_count;
    double layer_width = (test_function->interval_end - test_function->interval_start) / layer_count;

    // Sumy wartości funkcji i ich kwadratów dla każdej warstwy (scalane z wątków)
    double *layer_sums = calloc(layer_count, sizeof(double));
    double *layer_sums_of_squares = calloc(layer_count, sizeof(double));

    omp_set_num_threads(thread_count);
    double t0 = omp_get_wtime();
    #pragma omp parallel
    {
        // Lokalne sumy wątku, żeby nie blokować na każdej próbce
        double *local_sums = calloc(layer_count, sizeof(double));
        double *local_sums_of_squares = calloc(layer_count, sizeof(double));

        #pragma omp for schedule(static)
        for (long long j = 0; j < n; j++) {
            int layer = (int)(j / samples_per_layer);
            double x = test_function->interval_start
                     + (layer + rng_uniform(seed, (uint64_t)j)) * layer_width;
            double value = test_function->function(x);
            local_sums[layer] += value;
            local_sums_of_squares[layer] += value * value;
        }

        #pragma omp critical
        {
            for (int layer = 0; layer < layer_count; layer++) {
                layer_sums[layer] += local_sums[layer];
                layer_sums_of_squares[layer] += local_sums_of_squares[layer];
            }
        }

        free(local_sums);
        free(local_sums_of_squares);
    }
    double t1 = omp_get_wtime();

    // Estymata = sum_s w * mean_s, wariancja = sum_s w^2 * var_s / n_s
    double estimate = 0.0;
    double variance = 0.0;
    for (int layer = 0; layer < layer_count; layer++) {
        double layer_mean = layer_sums[layer] / samples_per_layer;
        double layer_variance = (layer_sums_of_squares[layer]
                                 - layer_sums[layer] * layer_sums[layer] / samples_per_layer)
                                / (samples_per_layer - 1);
        estimate += layer_width * layer_mean;
        variance += layer_width * layer_width * layer_variance / samples_per_layer;
    }

    free(layer_sums);
    free(layer_sums_of_squares);

    MonteCarloResult result;
    result.estimate = estimate;
    result.standard_error = sqrt(variance);
    result.time_seconds = t1 - t0;
    return result;
}
