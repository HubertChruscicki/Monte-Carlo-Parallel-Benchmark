#include <math.h>
#include <string.h>
#include "functions.h"

// f(x) = sin(x) na [0, pi], całka = 2
static double sin_function(double x) {
    return sin(x);
}

// f(x) = 3(x-1)^2 + 4 na [0, 2], całka = 10
static double poly_function(double x) {
    return 3.0 * (x - 1.0) * (x - 1.0) + 4.0;
}

int find_test_function(const char *name, TestFunction *out) {
    if (strcmp(name, "sin") == 0) {
        out->name = "sin";
        out->function = sin_function;
        out->interval_start = 0.0;
        out->interval_end = M_PI;
        out->exact_value = 2.0;
        return 1;
    }
    if (strcmp(name, "poly") == 0) {
        out->name = "poly";
        out->function = poly_function;
        out->interval_start = 0.0;
        out->interval_end = 2.0;
        out->exact_value = 10.0;
        return 1;
    }
    return 0;
}
