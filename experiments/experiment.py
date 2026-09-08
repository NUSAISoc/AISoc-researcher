"""Experiment definitions and the registry that selects one by name.

An experiment is a callable that, given a configuration and a sandbox, produces
an iterable of record dicts. Records are the raw per-unit output of a run; they
are written to the run log verbatim. The synthetic experiment shipped here is
deterministic and offline: the same seed produces the same records, so a
synthetic run is reproducible and clearly marked ``synthetic: true``.

To add your own experiment, write a function with the same signature, decorate
it with ``@register("your-name")``, and select it with ``EXPERIMENT_NAME``.
Replace the synthetic example with the protocol from
``docs/05-experiment-design.md``. A live experiment must respect the fail-closed
configuration in ``config.py`` and must record real outcomes only, never
invented ones. Timeouts, refusals, and errors are recorded as results.
"""
from __future__ import annotations

import hashlib
from typing import Callable, Dict, Iterator, List, Mapping

from .config import ExperimentConfig
from .workspace import Sandbox

Experiment = Callable[[ExperimentConfig, Sandbox], List[Mapping[str, object]]]

_REGISTRY: Dict[str, Experiment] = {}


def register(name: str) -> Callable[[Experiment], Experiment]:
    def decorator(func: Experiment) -> Experiment:
        if name in _REGISTRY:
            raise ValueError(f"experiment already registered: {name}")
        _REGISTRY[name] = func
        return func
    return decorator


def get_experiment(name: str) -> Experiment:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise KeyError(f"unknown experiment {name!r}; registered: {known}") from exc


def registered_names() -> List[str]:
    return sorted(_REGISTRY)


def _deterministic_value(seed: int, index: int) -> float:
    """A deterministic pseudo-value in [0, 1) from seed and index.

    This is a synthetic placeholder measurement, not experimental data. It is a
    hash of the inputs so a run is reproducible and obviously synthetic. Real
    experiments must return real observations.
    """
    digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


@register("example-synthetic")
def example_synthetic(config: ExperimentConfig, sandbox: Sandbox) -> List[Mapping[str, object]]:
    """A deterministic, offline synthetic experiment.

    It writes a small artifact into the sandbox (to exercise the containment
    boundary) and returns one record per unit. Every record is marked synthetic
    so it can never be mistaken for real data.
    """
    sandbox.write_text("run.txt", f"synthetic run for {config.name}, seed={config.seed}\n")
    records: List[Mapping[str, object]] = []
    for index in range(config.num_records):
        condition = "treatment" if index % 2 == 0 else "control"
        records.append(
            {
                "unit_index": index,
                "condition": condition,
                "synthetic_value": round(_deterministic_value(config.seed, index), 6),
                "synthetic": True,
                "status": "ok",
            }
        )
    return records
