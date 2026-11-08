"""Uruchamia eksperymenty z mc_app, sprawdza poprawność, zapisuje dane, statystyki i wykresy.

Uruchamiać z katalogu projektu w WSL:  python3 scripts/run_experiments.py
"""
import csv
import os
import platform
import statistics
import subprocess
import sys
import time
from itertools import product

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXECUTABLE_PATH = "./src/mc_app"
FUNCTION_NAMES = ["sin", "poly"]
EXACT_VALUES = {"sin": 2.0, "poly": 10.0}
FUNCTION_LABELS = {"sin": "sin(x) na [0, π]", "poly": "3(x−1)²+4 na [0, 2]"}
METHOD_NAMES = ["classic", "stratified"]
METHOD_LABELS = {"classic": "klasyczne", "stratified": "warstwowe"}
SAMPLE_COUNTS = [10_000, 100_000, 1_000_000, 10_000_000]
LARGEST_N = max(SAMPLE_COUNTS)
LAYER_COUNT = 10
BATCH_SIZE = 10_000
SEEDS = list(range(1, 21))
EPS_LEVELS = [1e-2, 3e-3, 1e-3, 3e-4, 1e-4]
TIME_TO_EPS_THREADS = 1
TOLERANCE = 1e-9

CPU_COUNT = os.cpu_count() or 1
THREAD_COUNTS = []
power_of_two = 1
while power_of_two <= 2 * CPU_COUNT:
    THREAD_COUNTS.append(power_of_two)
    power_of_two *= 2
SPEEDUP_THREADS = [count for count in THREAD_COUNTS if count <= CPU_COUNT]
COST_THREADS = [1, CPU_COUNT]

DATA_DIR = "data"
PLOTS_DIR = "plots"
RAW_RESULTS_CSV = "data/raw_results.csv"
SUMMARY_CSV = "data/summary.csv"
COST_CSV = "data/cost_breakdown.csv"
TIME_TO_EPS_CSV = "data/time_to_eps.csv"
REFERENCE_CSV = "data/reference_check.csv"
SYSTEM_INFO_TXT = "data/system_info.txt"

RAW_FIELDS = ["func", "method", "timing", "samples", "layers", "batch", "threads", "seed",
              "oversubscribed", "estimate", "error", "ci_low", "ci_high", "std_error",
              "time_core_sec", "time_agg_sec", "time_wall_sec", "samples_per_sec"]
SUMMARY_FIELDS = ["func", "method", "samples", "layers", "batch", "threads", "oversubscribed",
                  "runs", "median_time_core_sec", "q25_time_core_sec", "q75_time_core_sec",
                  "std_time_core_sec", "median_time_agg_sec", "median_time_wall_sec",
                  "median_samples_per_sec", "median_error", "q25_error", "q75_error",
                  "median_std_error", "ci_coverage"]
COST_FIELDS = ["func", "method", "samples", "layers", "batch", "threads",
               "median_full_core_sec", "median_rng_sec", "median_func_sec", "median_agg_sec",
               "share_rng", "share_func", "share_agg"]
TIME_TO_EPS_FIELDS = ["func", "method", "eps", "reached", "samples", "threads",
                      "median_time_core_sec", "median_error"]
REFERENCE_FIELDS = ["check", "func", "method", "samples", "threads", "batch",
                    "value_reference", "value_tested", "abs_diff", "passed"]


