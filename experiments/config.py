"""Experiment configuration, driven entirely by environment variables.

All experiment parameters are configurable from the environment so a run is
reproducible from its recorded configuration alone. The defaults describe a
deterministic, offline synthetic run that needs no credentials and no network.

Environment variables
----------------------
EXPERIMENT_RUN_MODE   ``synthetic`` (default) or ``live``.
EXPERIMENT_NAME       Registered experiment to run. Default ``example-synthetic``.
EXPERIMENT_SEED       Integer seed for deterministic synthetic runs. Default ``0``.
EXPERIMENT_NUM_RECORDS Number of records the synthetic experiment emits. Default ``8``.
EXPERIMENT_AUTH       Path (repo-relative) to a dated authorization doc. Required for live.
EXPERIMENT_CREDENTIAL Name of the credential/env-var expected for a live run. Required for live.
EXPERIMENT_NOTES      Free-text note recorded in the ledger row.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
WORKSPACES_DIR = Path(__file__).resolve().parent / "workspaces"

SYNTHETIC = "synthetic"
LIVE = "live"
VALID_MODES = (SYNTHETIC, LIVE)


class ConfigError(ValueError):
    """Raised when the environment does not describe a runnable configuration."""


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str = SYNTHETIC
    name: str = "example-synthetic"
    seed: int = 0
    num_records: int = 8
    auth_ref: str = ""
    credential_name: str = ""
    notes: str = ""
    extra: Dict[str, str] = field(default_factory=dict)

    @property
    def synthetic(self) -> bool:
        return self.mode == SYNTHETIC

    def config_hash(self) -> str:
        """A stable hash of the configuration, recorded in the ledger."""
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def load_config(env: Dict[str, str] | None = None) -> ExperimentConfig:
    """Build the configuration from the environment and validate it.

    Live mode is fail-closed: it requires ``EXPERIMENT_AUTH`` to point at a file
    that exists in the repository and ``EXPERIMENT_CREDENTIAL`` to name a
    present, non-empty environment variable. If either is missing the run is
    refused; there is no silent fallback to synthetic.
    """
    env = dict(os.environ if env is None else env)
    mode = env.get("EXPERIMENT_RUN_MODE", SYNTHETIC).strip() or SYNTHETIC
    if mode not in VALID_MODES:
        raise ConfigError(f"EXPERIMENT_RUN_MODE must be one of {VALID_MODES}, got {mode!r}")

    cfg = ExperimentConfig(
        mode=mode,
        name=env.get("EXPERIMENT_NAME", "example-synthetic").strip() or "example-synthetic",
        seed=_env_int("EXPERIMENT_SEED", 0),
        num_records=_env_int("EXPERIMENT_NUM_RECORDS", 8),
        auth_ref=env.get("EXPERIMENT_AUTH", "").strip(),
        credential_name=env.get("EXPERIMENT_CREDENTIAL", "").strip(),
        notes=env.get("EXPERIMENT_NOTES", "").strip(),
    )

    if cfg.num_records < 1:
        raise ConfigError("EXPERIMENT_NUM_RECORDS must be at least 1")

    if cfg.mode == LIVE:
        _validate_live(cfg, env)
    return cfg


def _validate_live(cfg: ExperimentConfig, env: Dict[str, str]) -> None:
    if not cfg.auth_ref:
        raise ConfigError(
            "live mode requires EXPERIMENT_AUTH set to a dated authorization document; refusing to run"
        )
    auth_path = (REPO_ROOT / cfg.auth_ref).resolve()
    try:
        auth_path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ConfigError("EXPERIMENT_AUTH must be a path inside the repository") from exc
    if not auth_path.is_file():
        raise ConfigError(f"live authorization document not found: {cfg.auth_ref}")
    if not cfg.credential_name:
        raise ConfigError(
            "live mode requires EXPERIMENT_CREDENTIAL naming the credential env var; refusing to run"
        )
    if not env.get(cfg.credential_name):
        raise ConfigError(
            f"live credential {cfg.credential_name!r} is not set in the environment; refusing to run"
        )
