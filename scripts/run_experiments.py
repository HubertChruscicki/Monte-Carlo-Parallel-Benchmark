"""Uruchamia eksperymenty z mc_app, zapisuje surowe wyniki, statystyki i wykresy.

Uruchamiać z katalogu projektu w WSL:  python3 scripts/run_experiments.py
"""
import csv
import os
import statistics
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXECUTABLE_PATH = "./src/mc_app"
FUNCTION_NAMES = ["sin", "poly"]
EXACT_VALUES = {"sin": 2.0, "poly": 10.0}
METHOD_NAMES = ["classic", "stratified"]
SAMPLE_COUNTS = [10_000, 100_000, 1_000_000, 10_000_000]
LAYER_COUNT = 10
SEEDS = [1, 2, 3, 4, 5]

CPU_COUNT = os.cpu_count() or 1
THREAD_COUNTS = []
power_of_two = 1
while power_of_two <= 2 * CPU_COUNT:
    THREAD_COUNTS.append(power_of_two)
    power_of_two *= 2

RAW_RESULTS_CSV = "data/raw_results.csv"
SUMMARY_CSV = "data/summary.csv"
RAW_FIELDS = ["func", "method", "samples", "layers", "threads", "seed",
              "oversubscribed", "estimate", "error", "ci_low", "ci_high", "time_sec"]
SUMMARY_FIELDS = ["func", "method", "samples", "threads", "oversubscribed", "runs",
                  "median_time_sec", "std_time_sec", "median_error", "ci_coverage"]


def run_one(function_name, method_name, sample_count, thread_count, seed):
    command = [EXECUTABLE_PATH, "--func", function_name, "--method", method_name,
               "--samples", str(sample_count), "--threads", str(thread_count),
               "--seed", str(seed)]
    if method_name == "stratified":
        command += ["--layers", str(LAYER_COUNT)]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Błąd dla {command}: {completed.stderr.strip()}")
    estimate, absolute_error, ci_low, ci_high, time_sec = completed.stdout.strip().split(",")
    return {
        "func": function_name,
        "method": method_name,
        "samples": sample_count,
        "layers": LAYER_COUNT if method_name == "stratified" else 0,
        "threads": thread_count,
        "seed": seed,
        "oversubscribed": int(thread_count > CPU_COUNT),
        "estimate": float(estimate),
        "error": float(absolute_error),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "time_sec": float(time_sec),
    }


def summarize(rows):
    groups = {}
    for row in rows:
        key = (row["func"], row["method"], row["samples"], row["threads"])
        groups.setdefault(key, []).append(row)

    summary = []
    for (function_name, method_name, sample_count, thread_count), group in groups.items():
        times = [row["time_sec"] for row in group]
        errors = [row["error"] for row in group]
        covered = [row["ci_low"] <= EXACT_VALUES[function_name] <= row["ci_high"] for row in group]
        summary.append({
            "func": function_name,
            "method": method_name,
            "samples": sample_count,
            "threads": thread_count,
            "oversubscribed": int(thread_count > CPU_COUNT),
            "runs": len(group),
            "median_time_sec": statistics.median(times),
            "std_time_sec": statistics.stdev(times) if len(times) > 1 else 0.0,
            "median_error": statistics.median(errors),
            "ci_coverage": sum(covered) / len(covered),
        })
    return summary