def write_csv(path, fields, rows):
    with open(path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def quartiles(values):
    q25, _, q75 = statistics.quantiles(values, n=4, method="inclusive")
    return q25, q75


def build_arguments(func, method, samples, threads, seed, timing, batch, impl):
    command = [EXECUTABLE_PATH, "--func", func, "--method", method, "--samples", str(samples),
               "--threads", str(threads), "--seed", str(seed), "--batch", str(batch),
               "--timing", timing, "--impl", impl]
    if method == "stratified":
        command += ["--layers", str(LAYER_COUNT)]
    return command


def parse_output(stdout):
    fields = stdout.strip().split(",")
    estimate, absolute_error, ci_low, ci_high, std_error, time_core, time_agg = map(float, fields)
    return {"estimate": estimate, "error": absolute_error, "ci_low": ci_low,
            "ci_high": ci_high, "std_error": std_error,
            "time_core_sec": time_core, "time_agg_sec": time_agg}


def run_one(func, method, samples, threads, seed, timing="full", batch=BATCH_SIZE, impl="omp"):
    command = build_arguments(func, method, samples, threads, seed, timing, batch, impl)
    start = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True)
    wall_time = time.perf_counter() - start
    if completed.returncode != 0:
        raise RuntimeError(f"Błąd dla {command}: {completed.stderr.strip()}")
    row = parse_output(completed.stdout)
    row.update({
        "func": func, "method": method, "timing": timing, "samples": samples,
        "layers": LAYER_COUNT if method == "stratified" else 0, "batch": batch,
        "threads": threads, "seed": seed, "oversubscribed": int(threads > CPU_COUNT),
        "time_wall_sec": wall_time,
        "samples_per_sec": samples / max(row["time_core_sec"], 1e-12),
    })
    return row


def warm_up(func, method, samples, threads, timing):
    # Rozgrzewka: jedno uruchomienie bez zapisu do CSV
    run_one(func, method, samples, threads, seed=0, timing=timing)


def check_reference():
    rows = []
    for func, method in product(FUNCTION_NAMES, METHOD_NAMES):
        for samples, seed in product([10_000, 1_000_000], [1, 2]):
            reference = run_one(func, method, samples, 1, seed, impl="seq")
            variants = [
                ("omp, p=1", 1, BATCH_SIZE),
                ("omp, p=2", 2, BATCH_SIZE),
                (f"omp, p={CPU_COUNT}", CPU_COUNT, BATCH_SIZE),
                ("omp, partia=1000", CPU_COUNT, 1000),
                ("omp, partia > N", CPU_COUNT, 10**9),
            ]
            for name, threads, batch in variants:
                tested = run_one(func, method, samples, threads, seed, batch=batch)
                diff = abs(tested["estimate"] - reference["estimate"])
                limit = TOLERANCE * max(1.0, abs(reference["estimate"]))
                rows.append({"check": f"seq vs {name}, seed={seed}", "func": func,
                             "method": method, "samples": samples, "threads": threads,
                             "batch": batch,
                             "value_reference": reference["estimate"],
                             "value_tested": tested["estimate"],
                             "abs_diff": diff, "passed": int(diff <= limit)})

    edge_cases = [
        ("N = 2 (klasyczne)", ["--func", "sin", "--method", "classic", "--samples", "2"], 0),
        ("N niepodzielne przez K", ["--func", "sin", "--method", "stratified", "--samples", "10001",
                                    "--layers", "10"], 1),
        ("partia = 0", ["--func", "sin", "--samples", "100", "--batch", "0"], 1),
        ("nieznana funkcja", ["--func", "xyz", "--samples", "100"], 1),
        ("tryb rng z --impl seq", ["--func", "sin", "--samples", "100", "--timing", "rng",
                                   "--impl", "seq"], 1),
    ]
    for name, arguments, expected_code in edge_cases:
        completed = subprocess.run([EXECUTABLE_PATH] + arguments, capture_output=True, text=True)
        rows.append({"check": f"przypadek brzegowy: {name}", "func": "", "method": "",
                     "samples": "", "threads": "", "batch": "", "value_reference": "",
                     "value_tested": "", "abs_diff": "",
                     "passed": int(completed.returncode == expected_code)})

    write_csv(REFERENCE_CSV, REFERENCE_FIELDS, rows)
    failed = [row for row in rows if not row["passed"]]
    if failed:
        raise RuntimeError(f"Sprawdzenie poprawności nie przeszło: {len(failed)} przypadków, "
                           f"zobacz {REFERENCE_CSV}")
    print(f"Sprawdzenie poprawności: {len(rows)} przypadków, wszystkie przeszły.")


