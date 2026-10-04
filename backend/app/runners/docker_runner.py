"""Run a Python bundle inside a disposable, locked-down Docker container.

Security properties (see README "Isolated execution"):
  * ``--network none``             no network
  * ``--user 1000:1000``           non-root
  * ``--read-only``                read-only root filesystem
  * bundle and inputs mounted read-only; hidden labels are never written anywhere near here
  * ``--tmpfs /tmp:size=...``      small writable scratch space
  * ``--memory`` / ``--cpus`` / ``--pids-limit``
  * ``--cap-drop ALL`` + ``--security-opt no-new-privileges``
  * ``--rm`` and an explicit ``docker kill`` on timeout

The container prints a single JSON document on stdout; student prints go to stderr.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from pathlib import Path

from app.config import Settings
from app.core.submission_adapter import SubmissionError, SubmissionTimeout
from app.runners.base import RunnerResult

log = logging.getLogger(__name__)

MAX_STDOUT = 64 * 1024 * 1024


class DockerRunner:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    # -- mount mapping ---------------------------------------------------------------------
    def _mount_mode(self) -> str:
        mode = self.s.runner_mount_mode
        if mode == "auto":
            return "volume" if self.s.runner_data_volume else "bind"
        return mode

    def _mount_arg(self, path: Path, target: str) -> str:
        """Build a ``--mount`` argument making ``path`` visible read-only inside the sandbox."""
        path = path.resolve()
        mode = self._mount_mode()
        if mode == "volume":
            root = Path(self.s.runner_volume_mountpoint).resolve()
            try:
                rel = path.relative_to(root)
            except ValueError:
                raise RuntimeError(
                    f"{path} is not inside the data volume mount point {root}"
                ) from None
            return (
                f"type=volume,src={self.s.runner_data_volume},dst={target},"
                f"volume-subpath={rel.as_posix()},readonly"
            )
        data_dir = self.s.data_dir.resolve()
        if self.s.runner_host_data_dir:
            try:
                rel = path.relative_to(data_dir)
            except ValueError:
                raise RuntimeError(f"{path} is not inside data_dir {data_dir}") from None
            host_path = Path(self.s.runner_host_data_dir) / rel
        else:
            host_path = path
        return f"type=bind,src={host_path.as_posix()},dst={target},readonly"

    # -- execution -------------------------------------------------------------------------
    def build_command(self, name: str, bundle_dir: Path, inputs_dir: Path) -> list[str]:
        s = self.s
        return [
            s.runner_docker_binary,
            "run",
            "--rm",
            "-i",
            "--name",
            name,
            "--network",
            "none",
            "--user",
            s.runner_user,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            s.runner_memory,
            "--memory-swap",
            s.runner_memory,
            "--cpus",
            str(s.runner_cpus),
            "--pids-limit",
            str(s.runner_pids_limit),
            "--tmpfs",
            f"/tmp:rw,nosuid,nodev,size={s.runner_tmp_size}",
            "--mount",
            self._mount_arg(bundle_dir, "/bundle"),
            "--mount",
            self._mount_arg(inputs_dir, "/inputs"),
            "--env",
            "HOME=/tmp",
            "--env",
            "OMP_NUM_THREADS=1",
            "--env",
            "MKL_NUM_THREADS=1",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            s.runner_image,
        ]

    def run(self, *, bundle_dir: Path, inputs_dir: Path, workdir: Path) -> RunnerResult:
        name = f"arena-run-{uuid.uuid4().hex[:12]}"
        cmd = self.build_command(name, bundle_dir, inputs_dir)
        timeout = self.s.runner_timeout_seconds
        log.info("runner start %s (timeout %ss)", name, timeout)
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=timeout + 5, stdin=subprocess.DEVNULL, check=False
            )
        except subprocess.TimeoutExpired as exc:
            self._kill(name)
            tail = _tail(exc.stderr)
            raise SubmissionTimeout(
                f"Submission exceeded the {timeout} second time limit and was terminated.",
                [tail] if tail else [],
            ) from None
        runtime = time.monotonic() - t0
        stderr_tail = _tail(proc.stderr)

        if proc.returncode != 0 and not proc.stdout.strip():
            if proc.stderr.lstrip().startswith(b"docker:") or proc.returncode in (125, 126, 127):
                # The Docker CLI itself failed (bad mount, missing image, daemon down): this is
                # an infrastructure problem, not the student's fault.
                raise RuntimeError(f"docker run failed (exit {proc.returncode}): {stderr_tail}")
            if proc.returncode == 137 or b"OOM" in proc.stderr:
                raise SubmissionError(
                    f"Submission was killed (exit {proc.returncode}); it probably exceeded the "
                    f"memory limit of {self.s.runner_memory}.",
                    [stderr_tail] if stderr_tail else [],
                )
            raise SubmissionError(
                f"Submission container failed (exit code {proc.returncode}).",
                [stderr_tail] if stderr_tail else [],
            )
        try:
            payload = json.loads(proc.stdout[-MAX_STDOUT:].decode("utf-8", "replace"))
        except (ValueError, UnicodeDecodeError):
            raise SubmissionError(
                "Runner produced no parseable result.", [stderr_tail] if stderr_tail else []
            ) from None
        if not payload.get("ok"):
            msg = payload.get("error") or "Submission failed inside the sandbox."
            details = [d for d in [payload.get("traceback", ""), stderr_tail] if d]
            raise SubmissionError(str(msg)[:500], details)
        return RunnerResult(
            predictions=payload.get("predictions", {}),
            runtime_seconds=round(runtime, 3),
            stderr_tail=stderr_tail,
            info={"timings": payload.get("timings", {})},
        )

    def _kill(self, name: str) -> None:
        try:
            subprocess.run(
                [self.s.runner_docker_binary, "kill", name],
                capture_output=True,
                timeout=20,
                check=False,
            )
            subprocess.run(
                [self.s.runner_docker_binary, "rm", "-f", name],
                capture_output=True,
                timeout=20,
                check=False,
            )
        except subprocess.TimeoutExpired:
            log.warning("could not kill runner container %s", name)
            return
        # Removal is asynchronous; wait briefly so no stray container outlives the job.
        for _ in range(50):
            r = subprocess.run(
                [self.s.runner_docker_binary, "inspect", "--format", "{{.Id}}", name],
                capture_output=True,
                timeout=20,
                check=False,
            )
            if r.returncode != 0:
                return
            time.sleep(0.1)
        log.warning("runner container %s still present after kill", name)


def _tail(data: bytes | None, limit: int = 4000) -> str:
    if not data:
        return ""
    text = data.decode("utf-8", "replace")
    return text[-limit:].strip()
