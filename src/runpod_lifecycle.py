import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class RunPodLifecycleManager:
    def __init__(
        self,
        *,
        pod_id: str,
        base_url: str,
        idle_seconds: int = 300,
        startup_timeout: int = 300,
        poll_seconds: int = 5,
        state_dir: Path | None = None,
        runpodctl: str = "runpodctl",
    ):
        self.pod_id = pod_id
        self.base_url = base_url.rstrip("/")
        self.health_url = self.base_url + "/v1/models"
        self.idle_seconds = idle_seconds
        self.startup_timeout = startup_timeout
        self.poll_seconds = poll_seconds
        self.runpodctl = runpodctl
        self.state_dir = (
            state_dir
            or Path.home() / ".fixsimple" / "runpod"
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / f"{pod_id}.json"
        self.lock_path = self.state_dir / f"{pod_id}.lock"
        self.audit_path = self.state_dir / f"{pod_id}.audit.jsonl"

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str,
        environ=None,
    ):
        env = environ or os.environ
        pod_id = env.get("FIXSIMPLE_RUNPOD_ID")
        if not pod_id:
            return None

        return cls(
            pod_id=pod_id,
            base_url=base_url,
            idle_seconds=int(
                env.get(
                    "FIXSIMPLE_RUNPOD_IDLE_SECONDS",
                    "300",
                )
            ),
            startup_timeout=int(
                env.get(
                    "FIXSIMPLE_RUNPOD_STARTUP_TIMEOUT",
                    "300",
                )
            ),
            poll_seconds=int(
                env.get(
                    "FIXSIMPLE_RUNPOD_POLL_SECONDS",
                    "5",
                )
            ),
            state_dir=Path(
                env.get(
                    "FIXSIMPLE_RUNPOD_STATE_DIR",
                    str(
                        Path.home()
                        / ".fixsimple"
                        / "runpod"
                    ),
                )
            ),
            runpodctl=env.get(
                "FIXSIMPLE_RUNPODCTL",
                "runpodctl",
            ),
        )

    @contextmanager
    def _locked_state(self):
        self.lock_path.touch(exist_ok=True)

        with self.lock_path.open("r+") as lock_file:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX,
            )

            state = self._read_state()

            try:
                yield state
                self._write_state(state)
            finally:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_UN,
                )

    def _read_state(self) -> dict:
        if not self.state_path.exists():
            return {
                "generation": 0,
                "last_activity": 0.0,
                "leases": {},
            }

        try:
            data = json.loads(
                self.state_path.read_text()
            )
        except (OSError, json.JSONDecodeError):
            data = {}

        return {
            "generation": int(
                data.get("generation", 0)
            ),
            "last_activity": float(
                data.get("last_activity", 0.0)
            ),
            "leases": (
                data.get("leases")
                if isinstance(
                    data.get("leases"),
                    dict,
                )
                else {}
            ),
        }

    def _write_state(self, state: dict) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.state_path.name + ".",
            dir=self.state_dir,
        )
        tmp_path = Path(tmp_name)

        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(
                    state,
                    handle,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(
                tmp_path,
                self.state_path,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def _audit(self, event: str, **details) -> None:
        record = {
            "event": event,
            "timestamp": time.time(),
            "pod_id": self.pod_id,
            **details,
        }

        with self.audit_path.open("a") as handle:
            handle.write(
                json.dumps(
                    record,
                    sort_keys=True,
                )
                + "\n"
            )

    def _health_ok(self) -> bool:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--fail",
                "--max-time",
                "5",
                self.health_url,
            ],
            text=True,
            capture_output=True,
        )
        return result.returncode == 0

    def ensure_ready(self) -> None:
        if self._health_ok():
            return

        self._audit("pod_start_requested")

        result = subprocess.run(
            [
                self.runpodctl,
                "pod",
                "start",
                self.pod_id,
            ],
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            self._audit(
                "pod_start_failed",
                returncode=result.returncode,
                stderr=result.stderr.strip(),
            )
            raise RuntimeError(
                "RunPod start failed\n"
                f"exit={result.returncode}\n"
                f"stdout={result.stdout}\n"
                f"stderr={result.stderr}"
            )

        deadline = time.time() + self.startup_timeout

        while time.time() < deadline:
            if self._health_ok():
                self._audit("pod_ready")
                return

            time.sleep(self.poll_seconds)

        self._audit("pod_start_timeout")
        raise TimeoutError(
            "RunPod did not become healthy before timeout"
        )

    def begin_request(
        self,
        *,
        request_timeout: int,
    ) -> str:
        self.ensure_ready()

        lease_id = uuid.uuid4().hex
        now = time.time()
        lease_expiry = (
            now
            + request_timeout
            + self.idle_seconds
        )

        with self._locked_state() as state:
            state["generation"] += 1
            state["last_activity"] = now
            state["leases"][lease_id] = lease_expiry
            generation = state["generation"]

        self._audit(
            "lease_acquired",
            lease_id=lease_id,
            expires_at=lease_expiry,
        )
        self._spawn_idle_watcher(generation)
        return lease_id

    def end_request(self, lease_id: str) -> None:
        now = time.time()

        with self._locked_state() as state:
            state["leases"].pop(
                lease_id,
                None,
            )
            state["generation"] += 1
            state["last_activity"] = now
            generation = state["generation"]

        self._audit(
            "lease_released",
            lease_id=lease_id,
        )
        self._spawn_idle_watcher(generation)

    def _spawn_idle_watcher(
        self,
        generation: int,
    ) -> None:
        subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--watch-idle",
                "--pod-id",
                self.pod_id,
                "--base-url",
                self.base_url,
                "--idle-seconds",
                str(self.idle_seconds),
                "--startup-timeout",
                str(self.startup_timeout),
                "--poll-seconds",
                str(self.poll_seconds),
                "--state-dir",
                str(self.state_dir),
                "--runpodctl",
                self.runpodctl,
                "--generation",
                str(generation),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def watch_idle(
        self,
        generation: int,
    ) -> None:
        while True:
            now = time.time()

            with self._locked_state() as state:
                if state["generation"] != generation:
                    return

                leases = {
                    lease_id: float(expiry)
                    for lease_id, expiry
                    in state["leases"].items()
                    if float(expiry) > now
                }
                state["leases"] = leases

                latest_lease = max(
                    leases.values(),
                    default=0.0,
                )
                stop_after = max(
                    state["last_activity"]
                    + self.idle_seconds,
                    latest_lease,
                )

                if leases or now < stop_after:
                    sleep_for = max(
                        0.5,
                        min(
                            5.0,
                            stop_after - now,
                        ),
                    )
                else:
                    state["generation"] += 1
                    stop_generation = state["generation"]
                    sleep_for = None

            if sleep_for is not None:
                time.sleep(sleep_for)
                continue

            self._audit(
                "pod_stop_requested",
                generation=stop_generation,
            )

            result = subprocess.run(
                [
                    self.runpodctl,
                    "pod",
                    "stop",
                    self.pod_id,
                ],
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                self._audit("pod_stopped")
                return

            self._audit(
                "pod_stop_failed",
                returncode=result.returncode,
                stderr=result.stderr.strip(),
            )
            return


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--watch-idle",
        action="store_true",
    )
    parser.add_argument("--pod-id")
    parser.add_argument("--base-url")
    parser.add_argument(
        "--idle-seconds",
        type=int,
        default=300,
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=300,
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
    )
    parser.add_argument(
        "--runpodctl",
        default="runpodctl",
    )
    parser.add_argument(
        "--generation",
        type=int,
    )

    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.watch_idle:
        raise SystemExit(
            "runpod_lifecycle is not a standalone command"
        )

    manager = RunPodLifecycleManager(
        pod_id=args.pod_id,
        base_url=args.base_url,
        idle_seconds=args.idle_seconds,
        startup_timeout=args.startup_timeout,
        poll_seconds=args.poll_seconds,
        state_dir=args.state_dir,
        runpodctl=args.runpodctl,
    )
    manager.watch_idle(args.generation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
