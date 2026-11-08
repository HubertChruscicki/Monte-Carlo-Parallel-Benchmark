#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include "functions.h"
#include "monte_carlo.h"

int main(int argc, char *argv[]) {
    const char *function_name = "sin";
    const char *method_name = "classic";
    const char *timing_name = "full";
    const char *impl_name = "omp";
    long long samples = 1000000;
    int layer_count = 10;
    long long batch = 10000;
    int thread_count = 4;
    unsigned long long seed = 1;

    // Parametry w parach: --nazwa wartość
    for (int i = 1; i < argc; i += 2) {
        if (i + 1 >= argc) {
            fprintf(stderr, "ERROR: brak wartości dla opcji %s\n", argv[i]);
            return 1;
        }
        const char *option = argv[i];
        const char *value = argv[i + 1];
        if (strcmp(option, "--func") == 0) function_name = value;
        else if (strcmp(option, "--method") == 0) method_name = value;
        else if (strcmp(option, "--samples") == 0) samples = atoll(value);
        else if (strcmp(option, "--layers") == 0) layer_count = atoi(value);
        else if (strcmp(option, "--batch") == 0) batch = atoll(value);
        else if (strcmp(option, "--threads") == 0) thread_count = atoi(value);
        else if (strcmp(option, "--seed") == 0) seed = strtoull(value, NULL, 10);
        else if (strcmp(option, "--timing") == 0) timing_name = value;
        else if (strcmp(option, "--impl") == 0) impl_name = value;
        else {
            fprintf(stderr, "ERROR: nieznana opcja %s\n", option);
            return 1;
        }
    }

    TestFunction test_function;
    if (!find_test_function(function_name, &test_function)) {
        fprintf(stderr, "ERROR: nieznana funkcja %s (dozwolone: sin, poly)\n", function_name);
        return 1;
    }
    if (samples < 2) {
        fprintf(stderr, "ERROR: liczba próbek musi być >= 2\n");
        return 1;
    }
    if (thread_count < 1) {
        fprintf(stderr, "ERROR: liczba wątków musi być >= 1\n");
        return 1;
    }
    if (batch < 1) {
        fprintf(stderr, "ERROR: rozmiar partii musi być >= 1\n");
        return 1;
    }

    TimingMode timing;
    if (strcmp(timing_name, "full") == 0) {
        timing = TIMING_FULL;
    } else if (strcmp(timing_name, "rng") == 0) {
        timing = TIMING_RNG_ONLY;
    } else {
        fprintf(stderr, "ERROR: nieznany tryb pomiaru %s (dozwolone: full, rng)\n", timing_name);
        return 1;
    }

    int sequential;
    if (strcmp(impl_name, "omp") == 0) {
        sequential = 0;
    } else if (strcmp(impl_name, "seq") == 0) {
        sequential = 1;
    } else {
        fprintf(stderr, "ERROR: nieznana implementacja %s (dozwolone: omp, seq)\n", impl_name);
        return 1;
    }
    if (sequential && timing == TIMING_RNG_ONLY) {
        fprintf(stderr, "ERROR: tryb rng jest dostępny tylko dla --impl omp\n");
        return 1;
    }

    MonteCarloResult result;
    if (strcmp(method_name, "classic") == 0) {
        if (sequential) {
            result = monte_carlo_sequential(&test_function, samples, 1, batch, (uint64_t)seed);
        } else {
            result = monte_carlo_classic(&test_function, samples, batch, (uint64_t)seed,
                                         thread_count, timing);
        }
    } else if (strcmp(method_name, "stratified") == 0) {
        if (layer_count < 1) {
            fprintf(stderr, "ERROR: liczba warstw musi być >= 1\n");
            return 1;
        }
        if (samples % layer_count != 0) {
            fprintf(stderr, "ERROR: liczba próbek musi być podzielna przez liczbę warstw\n");
            return 1;
        }
        if (samples / layer_count < 2) {
            fprintf(stderr, "ERROR: za mało próbek na warstwę (minimum 2)\n");
            return 1;
        }
        if (sequential) {
            result = monte_carlo_sequential(&test_function, samples, layer_count, batch,
                                            (uint64_t)seed);
        } else {
            result = monte_carlo_stratified(&test_function, samples, layer_count, batch,
                                            (uint64_t)seed, thread_count, timing);
        }
    } else {
        fprintf(stderr, "ERROR: nieznana metoda %s (dozwolone: classic, stratified)\n", method_name);
        return 1;
    }

    double absolute_error = fabs(result.estimate - test_function.exact_value);
    double confidence_interval_low = result.estimate - 1.96 * result.standard_error;
    double confidence_interval_high = result.estimate + 1.96 * result.standard_error;

    // Wynik: estimate,error,ci_low,ci_high,std_error,time_core_sec,time_agg_sec
    printf("%.10f,%.10e,%.10f,%.10f,%.10e,%.9f,%.9f\n", result.estimate, absolute_error,
           confidence_interval_low, confidence_interval_high, result.standard_error,
           result.time_core_seconds, result.time_agg_seconds);
    return 0;
}
