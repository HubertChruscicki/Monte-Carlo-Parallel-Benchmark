#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
#include "monte_carlo.h"
#include "rng.h"

// Losowanie próbki o indeksie j w warstwie zaczynającej się od layer_start, szerokości width.
// Tryb RNG_ONLY zwraca samo u (bez f(x)), żeby zmierzyć koszt generatora.
static inline double sample_value(const TestFunction *tf, double layer_start, double width,
                                  uint64_t seed, long long j, TimingMode timing) {
    double u = rng_uniform(seed, (uint64_t)j);
    if (timing == TIMING_RNG_ONLY) {
        return u;
    }
    return tf->function(layer_start + u * width);
}

// Wspólny silnik dla wszystkich wariantów. Klasyczne Monte Carlo to przypadek layer_count = 1.
// Próbki każdej warstwy dzielimy na partie po `batch` próbek. Dla każdej partii liczymy sumę
// i sumę kwadratów wartości, a dopiero potem scalamy partie w estymatę i wariancję.
// Równoległość OpenMP: partie rozdzielane między wątki (schedule static), każda partia liczona
// w całości przez jeden wątek. Liczba partii ogranicza maksymalne równoległe wykorzystanie.
static MonteCarloResult run_batched(const TestFunction *tf, long long n, int layer_count,
                                    long long batch, uint64_t seed, int thread_count,
                                    TimingMode timing, int use_openmp) {
    long long samples_per_layer = n / layer_count;
    double width = (tf->interval_end - tf->interval_start) / layer_count;
    long long batches_per_layer = (samples_per_layer + batch - 1) / batch;
    long long total_batches = batches_per_layer * layer_count;

    double *batch_sum = malloc((size_t)total_batches * sizeof(double));
    double *batch_sum_sq = malloc((size_t)total_batches * sizeof(double));
    if (batch_sum == NULL || batch_sum_sq == NULL) {
        fprintf(stderr, "ERROR: brak pamięci na statystyki partii\n");
        exit(1);
    }

    // Pętla próbkowania: każdy wątek dostaje część partii i liczy dla nich sumy lokalnie.
    // Jedna sekcja równoległa dla całej pętli, bez bariery po każdej partii.
    double t0 = omp_get_wtime();
    #pragma omp parallel for if(use_openmp) num_threads(thread_count) schedule(static)
    for (long long b = 0; b < total_batches; b++) {
        long long layer = b / batches_per_layer;
        long long chunk = b % batches_per_layer;
        long long layer_end = (layer + 1) * samples_per_layer;
        long long first = layer * samples_per_layer + chunk * batch;
        long long last = first + batch;
        if (last > layer_end) {
            last = layer_end;
        }
        double layer_start = tf->interval_start + (double)layer * width;
        double part_sum = 0.0;
        double part_sum_sq = 0.0;
        for (long long j = first; j < last; j++) {
            double value = sample_value(tf, layer_start, width, seed, j, timing);
            part_sum += value;
            part_sum_sq += value * value;
        }
        batch_sum[b] = part_sum;
        batch_sum_sq[b] = part_sum_sq;
    }
    double t1 = omp_get_wtime();

    // Scalanie partii: estymata = Σ w·μ_s, wariancja = Σ w²·s_s²/n_s
    double estimate = 0.0;
    double variance = 0.0;
    for (long long layer = 0; layer < layer_count; layer++) {
        double layer_sum = 0.0;
        double layer_sum_sq = 0.0;
        for (long long chunk = 0; chunk < batches_per_layer; chunk++) {
            long long b = layer * batches_per_layer + chunk;
            layer_sum += batch_sum[b];
            layer_sum_sq += batch_sum_sq[b];
        }
        double layer_mean = layer_sum / samples_per_layer;
        double layer_variance = (layer_sum_sq - layer_sum * layer_sum / samples_per_layer)
                                / (samples_per_layer - 1);
        estimate += width * layer_mean;
        variance += width * width * layer_variance / samples_per_layer;
    }
    double t2 = omp_get_wtime();

    free(batch_sum);
    free(batch_sum_sq);

    MonteCarloResult result;
    result.estimate = estimate;
    result.standard_error = sqrt(variance);
    result.time_core_seconds = t1 - t0;
    result.time_agg_seconds = t2 - t1;
    return result;
}

MonteCarloResult monte_carlo_classic(const TestFunction *test_function, long long n,
                                     long long batch, uint64_t seed, int thread_count,
                                     TimingMode timing) {
    return run_batched(test_function, n, 1, batch, seed, thread_count, timing, 1);
}

MonteCarloResult monte_carlo_stratified(const TestFunction *test_function, long long n,
                                        int layer_count, long long batch, uint64_t seed,
                                        int thread_count, TimingMode timing) {
    return run_batched(test_function, n, layer_count, batch, seed, thread_count, timing, 1);
}

MonteCarloResult monte_carlo_sequential(const TestFunction *test_function, long long n,
                                        int layer_count, long long batch, uint64_t seed) {
    return run_batched(test_function, n, layer_count, batch, seed, 1, TIMING_FULL, 0);
}
