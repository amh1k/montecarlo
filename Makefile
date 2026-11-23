CFLAGS ?= -O3 -Wall -Wextra -Wpedantic
OMPFLAGS ?= -fopenmp
MPICC ?= mpicc

.PHONY: all seq omp mpi
all: seq omp

seq: build/seq
omp: build/omp

mpi: build/mpi

build/seq: src/seq.c src/common.h Makefile | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(LDFLAGS) -o $@ $< $(LDLIBS)

build/omp: src/omp.c src/common.h Makefile | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(OMPFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

build/mpi: src/mpi.c src/common.h Makefile | build
	$(MPICC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(LDFLAGS) -o $@ $< $(LDLIBS)

build:
	mkdir -p $@
