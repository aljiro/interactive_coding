"""Application settings (environment variables / .env)."""

from __future__ import annotations

import socket
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DNNLS Live Arena"
    log_level: str = "INFO"

    # --- storage -------------------------------------------------------------
    database_url: str = "postgresql+psycopg://arena:arena@db:5432/arena"
    data_dir: Path = Path("/data")
    static_dir: Path | None = None  # built frontend (served from the same origin)

    # --- auth ----------------------------------------------------------------
    teacher_secret: str = "change-me"

    # --- submissions ---------------------------------------------------------
    max_upload_bytes: int = 50 * 1024 * 1024
    submission_min_interval_seconds: float = 5.0
    max_pending_submissions_per_participant: int = 1
    zip_max_files: int = 500
    zip_max_uncompressed_bytes: int = 200 * 1024 * 1024
    zip_max_compression_ratio: float = 200.0

    # --- live updates --------------------------------------------------------
    sse_poll_interval_seconds: float = 0.5
    sse_heartbeat_seconds: float = 15.0

    # --- worker --------------------------------------------------------------
    worker_poll_interval_seconds: float = 1.0
    worker_id: str = ""
    stale_job_seconds: int = 600

    # --- sandboxed runner ----------------------------------------------------
    runner_image: str = "dnnls-arena-runner:latest"
    runner_timeout_seconds: int = 30
    runner_cpus: float = 1.0
    runner_memory: str = "512m"
    runner_pids_limit: int = 64
    runner_tmp_size: str = "256m"
    runner_user: str = "1000:1000"
    runner_docker_binary: str = "docker"
    # How the worker makes job directories visible to the sandbox container.
    #   volume: data_dir is a named Docker volume -> mount sub-paths of that volume
    #   bind:   data_dir corresponds to runner_host_data_dir on the Docker host
    #   auto:   volume if runner_data_volume is set, else bind
    runner_mount_mode: str = "auto"
    runner_data_volume: str = ""
    # Where runner_data_volume is mounted inside the worker container (volume mode).
    runner_volume_mountpoint: str = "/data"
    runner_host_data_dir: str = ""

    @property
    def effective_worker_id(self) -> str:
        return self.worker_id or socket.gethostname()

    @property
    def submissions_dir(self) -> Path:
        return self.data_dir / "submissions"


@lru_cache
def get_settings() -> Settings:
    return Settings()
