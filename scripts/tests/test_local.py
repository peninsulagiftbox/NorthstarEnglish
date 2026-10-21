import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import socket

spec = importlib.util.spec_from_file_location("local", Path(__file__).parents[1] / "local.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


class LocalTests(unittest.TestCase):
    def test_env_is_data_and_never_shell_evaluated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("JAVA_HOME=$(touch /tmp/northstar-must-not-exist)\n")
            self.assertEqual("$(touch /tmp/northstar-must-not-exist)", local.read_env(path)["JAVA_HOME"])

    def test_duplicate_or_unrecognized_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            for content in ("PATH=evil\n", "WEB_PORT=3100\nWEB_PORT=3101\n"):
                path.write_text(content)
                with self.assertRaises(RuntimeError):
                    local.read_env(path)

    def test_foreign_process_is_never_owned(self):
        import os
        self.assertFalse(local.owns_process({"pid": os.getpid(), "cwd": str(local.ROOT), "token": "unrelated-northstar-java-process"}))

    def test_init_selects_free_ports_and_never_rewrites_existing_env(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(local, "ROOT", Path(directory)), patch.object(local, "available", side_effect=lambda port: port not in (3100, 3308)):
            local.initialize()
            path = Path(directory) / ".env"
            before = path.read_bytes()
            self.assertEqual("3101", local.read_env(path)["WEB_PORT"])
            self.assertEqual("3309", local.read_env(path)["MYSQL_PORT"])
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            local.initialize()
            self.assertEqual(before, path.read_bytes())

    def test_stopped_listener_time_wait_does_not_look_like_a_port_conflict(self):
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            port = server.getsockname()[1]
            server.listen()
            self.assertFalse(local.available(port))
            with socket.create_connection(("127.0.0.1", port)):
                accepted, _ = server.accept()
                accepted.close()
        self.assertTrue(local.available(port))


if __name__ == "__main__":
    unittest.main()
