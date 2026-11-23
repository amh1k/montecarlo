#!/usr/bin/env python3
"""Plot the scaling and accuracy summaries of a completed experiment."""
import argparse
from collections import defaultdict
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


MODES = {
    'seq': ('Sequential', '#364152', 'o'),
    'omp': ('OpenMP', '#006CA9', 's'),
    'mpi': ('MPI', '#A94705', '^'),
    'hybrid': ('Hybrid', '#00745B', 'D'),
}


def read_summary(directory, name):
    with (directory / f'{name}_summary.csv').open(newline='') as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError(f'{name} summary contains no measurements')
    return rows


def figure(title, ylabel):
    fig, ax = plt.subplots(figsize=(8, 4), layout='constrained')
    ax.set_title(title, loc='left', fontweight='semibold', pad=12)
    ax.set_ylabel(ylabel)
    ax.spines[['right', 'top']].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#D7DDE5', linewidth=0.7)
    return fig, ax


def save(fig, output, name):
    fig.savefig(output / f'{name}.png', dpi=220, facecolor='white')
    plt.close(fig)


def scaling_plots(rows, output):
    workloads = {(int(row['trials']), row['seed']) for row in rows}
    if len(workloads) != 1:
        raise ValueError('scaling plots require one shared trial count and seed')
    trials, seed = workloads.pop()
    rows.sort(key=lambda row: (list(MODES).index(row['mode']), int(row['ranks']),
                               int(row['threads_per_rank'])))
    positions = range(len(rows))
    labels = [f"{MODES[row['mode']][0]}\n{row['ranks']}×{row['threads_per_rank']}"
              for row in rows]
    specifications = [
        ('runtime', 'Median runtime (seconds)', 'median_seconds'),
        ('speedup', 'Speedup (sequential / layout)', 'speedup'),
        ('efficiency', 'Efficiency (speedup / workers)', 'efficiency'),
    ]
    for name, ylabel, metric in specifications:
        fig, ax = figure(f'{name.capitalize()} · {trials:,} trials · seed {seed}', ylabel)
        for x, row in zip(positions, rows):
            _, color, marker = MODES[row['mode']]
            value = float(row[metric])
            if name == 'runtime':
                spread = [[value - float(row['min_seconds'])],
                          [float(row['max_seconds']) - value]]
                ax.errorbar(x, value, yerr=spread, color=color, marker=marker, capsize=4)
            else:
                ax.plot(x, value, color=color, marker=marker)
        if name == 'speedup':
            workers = [int(row['ranks']) * int(row['threads_per_rank']) for row in rows]
            ax.scatter(positions, workers, marker='_', color='#737C88', label='Ideal speedup')
            ax.legend(loc='upper left', frameon=False)
        if name == 'efficiency':
            ax.axhline(1, color='#737C88', linestyle='--', linewidth=1, label='Ideal efficiency')
            ax.legend(loc='lower left', frameon=False)
        ax.set_xticks(positions, labels, fontsize=8)
        ax.set_xlim(-0.55, len(rows) - 0.45)
        ax.set_ylim(bottom=0)
        ax.set_xlabel('Execution layout (ranks × threads per rank)')
        save(fig, output, name)


def accuracy_plot(rows, output):
    series = defaultdict(list)
    for row in rows:
        key = row['mode'], row['ranks'], row['threads_per_rank']
        series[key].append((int(row['trials']), float(row['root_mean_squared_error'])))
    seed_counts = sorted({int(row['seeds']) for row in rows})
    seed_label = '–'.join(str(n) for n in (seed_counts if len(seed_counts) == 1
                                         else (seed_counts[0], seed_counts[-1])))
    fig, ax = figure(f'Accuracy · {seed_label} seeds per point', 'RMSE of π estimate')
    for mode, ranks, threads in series:
        label, color, marker = MODES[mode]
        x, y = zip(*sorted(series[mode, ranks, threads]))
        ax.loglog(x, y, label=f'{label} {ranks}×{threads}', color=color, marker=marker)
    trials = sorted({int(row['trials']) for row in rows})
    reference = [math.sqrt(math.pi * (4 - math.pi) / n) for n in trials]
    ax.loglog(trials, reference, label='Binomial standard error', color='#737C88',
              linestyle='--', linewidth=1.3)
    ax.set_xlabel('Trials per run')
    ax.legend(frameon=False, fontsize=8, loc='upper right')
    save(fig, output, 'accuracy')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path, help='directory containing both summary CSVs')
    parser.add_argument('output', type=Path, help='directory for the generated PNG files')
    args = parser.parse_args()
    if not (args.experiment / 'COMPLETE').is_file():
        parser.error('experiment is incomplete; inspect its runs.jsonl')
    scaling = read_summary(args.experiment, 'scaling')
    accuracy = read_summary(args.experiment, 'accuracy')
    args.output.mkdir(parents=True, exist_ok=True)
    scaling_plots(scaling, args.output)
    accuracy_plot(accuracy, args.output)


if __name__ == '__main__':
    main()
