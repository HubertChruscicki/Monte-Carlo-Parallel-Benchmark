#ifndef RNG_H
#define RNG_H

#include <stdint.h>

/**
 * Generuje liczbę pseudolosową z przedziału [0, 1).
 * 
 * W przeciwieństwie do standardowego rand() z biblioteki C (który ma ograniczony 
 * zakres do 32767 i powodowałby powtarzanie się liczb przy milionach próbek), 
 * to rozwiązanie zapewnia pełną precyzję oraz brak konfliktów między wątkami.
 * 
 * Mechanika działania oparta na indeksie próbki:
 * - 'seed' definiuje bazowe ziarno (gwarantuje pełną powtarzalność wyników).
 * - 'index' to unikalny numer iteracji / próbki w symulacji (od 0 do N-1).
 * 
 * Dzięki temu każdy wątek OpenMP może bezpiecznie i w dowolnej kolejności losować 
 * punkty, a dla tej samej pary (seed, index) zawsze uzyskamy co do bitu 
 * identyczny wynik, co jest kluczowe w weryfikacji i benchmarkach.
 */
double rng_uniform(uint64_t seed, uint64_t index);

#endif
