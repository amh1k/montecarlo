import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('summary', Path(__file__).resolve().parents[1] / 'scripts/summarize.py')
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


class SummaryTests(unittest.TestCase):
    def test_equal_workload_median_and_efficiency(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'COMPLETE').touch()
            (path / 'raw.csv').write_text(
                'stage,mode,trials,seed,ranks,threads_per_rank,seconds,pi_estimate\n'
                'scaling,seq,100,42,1,1,10,3.14\n'
                'scaling,seq,100,42,1,1,14,3.14\n'
                'scaling,omp,100,42,1,4,3,3.14\n'
                'scaling,seq,1000,42,1,1,100,3.14\n'
                'pilot,seq,100,42,1,1,999,3.14\n'
                'accuracy,seq,100,0,1,1,1,3.1\n'
                'accuracy,seq,100,1,1,1,1,3.2\n')
            s.summarize(path)
            with (path / 'scaling_summary.csv').open() as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(float(rows[1]['speedup']), 4)
            self.assertEqual(float(rows[1]['efficiency']), 1)
            with (path / 'accuracy_summary.csv').open() as source:
                row = next(csv.DictReader(source))
            self.assertEqual(int(row['seeds']), 2)
            self.assertAlmostEqual(float(row['mean_absolute_error']), .05)

    def test_missing_matching_baseline_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'COMPLETE').touch()
            (path / 'raw.csv').write_text(
                'stage,mode,trials,seed,ranks,threads_per_rank,seconds,pi_estimate\n'
                'scaling,seq,100,0,1,1,10,3.14\n'
                'scaling,omp,100,42,1,4,3,3.14\n')
            with self.assertRaisesRegex(ValueError, 'missing sequential baseline'):
                s.summarize(path)

    def test_incomplete_rejected(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            s.summarize(Path(temp))
