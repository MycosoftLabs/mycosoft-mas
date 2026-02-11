"""
Prometheus metric helpers (safe under repeated imports).

Pytest runs in this repo use `--import-mode=importlib`, and some modules are
imported multiple times under different module names/paths. The default
Prometheus REGISTRY will raise:

  ValueError: Duplicated timeseries in CollectorRegistry

when a module-level metric is registered more than once.

These helpers return an existing collector if it is already registered.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from prometheus_client import Counter, Gauge, Histogram, Summary, REGISTRY


def _get_existing(name: str) -> Optional[Any]:
    # prometheus_client internal; used defensively for test stability.
    return getattr(REGISTRY, "_names_to_collectors", {}).get(name)


def get_counter(name: str, documentation: str, labelnames: Iterable[str] = (), **kwargs: Any) -> Counter:
    existing = _get_existing(name)
    if existing is not None:
        return existing
    return Counter(name, documentation, labelnames=labelnames, **kwargs)


def get_gauge(name: str, documentation: str, labelnames: Iterable[str] = (), **kwargs: Any) -> Gauge:
    existing = _get_existing(name)
    if existing is not None:
        return existing
    return Gauge(name, documentation, labelnames=labelnames, **kwargs)


def get_histogram(
    name: str,
    documentation: str,
    labelnames: Iterable[str] = (),
    **kwargs: Any,
) -> Histogram:
    existing = _get_existing(name)
    if existing is not None:
        return existing
    return Histogram(name, documentation, labelnames=labelnames, **kwargs)


def get_summary(name: str, documentation: str, labelnames: Iterable[str] = (), **kwargs: Any) -> Summary:
    existing = _get_existing(name)
    if existing is not None:
        return existing
    return Summary(name, documentation, labelnames=labelnames, **kwargs)

