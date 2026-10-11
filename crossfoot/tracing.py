"""neatlogs setup and span helpers. Everything here is a no-op when NEATLOGS_API_KEY is absent."""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import os
import re

try:
    import neatlogs
except ImportError:  # the package is a dependency, but a broken install must not stop a run
    neatlogs = None

_on = False


_IMAGE = re.compile(r"data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=]+")


def _image_ref(m: re.Match) -> str:
    raw = base64.b64decode(m.group(0).split(",", 1)[1] + "===")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as im:
            size = f"{im.width}x{im.height}"
    except Exception:
        size = "?x?"
    return f"image {size} sha256:{hashlib.sha256(raw).hexdigest()[:12]}"


def mask_images(obj):
    """neatlogs mask: replace every data:image base64 string anywhere in a span with a short reference."""
    if isinstance(obj, str):
        return _IMAGE.sub(_image_ref, obj)
    if isinstance(obj, dict):
        return {k: mask_images(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [mask_images(v) for v in obj]
    return obj


def init() -> str:
    """Start tracing if the key is present. Returns the line to print first when it is not."""
    global _on
    if neatlogs is None or not os.environ.get("NEATLOGS_API_KEY"):
        _on = False
        return "NEATLOGS_API_KEY is not set: running untraced."
    neatlogs.init(api_key=os.environ["NEATLOGS_API_KEY"], workflow_name="crossfoot", mask=mask_images)
    _on = True
    return ""


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
