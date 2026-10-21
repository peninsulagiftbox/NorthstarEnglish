import os
from pathlib import Path
import subprocess
import sys
import unittest


class RunnerTests(unittest.TestCase):
    def test_sigterm_stops_and_reaps_its_child_without_deadlock(self):
        runner = Path(__file__).parents[1] / "service_runner.py"
        with subprocess.Popen([sys.executable, str(runner), "test", sys.executable, "-c",
                               "import os,time; print(os.getpid(), flush=True); time.sleep(30)"],
                              stdout=subprocess.PIPE, text=True) as process:
            child = int(process.stdout.readline())
            try:
                process.terminate()
                self.assertEqual(0, process.wait(timeout=5))
                with self.assertRaises(ProcessLookupError):
                    os.kill(child, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    unittest.main()
