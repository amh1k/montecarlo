#!/usr/bin/env python3
"""Capture reproducible Monte Carlo measurements using only the standard library."""
import argparse
import csv
import datetime
import io
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FIELDS = 'mode,trials,seed,ranks,threads_per_rank,hits,pi_estimate,seconds'.split(',')
CONFIGS = [('seq', 1, 1), ('omp', 1, 1), ('omp', 1, 2), ('omp', 1, 4),
           ('mpi', 1, 1), ('mpi', 2, 1), ('mpi', 4, 1),
           ('hybrid', 1, 4), ('hybrid', 2, 2), ('hybrid', 4, 1)]


def physical_cpus():
    """Choose one allowed logical CPU per physical core (Linux)."""
    cores = {}
    for cpu in sorted(os.sched_getaffinity(0)):
        topology = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        key = ((topology / 'physical_package_id').read_text().strip(),
               (topology / 'core_id').read_text().strip())
        cores.setdefault(key, cpu)
    return list(cores.values())


def configurations(cpus):
    return [c for c in CONFIGS if c[1] * c[2] <= len(cpus)]


def accuracy_configurations(configs):
    """Choose the largest available layout per mode, preferring balanced hybrid layouts."""
    selected = []
    for mode in ('seq', 'omp', 'mpi', 'hybrid'):
        layout = max((config for config in configs if config[0] == mode),
                     key=lambda c: (c[1] * c[2], min(c[1], c[2])), default=None)
        if layout is not None:
            selected.append(layout)
    return selected


def validate(output, mode, trials, seed, ranks, threads):
    reader = csv.DictReader(io.StringIO(output))
    if reader.fieldnames != FIELDS:
        raise ValueError('incorrect CSV header')
    rows = list(reader)
    if len(rows) != 1 or set(rows[0]) != set(FIELDS) or None in rows[0].values():
        raise ValueError('expected exactly one complete CSV result')
    row = rows[0]
    expected = dict(mode=mode, trials=str(trials), seed=str(seed), ranks=str(ranks),
                    threads_per_rank=str(threads))
    if any(row[k] != v for k, v in expected.items()):
        raise ValueError('result does not match requested workload or worker layout')
    hits, estimate, seconds = int(row['hits']), float(row['pi_estimate']), float(row['seconds'])
    if not (0 <= hits <= trials and math.isfinite(estimate) and
            math.isclose(estimate, 4 * hits / trials, rel_tol=1e-15) and
            math.isfinite(seconds) and seconds > 0):
        raise ValueError('invalid counts, estimate or runtime')
    return row


def worker(threads, executable, trials, seed):
    # MPICH and Open MPI export these rank identifiers before invoking Python.
    rank_text = os.environ.get('PMI_RANK', os.environ.get('OMPI_COMM_WORLD_RANK'))
    if rank_text is None:
        raise RuntimeError('MPI launcher did not provide PMI_RANK or OMPI_COMM_WORLD_RANK')
    rank = int(rank_text)
    cpus = [int(c) for c in os.environ['BENCH_CPUS'].split(',')]
    assigned = cpus[rank * threads:(rank + 1) * threads]
    if len(assigned) != threads:
        raise RuntimeError('insufficient assigned CPUs')
    os.sched_setaffinity(0, assigned)
    os.execv(executable, [executable, trials, seed])


def command(config, trials, seed, launcher, launcher_args, cpus):
    mode, ranks, threads = config
    executable = str(ROOT / 'build' / mode)
    if mode in ('mpi', 'hybrid'):
        return [launcher, *launcher_args, '-n', str(ranks), sys.executable,
                str(Path(__file__).resolve()), '--worker', str(threads), executable,
                str(trials), str(seed)]
    return ['taskset', '-c', ','.join(map(str, cpus[:threads])), executable,
            str(trials), str(seed)]


def run_process(cmd, env, timeout):
    # Kill the entire MPI process group on timeout, including rank workers.
    with subprocess.Popen(cmd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            raise RuntimeError(f'timed out after {timeout}s; stdout={stdout!r}; stderr={stderr!r}')
        return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)


