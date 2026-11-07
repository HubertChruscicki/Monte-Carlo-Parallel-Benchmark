#ifndef MONTE_CARLO_H
#define MONTE_CARLO_H

#include <stdint.h>
#include "functions.h"

// Wynik pojedynczego przebiegu
typedef struct {
    double estimate;         // estymata całki
    double standard_error;   // błąd standardowy estymaty
    double time_seconds;     // czas pętli próbkowania (OpenMP, wall clock)
} MonteCarloResult;

// Klasyczne Monte Carlo: n próbek, równoległość po próbkach
MonteCarloResult monte_carlo_classic(const TestFunction *test_function, long long n,
                                     uint64_t seed, int thread_count);

// Próbkowanie warstwowe: layer_count warstw po n/layer_count próbek, równoległość po próbkach
// Wymaga n % layer_count == 0 oraz n/layer_count >= 2 (sprawdzane w main.c)
MonteCarloResult monte_carlo_stratified(const TestFunction *test_function, long long n,
                                        int layer_count, uint64_t seed, int thread_count);

#endif
