import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from runpod_lifecycle import RunPodLifecycleManager


class RunPodLifecycleTests(unittest.TestCase):

    def test_ensure_ready_starts_stopped_pod_and_waits_for_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunPodLifecycleManager(
                pod_id="pod-123",
                base_url="https://pod.example",
                idle_seconds=5,
                startup_timeout=10,
                poll_seconds=1,
                state_dir=Path(tmp),
            )

            health = [False, True]

            def fake_health():
                return health.pop(0)

            manager._health_ok = fake_health

            completed = Mock()
            completed.returncode = 0
            completed.stdout = ""
            completed.stderr = ""

            with patch(
                "runpod_lifecycle.subprocess.run",
                return_value=completed,
            ) as run:
                manager.ensure_ready()

            run.assert_called_once_with(
                [
                    "runpodctl",
                    "pod",
                    "start",
                    "pod-123",
                ],
                text=True,
                capture_output=True,
            )

    def test_begin_and_end_request_manage_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunPodLifecycleManager(
                pod_id="pod-123",
                base_url="https://pod.example",
                idle_seconds=5,
                state_dir=Path(tmp),
            )

            with patch.object(
                manager,
                "ensure_ready",
            ), patch.object(
                manager,
                "_spawn_idle_watcher",
            ) as spawn:
                lease_id = manager.begin_request(
                    request_timeout=30,
                )

                state = manager._read_state()
                self.assertIn(
                    lease_id,
                    state["leases"],
                )

                manager.end_request(lease_id)

                state = manager._read_state()
                self.assertNotIn(
                    lease_id,
                    state["leases"],
                )

            self.assertEqual(
                spawn.call_count,
                2,
            )

    def test_idle_watcher_stops_pod_when_no_active_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RunPodLifecycleManager(
                pod_id="pod-123",
                base_url="https://pod.example",
                idle_seconds=5,
                state_dir=Path(tmp),
            )

            manager._write_state(
                {
                    "generation": 7,
                    "last_activity": 100.0,
                    "leases": {},
                }
            )

            completed = Mock()
            completed.returncode = 0
            completed.stdout = ""
            completed.stderr = ""

            with patch(
                "runpod_lifecycle.time.time",
                return_value=200.0,
            ), patch(
                "runpod_lifecycle.subprocess.run",
                return_value=completed,
            ) as run:
                manager.watch_idle(7)

            run.assert_called_once_with(
                [
                    "runpodctl",
                    "pod",
                    "stop",
                    "pod-123",
                ],
                text=True,
                capture_output=True,
            )

    def test_from_env_is_disabled_without_pod_id(self):
        manager = RunPodLifecycleManager.from_env(
            base_url="https://pod.example",
            environ={},
        )
        self.assertIsNone(manager)


if __name__ == "__main__":
    unittest.main()