def collect_main_runs():
    rows = []
    total = len(FUNCTION_NAMES) * len(METHOD_NAMES) * len(SAMPLE_COUNTS) * len(THREAD_COUNTS)
    done = 0
    for func, method, samples, threads in product(FUNCTION_NAMES, METHOD_NAMES,
                                                  SAMPLE_COUNTS, THREAD_COUNTS):
        warm_up(func, method, samples, threads, "full")
        for seed in SEEDS:
            rows.append(run_one(func, method, samples, threads, seed, timing="full"))
        done += 1
        print(f"[{done}/{total}] {func} {method} N={samples} p={threads}")
    return rows


def collect_rng_runs():
    rows = []
    for func, method, samples, threads in product(FUNCTION_NAMES, METHOD_NAMES,
                                                  SAMPLE_COUNTS, COST_THREADS):
        warm_up(func, method, samples, threads, "rng")
        for seed in SEEDS:
            rows.append(run_one(func, method, samples, threads, seed, timing="rng"))
    return rows


def summarize(rows):
    groups = {}
    for row in rows:
        key = (row["func"], row["method"], row["samples"], row["threads"])
        groups.setdefault(key, []).append(row)

    summary = []
    for (func, method, samples, threads), group in groups.items():
        times = [row["time_core_sec"] for row in group]
        errors = [row["error"] for row in group]
        covered = [row["ci_low"] <= EXACT_VALUES[func] <= row["ci_high"] for row in group]
        time_q25, time_q75 = quartiles(times)
        error_q25, error_q75 = quartiles(errors)
        summary.append({
            "func": func, "method": method, "samples": samples,
            "layers": group[0]["layers"], "batch": group[0]["batch"], "threads": threads,
            "oversubscribed": int(threads > CPU_COUNT), "runs": len(group),
            "median_time_core_sec": statistics.median(times),
            "q25_time_core_sec": time_q25, "q75_time_core_sec": time_q75,
            "std_time_core_sec": statistics.stdev(times),
            "median_time_agg_sec": statistics.median(row["time_agg_sec"] for row in group),
            "median_time_wall_sec": statistics.median(row["time_wall_sec"] for row in group),
            "median_samples_per_sec": statistics.median(row["samples_per_sec"] for row in group),
            "median_error": statistics.median(errors),
            "q25_error": error_q25, "q75_error": error_q75,
            "median_std_error": statistics.median(row["std_error"] for row in group),
            "ci_coverage": sum(covered) / len(covered),
        })
    return summary


def build_cost_breakdown(index, rng_rows):
    rng_groups = {}
    for row in rng_rows:
        key = (row["func"], row["method"], row["samples"], row["threads"])
        rng_groups.setdefault(key, []).append(row["time_core_sec"])

    rows = []
    for func, method, samples, threads in product(FUNCTION_NAMES, METHOD_NAMES,
                                                  SAMPLE_COUNTS, COST_THREADS):
        full = index[(func, method, samples, threads)]
        rng_time = statistics.median(rng_groups[(func, method, samples, threads)])
        full_time = full["median_time_core_sec"]
        func_time = max(full_time - rng_time, 0.0)
        agg_time = full["median_time_agg_sec"]
        total = rng_time + func_time + agg_time
        rows.append({
            "func": func, "method": method, "samples": samples, "layers": full["layers"],
            "batch": full["batch"], "threads": threads,
            "median_full_core_sec": full_time, "median_rng_sec": rng_time,
            "median_func_sec": func_time, "median_agg_sec": agg_time,
            "share_rng": rng_time / total, "share_func": func_time / total,
            "share_agg": agg_time / total,
        })
    return rows


def build_time_to_eps(index):
    rows = []
    for func, method, eps in product(FUNCTION_NAMES, METHOD_NAMES, EPS_LEVELS):
        found = None
        for samples in SAMPLE_COUNTS:
            row = index[(func, method, samples, TIME_TO_EPS_THREADS)]
            if row["median_error"] <= eps:
                found = row
                break
        rows.append({
            "func": func, "method": method, "eps": eps, "reached": int(found is not None),
            "samples": found["samples"] if found else "",
            "threads": TIME_TO_EPS_THREADS,
            "median_time_core_sec": found["median_time_core_sec"] if found else "",
            "median_error": found["median_error"] if found else "",
        })
    return rows


