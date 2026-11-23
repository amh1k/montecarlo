CFLAGS ?= -O3 -Wall -Wextra -Wpedantic
MPICC ?= mpicc

.PHONY: all seq mpi
all: seq

seq: build/seq
mpi: build/mpi

build/seq: src/seq.c src/common.h Makefile | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(LDFLAGS) -o $@ $< $(LDLIBS)

build/mpi: src/mpi.c src/common.h Makefile | build
	$(MPICC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(LDFLAGS) -o $@ $< $(LDLIBS)

build:
	mkdir -p $@
