"""Registers built-in adapters/evaluators/visualizations and discovers challenge packages."""

from __future__ import annotations

import importlib
import logging
import pkgutil

from app.core import registries

log = logging.getLogger(__name__)
_loaded = False


def load_builtin(force: bool = False) -> None:
    global _loaded
    if _loaded and not force:
        return

    from app.evaluators import register_all as register_evaluators
    from app.submissions import register_all as register_adapters
    from app.visualizations import register_all as register_visualizations

    register_adapters(registries.adapters)
    register_evaluators(registries.evaluators)
    register_visualizations(registries.visualizations)
    discover_challenges()
    _loaded = True


def discover_challenges(package: str = "app.challenges") -> list[str]:
    """Import every sub-package of ``app.challenges`` exposing a ``CHALLENGE`` object."""
    pkg = importlib.import_module(package)
    found: list[str] = []
    for mod in pkgutil.iter_modules(pkg.__path__):
        module = importlib.import_module(f"{package}.{mod.name}")
        challenge = getattr(module, "CHALLENGE", None)
        if challenge is None:
            continue
        registries.register_challenge(challenge, replace=True)
        found.append(challenge.id)
    log.info("challenges registered: %s", ", ".join(found) or "(none)")
    return found