def write_csv(path, fields, rows):
    with open(path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_speedup(summary, function_name, method_name):
    # S(p) = T(1) / T(p) dla tej samej metody i N; E(p) = S(p) / p
    largest_sample_count = max(SAMPLE_COUNTS)
    points = sorted([row for row in summary if row["func"] == function_name
                     and row["method"] == method_name
                     and row["samples"] == largest_sample_count],
                    key=lambda row: row["threads"])
    time_one_thread = next(row["median_time_sec"] for row in points if row["threads"] == 1)
    thread_counts = [row["threads"] for row in points]
    speedups = [time_one_thread / row["median_time_sec"] for row in points]
    efficiencies = [speedup / threads for speedup, threads in zip(speedups, thread_counts)]

    figure, (speedup_axis, efficiency_axis) = plt.subplots(1, 2, figsize=(10, 4))
    speedup_axis.plot(thread_counts, speedups, "o-", label="zmierzone")
    speedup_axis.plot(thread_counts, thread_counts, "--", color="gray", label="idealne")
    speedup_axis.set_xlabel("liczba wątków p")
    speedup_axis.set_ylabel("S(p) = T(1)/T(p)")
    speedup_axis.set_title(f"Speedup: {function_name}, {method_name}, N={largest_sample_count}")
    efficiency_axis.plot(thread_counts, efficiencies, "o-")
    efficiency_axis.set_xlabel("liczba wątków p")
    efficiency_axis.set_ylabel("E(p) = S(p)/p")
    efficiency_axis.set_title("Efektywność")
    for axis in (speedup_axis, efficiency_axis):
        axis.axvline(CPU_COUNT, color="red", linestyle=":", label="wątki logiczne")
        axis.set_xscale("log", base=2)
        axis.grid(True, alpha=0.3)
    speedup_axis.legend()
    figure.tight_layout()
    figure.savefig(f"plots/speedup_{function_name}_{method_name}.png", dpi=120)
    plt.close(figure)


def plot_error_vs_samples(rows, function_name):
    figure, axis = plt.subplots(figsize=(6, 4))
    for method_name in METHOD_NAMES:
        median_errors = []
        for sample_count in SAMPLE_COUNTS:
            errors = [row["error"] for row in rows if row["func"] == function_name
                      and row["method"] == method_name and row["samples"] == sample_count]
            median_errors.append(statistics.median(errors))
        axis.plot(SAMPLE_COUNTS, median_errors, "o-", label=method_name)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("liczba próbek N")
    axis.set_ylabel("mediana błędu bezwzględnego")
    axis.set_title(f"Błąd vs N: {function_name}")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(f"plots/error_vs_samples_{function_name}.png", dpi=120)
    plt.close(figure)


def plot_error_vs_time(summary, function_name):
    # Czas do zadanej dokładności: punkty błąd-czas dla różnych N przy najlepszej
    # liczbie wątków nie przekraczającej liczby wątków logicznych
    reference_threads = max(count for count in THREAD_COUNTS if count <= CPU_COUNT)
    figure, axis = plt.subplots(figsize=(6, 4))
    for method_name in METHOD_NAMES:
        points = sorted([row for row in summary if row["func"] == function_name
                         and row["method"] == method_name
                         and row["threads"] == reference_threads],
                        key=lambda row: row["samples"])
        axis.plot([row["median_time_sec"] for row in points],
                  [row["median_error"] for row in points], "o-", label=method_name)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("mediana czasu [s]")
    axis.set_ylabel("mediana błędu bezwzględnego")
    axis.set_title(f"Błąd vs czas: {function_name}, p={reference_threads}")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(f"plots/error_vs_time_{function_name}.png", dpi=120)
    plt.close(figure)


def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("plots", exist_ok=True)

    subprocess.run(["make"], check=True)

    rows = []
    total_runs = (len(FUNCTION_NAMES) * len(METHOD_NAMES) * len(SAMPLE_COUNTS)
                  * len(THREAD_COUNTS) * len(SEEDS))
    completed_runs = 0
    for function_name in FUNCTION_NAMES:
        for method_name in METHOD_NAMES:
            for sample_count in SAMPLE_COUNTS:
                for thread_count in THREAD_COUNTS:
                    for seed in SEEDS:
                        rows.append(run_one(function_name, method_name, sample_count,
                                            thread_count, seed))
                        completed_runs += 1
                    print(f"[{completed_runs}/{total_runs}] {function_name} {method_name} "
                          f"N={sample_count} p={thread_count}")

    write_csv(RAW_RESULTS_CSV, RAW_FIELDS, rows)
    summary = summarize(rows)
    write_csv(SUMMARY_CSV, SUMMARY_FIELDS, summary)

    for function_name in FUNCTION_NAMES:
        for method_name in METHOD_NAMES:
            plot_speedup(summary, function_name, method_name)
        plot_error_vs_samples(rows, function_name)
        plot_error_vs_time(summary, function_name)

    print(f"Zapisano {len(rows)} przebiegów do {RAW_RESULTS_CSV}, statystyki do {SUMMARY_CSV}, "
          f"wykresy do plots/.")


if __name__ == "__main__":
    main()
