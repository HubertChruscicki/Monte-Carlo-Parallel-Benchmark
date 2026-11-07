# Monte Carlo (O06), Etap 1

Założenia i zakres: [ZALOZENIA_PROJEKTU.md](ZALOZENIA_PROJEKTU.md).

## Szybki start

W WSL, z katalogu projektu uruchom jedno polecenie:

```bash
cd /mnt/c/Users/huber/Desktop/STUDIA/SEM9/PRIR/Monte-Carlo-Parallel-Benchmark
python3 scripts/run_experiments.py
```

Skrypt sam kompiluje program (`make`), wykonuje wszystkie przebiegi, zapisuje wyniki do `data/` i wykresy do `plots/`. Nie trzeba nic kompilować ręcznie.

## Wymagania (jednorazowo)

```bash
sudo apt update
sudo apt install build-essential python3 python3-pip
python3 -m pip install --user --break-system-packages matplotlib
```

## Pojedyncze uruchomienie programu C

Opcjonalnie, np. do sprawdzenia wyniku dla jednego ustawienia:

```bash
make
./src/mc_app --func sin --method classic --samples 1000000 --threads 4 --seed 1
./src/mc_app --func poly --method stratified --samples 1000000 --layers 10 --threads 4 --seed 1
```

Wynik (jedna linia CSV): `estimate,error,ci_low,ci_high,time_sec`

## Wyniki

- `data/raw_results.csv`: każdy przebieg osobno
- `data/summary.csv`: mediana i rozrzut czasu, mediana błędu, pokrycie przedziałów ufności
- `plots/`: speedup i efektywność, błąd vs N, błąd vs czas

## Uwagi

- Pliki tekstowe w repozytorium powinny mieć zakończenia LF, inaczej `make` w WSL może nie działać.
- Przed sprawozdaniem zapisać konfigurację komputera (model CPU, liczba rdzeni, wersja WSL, wersja gcc).
