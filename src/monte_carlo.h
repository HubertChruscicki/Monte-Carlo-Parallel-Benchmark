#ifndef MONTE_CARLO_H
#define MONTE_CARLO_H

#include <stdint.h>
#include "functions.h"

// Tryb pomiaru: pełny (losowanie + f(x) + sumy) albo tylko losowanie (koszt generatora)
typedef enum {
    TIMING_FULL = 0,
    TIMING_RNG_ONLY = 1
} TimingMode;

// Wynik pojedynczego przebiegu
typedef struct {
    double estimate;           // estymata całki
    double standard_error;     // błąd standardowy estymaty
    double time_core_seconds;  // pętla próbkowania: losowanie, f(x), sumy partii (wall clock)
    double time_agg_seconds;   // scalenie partii, estymata i wariancja (wall clock)
} MonteCarloResult;

// Klasyczne Monte Carlo: jedna warstwa obejmująca cały przedział, próbki dzielone na partie
MonteCarloResult monte_carlo_classic(const TestFunction *test_function, long long n,
                                     long long batch, uint64_t seed, int thread_count,
                                     TimingMode timing);

// Próbkowanie warstwowe: layer_count warstw po n/layer_count próbek, próbki dzielone na partie
// Wymaga n % layer_count == 0 oraz n/layer_count >= 2 (sprawdzane w main.c)
MonteCarloResult monte_carlo_stratified(const TestFunction *test_function, long long n,
                                        int layer_count, long long batch, uint64_t seed,
                                        int thread_count, TimingMode timing);

// Referencja sekwencyjna: ta sama logika bez OpenMP, do sprawdzania poprawności
MonteCarloResult monte_carlo_sequential(const TestFunction *test_function, long long n,
                                        int layer_count, long long batch, uint64_t seed);

#endif