def capture(cmd):
    result = subprocess.run(cmd, text=True, capture_output=True)
    return {'command': cmd, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new output directory')
    parser.add_argument('--trials', type=int, default=10**10)
    parser.add_argument('--pilot-trials', type=int, default=10**7)
    parser.add_argument('--repetitions', type=int, default=2)
    parser.add_argument('--stages', nargs='+', choices=['pilot', 'scaling', 'accuracy'], default=['pilot', 'scaling', 'accuracy'])
    parser.add_argument('--accuracy-trials', type=int, nargs='+', default=[10**4, 10**5, 10**6, 10**7])
    parser.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2, 3, 42])
    parser.add_argument('--mpiexec', default='mpiexec')
    parser.add_argument('--mpi-args', default='', help='launcher options, e.g. "-bind-to none"')
    parser.add_argument('--timeout', type=float, default=1800)
    args = parser.parse_args()
    if any(n <= 0 or n >= 2**64 for n in [args.trials, args.pilot_trials, *args.accuracy_trials]) or args.repetitions < 1:
        parser.error('trial counts must fit positive uint64; repetitions must be positive')
    if any(s < 0 or s >= 2**64 for s in args.seeds) or args.timeout <= 0:
        parser.error('seeds must fit uint64; timeout must be positive')
    cpus = physical_cpus()
    configs = configurations(cpus)
    for mode in {c[0] for c in configs}:
        if not os.access(ROOT / 'build' / mode, os.X_OK):
            parser.error(f'build/{mode} missing; build all four modes first')
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'platform': platform.platform(), 'python': sys.version, 'physical_cpus': cpus,
                'binary_sha256': {mode: hashlib.sha256((ROOT / 'build' / mode).read_bytes()).hexdigest() for mode in {c[0] for c in configs}},
                'configurations': configs, 'arguments': vars(args) | {'output': str(args.output)},
                'invocation': sys.argv, 'environment': {k: v for k, v in os.environ.items()
                    if k.startswith(('OMP_', 'MPICH_', 'HYDRA_', 'OMPI_')) or k == 'LD_LIBRARY_PATH'},
                'probes': [capture(c) for c in [['git', 'rev-parse', 'HEAD'], ['git', 'status', '--short'],
                    ['lscpu'], ['cc', '--version'], ['make', '-Bn', 'seq', 'omp', 'mpi', 'hybrid'],
                    [args.mpiexec, '--version']]],
                'placement': 'One logical CPU per physical core; disjoint contiguous slices per MPI rank; OpenMP bound to cores.'}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    env = os.environ | {'OMP_DYNAMIC': 'FALSE', 'OMP_PROC_BIND': 'TRUE', 'OMP_PLACES': 'cores',
                        'BENCH_CPUS': ','.join(map(str, cpus))}
    jobs = [('pilot', c, args.pilot_trials, 42, 1) for c in configs]
    jobs += [('scaling', c, args.trials, 42, rep) for rep in range(1, args.repetitions + 1) for c in configs]
    accuracy_configs = accuracy_configurations(configs)
    jobs += [('accuracy', c, n, seed, 1) for n in args.accuracy_trials for seed in args.seeds
             for c in accuracy_configs]
    jobs = [job for job in jobs if job[0] in args.stages]
    with (args.output / 'runs.jsonl').open('w') as log, (args.output / 'raw.csv').open('w', newline='') as raw:
        writer = csv.DictWriter(raw, fieldnames=['stage', 'repetition', *FIELDS], lineterminator='\n')
        writer.writeheader()
        for stage, config, n, seed, rep in jobs:
            env['OMP_NUM_THREADS'] = str(config[2])
            cmd = command(config, n, seed, args.mpiexec, shlex.split(args.mpi_args), cpus)
            record = dict(stage=stage, repetition=rep, command=cmd,
                          environment={k: env[k] for k in ['OMP_DYNAMIC', 'OMP_PROC_BIND', 'OMP_PLACES', 'OMP_NUM_THREADS', 'BENCH_CPUS']},
                          started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            print(f'{stage} {config} N={n} seed={seed} repetition={rep}', flush=True)
            started = time.monotonic()
            try:
                result = run_process(cmd, env, args.timeout)
                record.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
                if result.returncode:
                    raise RuntimeError(f'program exited {result.returncode}: {result.stderr}')
                row = validate(result.stdout, config[0], n, seed, config[1], config[2])
                writer.writerow(dict(stage=stage, repetition=rep, **row))
                raw.flush()
            except Exception as error:
                record['error'] = str(error)
                raise
            finally:
                record['wall_seconds'] = time.monotonic() - started
                log.write(json.dumps(record) + '\n')
                log.flush()
    (args.output / 'COMPLETE').write_text('All requested measurements completed successfully.\n')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        worker(int(sys.argv[2]), *sys.argv[3:])
    else:
        main()