def read_cpu_info():
    try:
        with open("/proc/cpuinfo") as cpuinfo:
            lines = cpuinfo.read().splitlines()
    except OSError:
        return "nieznany", "nieznana"
    model = next((line.split(":", 1)[1].strip() for line in lines
                  if line.startswith("model name")), "nieznany")
    cores = next((line.split(":", 1)[1].strip() for line in lines
                  if line.startswith("cpu cores")), "nieznana")
    return model, cores


def write_system_info():
    model, physical_cores = read_cpu_info()
    compiler = subprocess.run(["gcc", "--version"], capture_output=True, text=True).stdout
    lines = [
        f"Data pomiarów: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"System: {platform.platform()}",
        f"Procesor: {model}",
        f"Rdzenie fizyczne: {physical_cores}",
        f"Wątki logiczne (os.cpu_count): {CPU_COUNT}",
        f"Kompilator: {compiler.splitlines()[0] if compiler else 'nieznany'}",
        "Flagi kompilacji: -O3 -fopenmp -Wall -Wextra",
        f"Python: {sys.version.split()[0]}",
        f"matplotlib: {matplotlib.__version__}",
        f"Rozmiar partii: {BATCH_SIZE}",
        f"Liczba ziaren: {len(SEEDS)}",
        f"Liczba warstw (stratified): {LAYER_COUNT}",
        f"Siatka N: {SAMPLE_COUNTS}",
        f"Siatka p: {THREAD_COUNTS}",
    ]
    with open(SYSTEM_INFO_TXT, "w", encoding="utf-8") as info_file:
        info_file.write("\n".join(lines) + "\n")


def remove_old_plots():
    for name in os.listdir(PLOTS_DIR):
        if name.endswith(".png"):
            os.remove(os.path.join(PLOTS_DIR, name))


def save_figure(figure, name):
    figure.tight_layout()
    figure.savefig(os.path.join(PLOTS_DIR, name), dpi=120)
    plt.close(figure)


def plot_speedup(index, func):
    figure, axis = plt.subplots(figsize=(7, 5))
    for method in METHOD_NAMES:
        base = index[(func, method, LARGEST_N, 1)]["median_time_core_sec"]
        medians, lows, highs = [], [], []
        for threads in SPEEDUP_THREADS:
            row = index[(func, method, LARGEST_N, threads)]
            speedup = base / row["median_time_core_sec"]
            medians.append(speedup)
            lows.append(speedup - base / row["q75_time_core_sec"])
            highs.append(base / row["q25_time_core_sec"] - speedup)
        axis.errorbar(SPEEDUP_THREADS, medians, yerr=[lows, highs], fmt="o-", capsize=3,
                      label=f"{METHOD_LABELS[method]}: S(p) = T(1) / T(p)")
    axis.plot(SPEEDUP_THREADS, SPEEDUP_THREADS, "--", color="gray",
              label="idealnie: S(p) = p")
    axis.set_xticks(SPEEDUP_THREADS)
    axis.set_xlabel("liczba wątków p")
    axis.set_ylabel("przyspieszenie")
    axis.set_title(f"Przyspieszenie: {FUNCTION_LABELS[func]}, N = 10⁷")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="upper left")
    save_figure(figure, f"speedup_{func}.png")


def plot_efficiency(index, func):
    figure, axis = plt.subplots(figsize=(7, 5))
    for method in METHOD_NAMES:
        base = index[(func, method, LARGEST_N, 1)]["median_time_core_sec"]
        medians, lows, highs = [], [], []
        for threads in SPEEDUP_THREADS:
            row = index[(func, method, LARGEST_N, threads)]
            efficiency = base / row["median_time_core_sec"] / threads
            medians.append(efficiency)
            lows.append((efficiency - base / row["q75_time_core_sec"] / threads))
            highs.append(base / row["q25_time_core_sec"] / threads - efficiency)
        axis.errorbar(SPEEDUP_THREADS, medians, yerr=[lows, highs], fmt="o-", capsize=3,
                      label=f"{METHOD_LABELS[method]}: E(p) = S(p) / p")
    axis.axhline(1.0, color="gray", linestyle="--", label="idealnie: E(p) = 1")
    axis.set_xticks(SPEEDUP_THREADS)
    axis.set_ylim(0, 1.1)
    axis.set_xlabel("liczba wątków p")
    axis.set_ylabel("efektywność")
    axis.set_title(f"Efektywność: {FUNCTION_LABELS[func]}, N = 10⁷")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="upper right")
    save_figure(figure, f"efficiency_{func}.png")


