# Założenia projektu: Monte Carlo (O06), v0

Dokument nadrzędny dla pracy. W razie sprzeczności z `monte_carlo_etap1_specyfikacja_v2.pdf` obowiązuje ten plik.

Statusy: **[ustalone]** / **[propozycja]** / **[otwarte]**

---

## 1. Kontekst

- Przedmiot: PRiR 2026/2027, temat O06 (Monte Carlo z kontrolą dokładności), zespół 2 osoby.
- Etap 1: C (silnik) + OpenMP + Python (uruchomienia, statystyki, wykresy). **[ustalone]**
- Metody: klasyczna Monte Carlo oraz próbkowanie warstwowe (dodatek dla 2 osób). **[ustalone]**
- Python i uruchomienia w **WSL**, nie natywnie w Windows. **[ustalone]**
- MPI i CUDA/OpenCL poza Etapem 1.

---

## 2. Program w C

### Funkcje testowe
- `sin` na [0, π], wynik dokładny 2.0.
- `poly` = 3(x−1)² + 4 na [0, 2], wynik dokładny 10.0.

### Metody
- `classic`: N próbek, x = a + u·(b − a).
- `stratified`: K warstw szerokości w = (b − a)/K, po n = N/K próbek w każdej. Wymagane N podzielne przez K. **[propozycja]**
  - Î = Σ_s w · μ_s (bez dodatkowego dzielenia przez K)
  - Var(Î) = Σ_s w² · s_s² / n

### Losowość
- Generator SplitMix64 z ziarnem i indeksem próbki (counter-based). **[ustalone]**
- Dla `classic`: indeks próbki i. Dla `stratified`: indeks globalny s·n + i.
- Każdy przebieg ma jawne ziarno.
- Na tej samej liczbie próbek i tych samych ziarnach obie metody mają ten sam budżet. Porównanie robimy w sprawozdaniu, bez osobnego eksperymentu. **[ustalone]**

### Parametry CLI **[ustalone]**
- `--func sin|poly`
- `--method classic|stratified`
- `--samples N`
- `--layers K` (tylko dla stratified; nazwa zamiast `--strata`)
- `--batch B` (rozmiar partii, domyślnie 10000)
- `--threads p`
- `--seed s`
- `--timing full|rng` (`rng`: tylko losowanie, do oszacowania kosztu generatora)
- `--impl omp|seq` (`seq`: referencja sekwencyjna bez OpenMP)

### Wyjście
Jedna linia CSV na stdout: `estimate,error,ci_low,ci_high,std_error,time_core_sec,time_agg_sec`

- `error` = |estymata − dokładna|
- `ci` = 95% (1.96·SE)
- `time_core_sec` = pętla próbkowania (losowanie, f(x), sumy partii), mierzona w C (`omp_get_wtime`)
- `time_agg_sec` = scalanie partii, estymata i wariancja

### Walidacja **[ustalone]**
- N ≤ 0, p ≤ 0, K ≤ 0 → błąd.
- Tryb stratified: N % K ≠ 0 → błąd.

---

## 3. Pomiary

- Rozgrzewka: jedno uruchomienie każdej konfiguracji przed serią, bez zapisu do CSV. **[ustalone]**
- Referencja sekwencyjna (`--impl seq`, bez OpenMP) do sprawdzania poprawności. **[ustalone]**
- Każda konfiguracja: co najmniej 5 przebiegów z różnymi ziarnami. **[ustalone]**
- Siatka wątków: 1, 2, 4, 8, … do 2× liczby wątków logicznych. Przebiegi powyżej liczby wątków logicznych opisujemy w sprawozdaniu jako oversubscription. **[ustalone]**
- Czas mierzony tylko w C i zbierany przez Python. **[ustalone]**
- Python zapisuje surowe wyniki (każdy przebieg osobno) do `data/`.
- Python liczy: medianę, rozrzut (odchylenie standardowe lub IQR), CI.
- Wykresy: speedup S(p) = T(1)/T(p), efektywność E(p) = S(p)/p, błąd względem N dla obu metod, czas do zadanej dokładności z wykresu błąd vs czas dla różnych N.

---

## 4. Python

- `scripts/run_experiments.py`: buduje program (`make`), uruchamia przebiegi, zapisuje CSV.
- `analysis/` lub ten sam skrypt: statystyki i wykresy.
- Biblioteki: standardowe + matplotlib.

---

## 5. Struktura plików (v0)

```
monte-carlo-parallel-benchmark/
├── ZALOZENIA_PROJEKTU.md
├── README.md
├── Makefile
├── src/
│   ├── functions.h / .c
│   ├── rng.h / .c           # SplitMix64
│   ├── monte_carlo.h / .c   # classic, stratified, OpenMP
│   └── main.c               # CLI, wyjście CSV
├── scripts/
│   └── run_experiments.py
├── data/                    # surowe CSV
└── plots/                   # wykresy
```

Pliki tekstowe z zakończeniami LF (WSL). **[propozycja]**

---

## 6. Poprawki względem specyfikacji v2

| Problem w v2 | Poprawka |
|---|---|
| Estymator warstwowy dzieli przez K dwukrotnie | Î = Σ w·μ_s |
| `rand_r` i `RAND_MAX` (32767 na Windows) | SplitMix64 |
| Seed z czasu, brak powtarzalności | Jawne `--seed` |
| Równoległość po warstwach (K=10, p=8 → słabe skalowanie) | Równoległość po próbkach |
| Brak metody klasycznej | `--method classic` |
| Jeden przebieg na konfigurację | ≥5 przebiegów z różnymi ziarnami |
| Brak CI | CI 95% w wyjściu |
| Brak walidacji argumentów | Walidacja (sekcja 2) |

---

## 7. Otwarte kwestie

1. Sprawozdanie: zakres porównania klasycznej i warstwowej (ten sam N, ziarna) — jak szeroko opisać.
2. Czy wykres czasu do zadanej dokładności wystarczy w formie błąd vs czas.

---

## 8. Dziennik zmian

- v0: uproszczenie do wersji studenckiej, bez rozgrzewki, bez pomiaru czasu pełnego, bez wersji sekwencyjnej jako osobnego trybu, bez ustawień wiązania wątków, nazwa parametru `--layers`.
