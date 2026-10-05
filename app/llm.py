"""One interface to the language models.

  azure  : Azure OpenAI (the product), through the OpenAI-compatible v1 endpoint; model = deployment name
  github : GitHub Models (free, rate-limited), used to try models before paying
  ollama : local Gemma via Ollama (offline fallback; adapted from prep/step3_model_check/run_check.ask)

ask(prompt, schema, role) -> (answer dict, stats). Strict JSON schema output; stats carry latency, tokens and cost.
GPT-5.x models take no temperature: runs are made repeatable by a fixed reasoning effort and reported as mean/range.
"""
import copy
import json
import time

import requests

from . import config as C

_clients = {}


def strict(schema):
    """Strict structured output needs additionalProperties=false and every property required, at every level."""
    s = copy.deepcopy(schema)

    def fix(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for v in node.values():
                fix(v)
        elif isinstance(node, list):
            for v in node:
                fix(v)
    fix(s)
    return s


def client(provider):
    if provider not in _clients:
        from openai import OpenAI
        if provider == "azure":
            _clients[provider] = OpenAI(base_url=f"{C.AZURE_OPENAI_ENDPOINT}/openai/v1/", api_key=C.AZURE_OPENAI_API_KEY,
                                        max_retries=3, timeout=180)
        elif provider == "github":
            _clients[provider] = OpenAI(base_url="https://models.github.ai/inference", api_key=C.GITHUB_MODELS_TOKEN,
                                        max_retries=2, timeout=180)
    return _clients[provider]


def model_for(role, provider):
    m = {"answer": C.MODEL_ANSWER, "judge": C.MODEL_JUDGE, "fallback": C.MODEL_ANSWER_FALLBACK}[role]
    if provider == "github" and "/" not in m:
        m = "openai/" + m
    return m


def cost(model, tin, tout):
    p = C.PRICES.get(model) or C.PRICES.get(model.split("/")[-1])
    return None if not p else round((tin or 0) * p[0] / 1e6 + (tout or 0) * p[1] / 1e6, 6)


def _openai_ask(provider, model, system, user, schema, effort, max_out):
    kw = dict(model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
              response_format={"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": strict(schema)}},
              max_completion_tokens=max_out)
    if effort:
        kw["reasoning_effort"] = effort
    t = time.time()
    try:
        r = client(provider).chat.completions.create(**kw)
    except Exception as e:  # some endpoints reject reasoning_effort for some models: retry once without it
        if effort and "reasoning_effort" in str(e):
            kw.pop("reasoning_effort")
            r = client(provider).chat.completions.create(**kw)
        else:
            raise
    txt = r.choices[0].message.content or ""
    try:
        ans = json.loads(txt)
    except json.JSONDecodeError:
        ans = {"_unparsed": txt, "_finish": r.choices[0].finish_reason}
    u = r.usage
    reasoning = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", None) if u else None
    tin, tout = (u.prompt_tokens, u.completion_tokens) if u else (None, None)
    return ans, {"provider": provider, "model": model, "effort": effort, "latency_s": round(time.time() - t, 2),
                 "input_tokens": tin, "output_tokens": tout, "reasoning_tokens": reasoning, "cost_usd": cost(model, tin, tout)}


def _ollama_ask(system, user, schema):
    body = {"model": C.OLLAMA_MODEL, "system": system, "prompt": user, "stream": False, "think": False, "format": strict(schema),
            "options": {"temperature": 0, "num_ctx": 12288, "seed": 1}}
    t = time.time()
    d = requests.post(f"{C.OLLAMA_URL}/api/generate", json=body, timeout=900).json()
    try:
        ans = json.loads(d.get("response", ""))
    except json.JSONDecodeError:
        ans = {"_unparsed": d.get("response", "")}
    return ans, {"provider": "ollama", "model": C.OLLAMA_MODEL, "effort": None, "latency_s": round(time.time() - t, 2),
                 "input_tokens": d.get("prompt_eval_count"), "output_tokens": d.get("eval_count"), "reasoning_tokens": None,
                 "cost_usd": 0.0}


def ask(system, user, schema, role="answer", provider=None, model=None, effort=None, max_out=16000):
    """Returns (answer dict, stats). Falls back to the second deployment if the first fails (azure only)."""
    provider = provider or C.LLM_PROVIDER
    if provider == "ollama":
        return _ollama_ask(system, user, schema)
    model = model or model_for(role, provider)
    effort = effort if effort is not None else (C.EFFORT_JUDGE if role == "judge" else C.EFFORT_ANSWER)
    try:
        return _openai_ask(provider, model, system, user, schema, effort or None, max_out)
    except Exception:
        if provider == "azure" and role == "answer" and C.MODEL_ANSWER_FALLBACK:
            ans, st = _openai_ask(provider, C.MODEL_ANSWER_FALLBACK, system, user, schema, effort or None, max_out)
            st["fallback"] = True
            return ans, st
        raise
