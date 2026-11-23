CFLAGS ?= -O3 -Wall -Wextra -Wpedantic

.PHONY: all seq
all: seq

seq: build/seq

build/seq: src/seq.c src/common.h Makefile | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c17 $(LDFLAGS) -o $@ $< $(LDLIBS)

build:
	mkdir -p $@
