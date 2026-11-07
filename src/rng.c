#include "rng.h"

// Funkcja mieszająca algorytmu SplitMix64.
// Miesza bity liczby, żeby upewnić się, że generowane wartości są całkowicie losowe i nie mają żadnych ukrytych wzorców.
static uint64_t splitmix64_mix(uint64_t z) {
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

double rng_uniform(uint64_t seed, uint64_t index) {
    
    // Zamiast zwykłego rand(), liczymy unikalny stan dla konkretnego numeru 
    // próbki ('index'). Dzięki temu wątki OpenMP mogą liczyć próbki niezależnie, 
    // a dla tej samej pary (seed, index) zawsze dostaniemy ten sam wynik.
    uint64_t state = seed + (index + 1) * 0x9E3779B97F4A7C15ULL;
    
    // Zamiana na liczbę z przedziału [0, 1):
    // 1. Bierzemy wymieszaną liczbę i odcinamy zbędne bity (>> 11).
    // 2. Dzielimy przez 2^53, żeby dostać ułamek z przedziału od 0 do 1.
    return (double)(splitmix64_mix(state) >> 11) * (1.0 / 9007199254740992.0);
}
