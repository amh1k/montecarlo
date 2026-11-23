CFLAGS ?= -O3 -Wall -Wextra -Wpedantic
OMPFLAGS ?= -fopenmp

.PHONY: all seq omp
all: seq omp

seq: build/seq
omp: build/omp

build/seq: src/seq.c src/common.h Makefile | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(LDFLAGS) -o $@ $< $(LDLIBS)

build/omp: src/omp.c src/common.h Makefile | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(OMPFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

build:
	mkdir -p $@
