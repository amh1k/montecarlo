#!/usr/bin/env python3
"""Summarize measured runs; no timing extrapolation or graph dependencies."""
import argparse
import csv
from collections import defaultdict
import math
from pathlib import Path
import statistics


def summarize(directory):
    if not (directory / 'COMPLETE').exists():
        raise ValueError('experiment is incomplete; inspect runs.jsonl')
    with (directory / 'raw.csv').open() as source:
        rows = list(csv.DictReader(source))
    scaling, accuracy = defaultdict(list), defaultdict(list)
    for row in rows:
        key = tuple(row[k] for k in ('mode', 'trials', 'seed', 'ranks', 'threads_per_rank'))
        if row['stage'] == 'scaling':
            scaling[key].append(float(row['seconds']))
        elif row['stage'] == 'accuracy':
            accuracy[key[:2] + key[3:]].append(float(row['pi_estimate']) - math.pi)
    lines = []
    for (mode, trials, seed, ranks, threads), times in scaling.items():
        baseline = scaling.get(('seq', trials, seed, '1', '1'))
        if not baseline:
            raise ValueError(f'missing sequential baseline for N={trials}, seed={seed}')
        seconds = statistics.median(times)
        speedup = statistics.median(baseline) / seconds
        lines.append([mode, trials, seed, ranks, threads, len(times), min(times), seconds,
                      max(times), speedup, speedup / (int(ranks) * int(threads))])
    with (directory / 'scaling_summary.csv').open('w', newline='') as target:
        writer = csv.writer(target)
        writer.writerow(['mode', 'trials', 'seed', 'ranks', 'threads_per_rank', 'repetitions',
                         'min_seconds', 'median_seconds', 'max_seconds', 'speedup', 'efficiency'])
        writer.writerows(lines)
    with (directory / 'accuracy_summary.csv').open('w', newline='') as target:
        writer = csv.writer(target)
        writer.writerow(['mode', 'trials', 'ranks', 'threads_per_rank', 'seeds', 'mean_absolute_error',
                         'root_mean_squared_error', 'rmse_times_sqrt_n'])
        for (mode, trials, ranks, threads), errors in accuracy.items():
            rmse = math.sqrt(statistics.mean(e * e for e in errors))
            writer.writerow([mode, trials, ranks, threads, len(errors),
                             statistics.mean(abs(e) for e in errors), rmse, rmse * math.sqrt(int(trials))])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    summarize(parser.parse_args().directory)
