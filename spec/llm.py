#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat client for the spec drafter. Stdlib only.

The ONLY place RealEngine talks to a model. It drafts a SCENE_SPEC.md from a
brief; everything downstream of that file is code, so a build is reproducible
from the spec alone with no network.

Configuration (a LiteLLM proxy, or anything OpenAI-compatible):

    REALENGINE_LLM_BASE_URL   base URL, else LITELLM_BASE_URL   (required)
    REALENGINE_LLM_API_KEY    API key,  else LITELLM_MASTER_KEY (required)
    REALENGINE_LLM_MODEL      model id, default claude-sonnet-5

The proxy address is never hardcoded -- it lives on a private network and
must come from the environment (Doppler:
``doppler run --project unfoundbox --config dev_personal -- ...``).
Missing base URL or key is a fail-closed error naming what is absent; there
is no silent cloud fallback and no default endpoint.

Test hook: ``REALENGINE_LLM_STUB=<path>`` returns that file's contents
instead of calling anything. Receipts then carry ``source: "stub"`` so a
stubbed run can never be mistaken for a model's answer.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_MODEL = "claude-sonnet-5"
CHEAP_MODEL = "gemini-3.7-flash"


class LLMUnavailable(RuntimeError):
    """Raised when the drafter cannot run. Always names the missing piece."""


def resolve_config(env=None):
    """Return {base_url, api_key, model} or raise LLMUnavailable."""
    env = os.environ if env is None else env
    base = (env.get("REALENGINE_LLM_BASE_URL") or env.get("LITELLM_BASE_URL") or "").strip()
    key = (env.get("REALENGINE_LLM_API_KEY") or env.get("LITELLM_MASTER_KEY") or "").strip()
    model = (env.get("REALENGINE_LLM_MODEL") or DEFAULT_MODEL).strip()
    missing = []
    if not base:
        missing.append("REALENGINE_LLM_BASE_URL (or LITELLM_BASE_URL)")
    if not key:
        missing.append("REALENGINE_LLM_API_KEY (or LITELLM_MASTER_KEY)")
    if missing:
        raise LLMUnavailable(
            "spec drafter unavailable: %s not set. Run under "
            "`doppler run --project unfoundbox --config dev_personal --`, and "
            "point the base URL at the LiteLLM proxy. No endpoint is assumed."
            % " and ".join(missing))
    return {"base_url": base.rstrip("/"), "api_key": key, "model": model}


def stub_path(env=None):
    env = os.environ if env is None else env
    return env.get("REALENGINE_LLM_STUB") or None


def chat(messages, env=None, timeout=180, max_tokens=8000, temperature=0.0):
    """One chat completion. Returns (text, meta). Never logs the key."""
    env = os.environ if env is None else env

    stub = stub_path(env)
    if stub:
        with open(stub, encoding="utf-8") as f:
            return f.read(), {"source": "stub", "model": "stub:%s" % stub,
                              "stub_path": stub}

    cfg = resolve_config(env)
    payload = json.dumps({
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + cfg["api_key"]},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise LLMUnavailable("LLM HTTP %s from the proxy: %s" % (e.code, detail)) from e
    except urllib.error.URLError as e:
        raise LLMUnavailable(
            "cannot reach the LLM proxy (%s). It is on a private network: is "
            "the base URL right and the machine on it?" % e.reason) from e
    except (ValueError, OSError) as e:
        raise LLMUnavailable("LLM call failed: %s" % e) from e

    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMUnavailable("LLM response had no message content") from e
    usage = body.get("usage") or {}
    return text, {
        "source": "llm",
        "model": body.get("model") or cfg["model"],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }
