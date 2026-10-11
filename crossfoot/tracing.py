"""neatlogs setup and span helpers. Everything here is a no-op when NEATLOGS_API_KEY is absent."""
from __future__ import annotations

import contextlib
import os

try:
    import neatlogs
except ImportError:  # the package is a dependency, but a broken install must not stop a run
    neatlogs = None

_on = False


def init() -> str:
    """Start tracing if the key is present. Returns the line to print first when it is not."""
    global _on
    if neatlogs is None or not os.environ.get("NEATLOGS_API_KEY"):
        _on = False
        return "NEATLOGS_API_KEY is not set: running untraced."
    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name="crossfoot")
    _on = True
    return ""


def enabled() -> bool:
    return _on


def wrap(client):
    return neatlogs.wrap(client) if _on else client


def span(kind: str, name: str | None = None, **kw):
    """Decorator: a span of the given kind (WORKFLOW, AGENT, TOOL); identity when untraced."""
    def deco(fn):
        return neatlogs.span(kind=kind, name=name or fn.__name__, **kw)(fn) if _on else fn
    return deco


@contextlib.contextmanager
def trace(name: str, kind: str = "TOOL", **attrs):
    """Context manager yielding an object with set_attribute(k, v); tags are plain strings or numbers."""
    if not _on:
        yield _NoSpan()
        return
    with neatlogs.trace(name, kind=kind) as sp:
        for k, v in attrs.items():
            if v is not None:
                sp.set_attribute(k, v)
        yield sp


class _NoSpan:
    def set_attribute(self, key, value):
        pass


def shutdown():
    if _on:
        neatlogs.flush()
        neatlogs.shutdown()
