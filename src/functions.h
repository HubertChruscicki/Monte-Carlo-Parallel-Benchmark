#ifndef FUNCTIONS_H
#define FUNCTIONS_H

// Funkcja testowa: f(x) na przedziale [interval_start, interval_end] z dokładną wartością całki
typedef struct {
    const char *name;
    double (*function)(double);
    double interval_start;
    double interval_end;
    double exact_value;
} TestFunction;

// Wypełnia strukturę dla podanej nazwy ("sin" lub "poly"). Zwraca 1 gdy znaleziono.
int find_test_function(const char *name, TestFunction *out);

#endif