def plot_time_to_eps(eps_rows, func):
    figure, axis = plt.subplots(figsize=(7, 5))
    for method in METHOD_NAMES:
        points = sorted([row for row in eps_rows if row["func"] == func
                         and row["method"] == method and row["reached"]],
                        key=lambda row: row["eps"])
        axis.plot([row["eps"] for row in points],
                  [row["median_time_core_sec"] for row in points], "o-",
                  label=f"{METHOD_LABELS[method]}: czas do osiągnięcia ε (p = 1)")
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("docelowy błąd ε (błąd bezwzględny), skala logarytmiczna")
    axis.set_ylabel("czas rdzenia [s], skala logarytmiczna")
    axis.set_title(f"Czas do zadanej dokładności: {FUNCTION_LABELS[func]}")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend(loc="best")
    save_figure(figure, f"time_to_eps_{func}.png")


def plot_error_vs_n(index, func):
    figure, axis = plt.subplots(figsize=(7, 5))
    for method in METHOD_NAMES:
        rows = [index[(func, method, samples, 1)] for samples in SAMPLE_COUNTS]
        medians = [row["median_error"] for row in rows]
        lows = [row["median_error"] - row["q25_error"] for row in rows]
        highs = [row["q75_error"] - row["median_error"] for row in rows]
        axis.errorbar(SAMPLE_COUNTS, medians, yerr=[lows, highs], fmt="o-", capsize=3,
                      label=f"{METHOD_LABELS[method]}: mediana |estymata − dokładna|")
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("liczba próbek N, skala logarytmiczna")
    axis.set_ylabel("błąd bezwzględny, skala logarytmiczna")
    axis.set_title(f"Błąd estymacji vs N: {FUNCTION_LABELS[func]}")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend(loc="best")
    save_figure(figure, f"error_vs_n_{func}.png")


def plot_ci_coverage(index, func):
    figure, axis = plt.subplots(figsize=(7, 5))
    for method in METHOD_NAMES:
        coverage = [index[(func, method, samples, 1)]["ci_coverage"] for samples in SAMPLE_COUNTS]
        axis.plot(SAMPLE_COUNTS, coverage, "o-",
                  label=f"{METHOD_LABELS[method]}: udział przedziałów 95% z wynikiem dokładnym")
    axis.axhline(0.95, color="gray", linestyle="--", label="oczekiwane pokrycie: 0,95")
    axis.set_xscale("log")
    axis.set_ylim(0, 1.05)
    axis.set_xlabel("liczba próbek N, skala logarytmiczna")
    axis.set_ylabel("pokrycie przedziałów ufności (0–1)")
    axis.set_title(f"Pokrycie przedziałów ufności: {FUNCTION_LABELS[func]}")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend(loc="lower right")
    save_figure(figure, f"ci_coverage_{func}.png")


def plot_cost_breakdown(cost_rows, func):
    cases = [(method, threads) for method in METHOD_NAMES for threads in COST_THREADS]
    selected = [next(row for row in cost_rows if row["func"] == func
                     and row["method"] == method and row["threads"] == threads
                     and row["samples"] == LARGEST_N) for method, threads in cases]
    labels = [f"{METHOD_LABELS[row['method']]}\np = {row['threads']}\n"
              f"T = {row['median_full_core_sec'] + row['median_agg_sec']:.3f} s"
              for row in selected]
    rng = [100 * row["share_rng"] for row in selected]
    func_part = [100 * row["share_func"] for row in selected]
    agg = [100 * row["share_agg"] for row in selected]
    positions = range(len(selected))

    figure, axis = plt.subplots(figsize=(8, 5.5))
    axis.bar(positions, rng, label="generowanie liczb losowych (RNG)")
    axis.bar(positions, func_part, bottom=rng, label="funkcja podcałkowa f(x)")
    axis.bar(positions, agg, bottom=[a + b for a, b in zip(rng, func_part)],
             label="agregacja partii")
    axis.set_xticks(list(positions))
    axis.set_xticklabels(labels)
    axis.set_ylim(0, 100)
    axis.set_ylabel("udział w całkowitym czasie [%]")
    axis.set_title(f"Podział kosztu: {FUNCTION_LABELS[func]}, N = 10⁷")
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3)
    save_figure(figure, f"cost_breakdown_{func}.png")


