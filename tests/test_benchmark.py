"""Regression checks for benchmark collection and corrupt/misleading output."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('benchmark', Path(__file__).resolve().parents[1] / 'scripts/benchmark.py')
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)
HEADER = ','.join(b.FIELDS) + '\n'
VALID = HEADER + 'seq,10,42,1,1,8,3.2,0.001\n'


class BenchmarkTests(unittest.TestCase):
    def test_valid_result(self):
        self.assertEqual(b.validate(VALID, 'seq', 10, 42, 1, 1)['hits'], '8')

    def test_reject_corrupt_or_mismatched_results(self):
        variants = [VALID.replace('hits', 'count'), VALID + VALID, HEADER,
                    VALID.replace(',8,3.2,', ',11,4.4,'),
                    VALID.replace(',8,3.2,', ',8,3.1,'),
                    VALID.replace('0.001', 'nan'), VALID.replace('0.001', '-1'),
                    VALID.replace('seq,10', 'omp,10'), VALID.replace(',1,1,8', ',1,4,8'),
                    VALID.replace(',42,', ',0,'), VALID.replace('seq,10', 'seq,11'),
                    VALID.replace(',0.001', ''), VALID.replace('0.001', '0.001,extra')]
        for output in variants:
            with self.subTest(output=output), self.assertRaises((ValueError, TypeError)):
                b.validate(output, 'seq', 10, 42, 1, 1)

    def test_worker_limits(self):
        for cores in range(1, 5):
            configs = b.configurations(list(range(cores)))
            self.assertTrue(all(r * t <= cores for _, r, t in configs))
            self.assertIn(('seq', 1, 1), configs)

    def test_worker_placement(self):
        with patch.dict(b.os.environ, {'PMI_RANK': '1', 'BENCH_CPUS': '0,2,4,6'}), \
             patch.object(b.os, 'sched_setaffinity') as affinity, patch.object(b.os, 'execv') as execute:
            b.worker(2, '/example/hybrid', '10', '42')
            affinity.assert_called_once_with(0, [4, 6])
            execute.assert_called_once_with('/example/hybrid', ['/example/hybrid', '10', '42'])

    def test_failure_preserves_records_and_does_not_mark_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'run'
            args = ['benchmark.py', '--output', str(output)]
            failure = subprocess.CompletedProcess([], 7, '', 'launcher failed')
            with patch.object(b.sys, 'argv', args), patch.object(b, 'physical_cpus', return_value=[0]), \
                 patch.object(b.os, 'access', return_value=True), patch.object(b.Path, 'read_bytes', return_value=b'test'), patch.object(b, 'capture', return_value={}), \
                 patch.object(b, 'run_process', return_value=failure), patch('sys.stdout', new=io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'exited 7'):
                    b.main()
            self.assertFalse((output / 'COMPLETE').exists())
            record = json.loads((output / 'runs.jsonl').read_text())
            self.assertEqual(record['returncode'], 7)
            self.assertIn('launcher failed', record['error'])
            self.assertEqual((output / 'raw.csv').read_text().count('\n'), 1)

    def test_timeout_terminates_process_group(self):
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            b.run_process([b.sys.executable, '-c', 'import time; time.sleep(10)'], None, .05)

    def test_refuse_existing_output(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(b.sys, 'argv', ['benchmark.py', '--output', temp]), \
             patch.object(b, 'physical_cpus', return_value=[0]), patch.object(b.os, 'access', return_value=True):
            with self.assertRaises(FileExistsError):
                b.main()


if __name__ == '__main__':
    unittest.main()
