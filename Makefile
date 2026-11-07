CC = gcc
CFLAGS = -O3 -fopenmp -Wall -Wextra
SRC = src/main.c src/functions.c src/rng.c src/monte_carlo.c
HDR = src/functions.h src/rng.h src/monte_carlo.h
TARGET = src/mc_app

all: $(TARGET)

$(TARGET): $(SRC) $(HDR)
	$(CC) $(CFLAGS) $(SRC) -o $(TARGET) -lm

clean:
	rm -f $(TARGET)
