# Wykresy: jak je czytać

Wszystkie wykresy i tabele generuje `scripts/run_experiments.py` z plików w `data/`.
Konfiguracja sprzętu: `data/system_info.txt`.

## Parametry eksperymentu

- Funkcje: sin(x) na [0, π] (wynik dokładny 2), 3(x-1)²+4 na [0, 2] (wynik dokładny 10).
- Metody: klasyczna (jedna warstwa) i warstwowa (K = 10 warstw).
- Liczba próbek N: 10 000, 100 000, 1 000 000, 10 000 000. Te same N dla obu metod.
- Liczba wątków p: 1, 2, 4, 8, 16, 32. Wątków logicznych jest 16; wartości powyżej są oversubscription i nie są na wykresach przyspieszenia.
- Rozmiar partii: 10 000 próbek. Partie są rozdzielane między wątki, więc przy N mniejszym niż p × rozmiar partii nie wszystkie wątki mają pracę. Dane dla małych N i dużych p nie pokazują wtedy prawdziwego skalowania; wykresy przyspieszenia używają N = 10⁷.
- Ziarna: 20 na konfigurację. Przed każdą konfiguracją jedno uruchomienie rozgrzewkowe, którego wynik nie trafia do danych.
- Czas rdzenia: pętla próbkowania w C (losowanie, f(x), sumy partii). Czas pełny: całe uruchomienie programu mierzone w Pythonie.
- Punkt na wykresie to mediana z 20 ziaren. Słupki błędów to rozstęp międzykwartylowy: od kwartyla 1 (Q1) do kwartyla 3 (Q3).

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
- Przy 20 ziarnach udział zmienia się skokowo co 1/20 ≈ 0,05.
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