def write_readme():
    sample_list = ", ".join(format(n, ",").replace(",", " ") for n in SAMPLE_COUNTS)
    thread_list = ", ".join(str(p) for p in THREAD_COUNTS)
    batch_text = format(BATCH_SIZE, ",").replace(",", " ")
    seed_count = len(SEEDS)
    text = f"""# Wykresy: jak je czytać

Wszystkie wykresy i tabele generuje `scripts/run_experiments.py` z plików w `data/`.
Konfiguracja sprzętu: `data/system_info.txt`.

## Parametry eksperymentu

- Funkcje: sin(x) na [0, π] (wynik dokładny 2), 3(x-1)²+4 na [0, 2] (wynik dokładny 10).
- Metody: klasyczna (jedna warstwa) i warstwowa (K = {LAYER_COUNT} warstw).
- Liczba próbek N: {sample_list}. Te same N dla obu metod.
- Liczba wątków p: {thread_list}. Wątków logicznych jest {CPU_COUNT}; wartości powyżej są oversubscription i nie są na wykresach przyspieszenia.
- Rozmiar partii: {batch_text} próbek. Partie są rozdzielane między wątki, więc przy N mniejszym niż p × rozmiar partii nie wszystkie wątki mają pracę. Dane dla małych N i dużych p nie pokazują wtedy prawdziwego skalowania; wykresy przyspieszenia używają N = 10⁷.
- Ziarna: {seed_count} na konfigurację. Przed każdą konfiguracją jedno uruchomienie rozgrzewkowe, którego wynik nie trafia do danych.
- Czas rdzenia: pętla próbkowania w C (losowanie, f(x), sumy partii). Czas pełny: całe uruchomienie programu mierzone w Pythonie.
- Punkt na wykresie to mediana z {seed_count} ziaren. Słupki błędów to rozstęp międzykwartylowy: od kwartyla 1 (Q1) do kwartyla 3 (Q3).

## Wykresy

### `speedup_<funkcja>.png`: przyspieszenie

- Pytanie: ile razy szybciej działa program przy p wątkach niż przy jednym.
- Oś pozioma: liczba wątków p (skala liniowa).
- Oś pionowa: przyspieszenie S(p) = T(1) / T(p), skala liniowa. T to mediana czasu rdzenia dla N = 10⁷.
- Linie: jedna dla każdej metody. Każda liczona względem własnego T(1), czyli czasu tej samej metody przy p = 1.
- Linia przerywana: wynik idealny S(p) = p. Jest to jedyna linia pomocnicza.
- Słupki: zakres Q1-Q3 czasu przeliczony na S.
- Jak czytać: im bliżej linii przerywanej, tym lepsze skalowanie. Płaski przebieg oznacza, że kolejne wątki nie dają zysku.

### `efficiency_<funkcja>.png`: efektywność

- Pytanie: jaka część idealnego przyspieszenia jest wykorzystywana.
- Oś pozioma: liczba wątków p. Oś pionowa: efektywność E(p) = S(p) / p, od 0 do 1.
- Linia przerywana: E(p) = 1, czyli wykorzystanie idealne.
- Jak czytać: spadek krzywej oznacza narzut, np. synchronizację, dzielenie rdzeni fizycznych przez wątki logiczne albo koszt przydziału pracy.

### `time_to_eps_<funkcja>.png`: czas do zadanej dokładności

- Pytanie: ile czasu potrzeba, żeby osiągnąć zadany błąd ε.
- Oś pozioma: docelowy błąd ε, skala logarytmiczna. W prawo rośnie dopuszczalny błąd, w lewo rośnie wymagana dokładność.
- Oś pionowa: czas rdzenia w sekundach, skala logarytmiczna.
- Każdy punkt: najmniejsze N z siatki, dla którego mediana błędu jest nie większa niż ε. Czas to mediana czasu dla tego N.
- Brak punktu oznacza, że na siatce N nie osiągnięto ε.
- Wykres dla p = 1, żeby porównywać metody bez wpływu równoległości.
- Jak czytać: niżej oznacza szybciej przy tej samej dokładności.

### `error_vs_n_<funkcja>.png`: błąd vs liczba próbek

- Pytanie: jak błąd maleje wraz z liczbą próbek.
- Oś pozioma: N, skala logarytmiczna. Oś pionowa: mediana błędu bezwzględnego |estymata - dokładna|, skala logarytmiczna.
- Słupki: Q1-Q3 błędu z ziaren.
- Jak czytać: dla metody klasycznej błąd maleje około √10 ≈ 3,2 razy na każdą dekadę N. Niższa linia oznacza dokładniejszą metodę przy tym samym N.

### `ci_coverage_<funkcja>.png`: pokrycie przedziałów ufności

- Pytanie: czy przedziały ufności 95% rzeczywiście zawierają wynik dokładny.
- Oś pozioma: N, skala logarytmiczna. Oś pionowa: udział przedziałów zawierających wynik dokładny, od 0 do 1.
- Linia przerywana: oczekiwane pokrycie 0,95.
- Przy {len(SEEDS)} ziarnach udział zmienia się skokowo co 1/{len(SEEDS)} ≈ 0,05.
- Jak czytać: wartości blisko 0,95 oznaczają, że przedziały zachowują się zgodnie z teorią.

### `cost_breakdown_<funkcja>.png`: podział kosztu

- Pytanie: z czego składa się czas działania.
- Słupki: cztery konfiguracje (metoda i p) dla N = 10⁷. Pod etykietą podano całkowity czas T.
- Części słupka:
  - RNG: czas samego losowania (tryb `--timing rng`).
  - f(x): różnica czasu pełnego i czasu RNG.
  - agregacja: czas scalania partii, estymaty i wariancji.
- Jak czytać: duży udział RNG oznacza, że generator jest wąskim gardłem. Duży udział f(x) oznacza, że koszt leży w funkcji podcałkowej.
- Uwaga: część „RNG” zawiera też narzut pętli i partii, bo tryb RNG przechodzi tę samą strukturę.
- Agregacja trwa rzędu mikrosekund, czyli poniżej 0,01 % całego czasu. Na wykresie jest więc niewidoczna; jest w legendzie dla kompletności.
"""
    with open(os.path.join(PLOTS_DIR, "README.md"), "w", encoding="utf-8") as readme:
        readme.write(text)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    subprocess.run(["make", "clean"], check=True)
    subprocess.run(["make"], check=True)
    write_system_info()
    check_reference()

    main_rows = collect_main_runs()
    rng_rows = collect_rng_runs()
    write_csv(RAW_RESULTS_CSV, RAW_FIELDS, main_rows + rng_rows)

    summary = summarize(main_rows)
    write_csv(SUMMARY_CSV, SUMMARY_FIELDS, summary)
    index = {(row["func"], row["method"], row["samples"], row["threads"]): row
             for row in summary}

    cost_rows = build_cost_breakdown(index, rng_rows)
    write_csv(COST_CSV, COST_FIELDS, cost_rows)
    eps_rows = build_time_to_eps(index)
    write_csv(TIME_TO_EPS_CSV, TIME_TO_EPS_FIELDS, eps_rows)

    remove_old_plots()
    for func in FUNCTION_NAMES:
        plot_speedup(index, func)
        plot_efficiency(index, func)
        plot_time_to_eps(eps_rows, func)
        plot_error_vs_n(index, func)
        plot_ci_coverage(index, func)
        plot_cost_breakdown(cost_rows, func)
    write_readme()

    print(f"Zapisano {len(main_rows)} przebiegów głównych i {len(rng_rows)} przebiegów RNG "
          f"do {RAW_RESULTS_CSV}, statystyki do {SUMMARY_CSV}, wykresy do {PLOTS_DIR}/.")


if __name__ == "__main__":
    main()
