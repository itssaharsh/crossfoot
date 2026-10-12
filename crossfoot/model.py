"""Gateway client: images in, strict JSON out. Cost meter, budget guard, rate limit, one repair, one retry."""
from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "claude-haiku"
DEFAULT_BUDGET = 2.00          # dollars per run

# ESTIMATE ONLY: dollars per million tokens (input, output), from the gateway's own list (its /model/info, read on
# 11 October 2026). Not the gateway's bill; the figure `crossfoot budget` prints is the one to trust. Unknown models
# are priced like the dearest row.
PRICE_PER_MTOK = {
    "claude-haiku": (1.10, 5.50),
    "claude-sonnet-4.6": (3.30, 16.50),
    "claude-opus-4.6": (5.50, 27.50),
}
FIRST_CALL_ESTIMATE = 0.01     # what the guard assumes a call costs before it has seen one


class BudgetExceeded(Exception):
    pass


def price(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pin, pout = PRICE_PER_MTOK.get(model) or max(PRICE_PER_MTOK.values())
    return (prompt_tokens * pin + completion_tokens * pout) / 1e6


_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)\s*```", re.S)


def parse_json(text: str):
    """Parse a model answer as JSON. Tolerates a code fence (around the answer or inside prose) and prose before or
    after the JSON object; the first object or list that parses wins. Raises ValueError."""
    t = (text or "").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        first = e
    dec = json.JSONDecoder()
    for src in [m.group(1) for m in _FENCE.finditer(t)] + [t]:
        for m in re.finditer(r"[{\[]", src):
            try:
                obj, _ = dec.raw_decode(src[m.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, (dict, list)):
                return obj
    raise ValueError(f"answer is not valid JSON: {first}") from None


def root_url(base: str) -> str:
    base = base.rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def gateway_spend() -> tuple[float, float | None]:
    """(spend, max_budget) for the key, from the gateway. Reads the key from the environment; never prints it."""
    req = urllib.request.Request(root_url(os.environ["LITELLM_BASE_URL"]) + "/key/info",
                                 headers={"Authorization": "Bearer " + os.environ["LITELLM_API_KEY"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        info = json.load(r)["info"]
    return float(info.get("spend") or 0), (None if info.get("max_budget") is None else float(info["max_budget"]))


def data_url(image) -> str:
    raw = Path(image).read_bytes() if isinstance(image, (str, Path)) else image
    return "data:image/png;base64," + base64.b64encode(raw).decode()


class Gateway:
    def __init__(self, client=None, *, model=DEFAULT_MODEL, budget=DEFAULT_BUDGET, min_interval=1.1,
                 sleep=time.sleep, retry_wait=5.0, timeout=120):
        if client is None:
            from openai import OpenAI
            from . import tracing
            client = tracing.wrap(OpenAI(base_url=os.environ["LITELLM_BASE_URL"],
                                         api_key=os.environ["LITELLM_API_KEY"], timeout=timeout))
        self.client, self.model, self.budget = client, model, budget
        self.min_interval, self.sleep, self.retry_wait = min_interval, sleep, retry_wait
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        self.cost = 0.0
        self._last = 0.0
        self._meter = threading.Lock()      # reads overlap (three calls in flight); the counters must not race

    def _guard(self):
        est = self.cost / self.calls if self.calls else FIRST_CALL_ESTIMATE
        if self.cost + est > self.budget:
            raise BudgetExceeded(f"run budget ${self.budget:.2f} reached (estimated spend ${self.cost:.4f} after "
                                 f"{self.calls} calls); refusing the next call")

    def _call(self, messages, model):
        self._guard()
        from openai import APIConnectionError, APITimeoutError, RateLimitError
        for attempt in (0, 1):
            with self._meter:           # each call reserves the next start slot, so threads cannot beat the spacing
                start = max(time.monotonic(), self._last + self.min_interval)
                wait, self._last = start - time.monotonic(), start
            if wait > 0:
                self.sleep(wait)
            try:
                r = self.client.chat.completions.create(model=model, messages=messages, temperature=0)
                break
            except (RateLimitError, APITimeoutError, APIConnectionError):
                if attempt:
                    raise
                self.sleep(self.retry_wait)
        u = r.usage
        with self._meter:
            self.calls += 1
            self.prompt_tokens += u.prompt_tokens
            self.completion_tokens += u.completion_tokens
            self.cost += price(model, u.prompt_tokens, u.completion_tokens)
        return r.choices[0].message.content or ""

    def ask_json(self, prompt: str, image=None, *, validate=None, model=None):
        """Ask for JSON. A bad answer (not JSON, or `validate` raises ValueError) gets one repair request."""
        model = model or self.model
        content = [{"type": "text", "text": prompt}]
        if image is not None:
            content.append({"type": "image_url", "image_url": {"url": data_url(image)}})
        messages = [{"role": "user", "content": content}]
        text = self._call(messages, model)
        for repaired in (False, True):
            try:
                data = parse_json(text)
                if validate:
                    validate(data)
                return data
            except ValueError as e:
                if repaired:
                    raise
                messages = messages + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": f"That answer was rejected: {e}. Answer again with only the "
                                                "corrected JSON, nothing else."}]
                text = self._call(messages, model)
