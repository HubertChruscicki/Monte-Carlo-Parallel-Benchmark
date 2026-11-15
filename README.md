# Monte Carlo (O06), Etap 1

Założenia i zakres: [ZALOZENIA_PROJEKTU.md](ZALOZENIA_PROJEKTU.md).

## Szybki start

W WSL, z katalogu projektu uruchom jedno polecenie:

```bash
cd /mnt/c/Users/Komputer/Desktop/sem9/prir/Monte-Carlo-Parallel-Benchmark
python3 scripts/run_experiments.py
```

Skrypt sam kompiluje program (`make`), wykonuje wszystkie przebiegi, zapisuje wyniki do `data/` i wykresy do `plots/`. Nie trzeba nic kompilować ręcznie.

## Opcje skryptu (siatka wątków, N, ziarna)

Bez opcji skrypt robi pełną domyślną konfigurację. Siatkę można zmienić z wiersza poleceń, bez edycji kodu:

```bash
python3 scripts/run_experiments.py --help

# szybka próba, wyniki do osobnych katalogów (nie nadpisują data/ i plots/)
python3 scripts/run_experiments.py --threads 1,4,8 --seeds 5 --samples 10000,1000000 \
    --data-dir data_test --plots-dir plots_test

# pełny pomiar z własną siatką wątków
python3 scripts/run_experiments.py --threads 1,2,4,6,8,12,16,24,32 --omp-wait-policy passive
```

- `--threads`: siatka p, np. `1,2,4,8,12` (musi zawierać `1`). Domyślnie: potęgi dwójki do 2× liczby wątków logicznych plus sama liczba wątków logicznych komputera.
- `--samples`: siatka N (podzielne przez 10). `--seeds`: liczba ziaren (do raportu co najmniej 5).
- `--data-dir`, `--plots-dir`: dokąd zapisać wyniki. Dobrze dać każdemu komputerowi osobny katalog (np. `data_ryzen`), bo pomiary z różnych maszyn nie są porównywalne.
- `--omp-wait-policy passive`: ustawia `OMP_WAIT_POLICY` dla uruchomień. Przy p równym liczbie wątków logicznych domyślne oczekiwanie aktywne potrafi wydłużyć czas kilkukrotnie (zapaść S(p)); `passive` to usuwa. Zapisywane w `system_info.txt`.
- Wykresy przyspieszenia, efektywności i podziału kosztu używają największego N z siatki i p nieprzekraczających liczby wątków logicznych; większe p to oversubscription.

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

Wynik (jedna linia CSV): `estimate,error,ci_low,ci_high,std_error,time_core_sec,time_agg_sec`

## Wyniki

- `data/raw_results.csv`: każdy przebieg osobno
- `data/summary.csv`: mediana i rozrzut czasu, mediana błędu, pokrycie przedziałów ufności
- `data/cost_breakdown.csv`, `data/time_to_eps.csv`, `data/reference_check.csv`, `data/system_info.txt`
- `plots/`: wykresy oraz `plots/README.md` z opisem, jak je czytać

## Uwagi

- Pliki tekstowe w repozytorium powinny mieć zakończenia LF, inaczej `make` w WSL może nie działać.
- Przed sprawozdaniem zapisać konfigurację komputera (model CPU, liczba rdzeni, wersja WSL, wersja gcc).
