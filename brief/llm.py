"""LunaClaw Brief — LLM Client

Auto-detects OpenClaw environment (OPENCLAW_API_KEY / OPENCLAW_BASE_URL)
and uses its built-in LLM proxy when available. Falls back to user-configured
third-party LLM (config.local.yaml / env vars).

Provides:
  - chat()     : Multi-turn conversation API
  - classify() : Lightweight single-turn classification (low temperature)
  - stream()   : Streaming chat completions (yields chunks)
"""

import json
import os
import requests


class LLMUsage:
    """Accumulated token usage and cost tracking across all LLM calls."""

    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.call_count = 0

    def record(self, usage: dict):
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_completion_tokens += usage.get("completion_tokens", 0)
        self.call_count += 1

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """Rough estimate based on GPT-4o-mini pricing ($0.15/1M in, $0.60/1M out)."""
        return (self.total_prompt_tokens * 0.15 + self.total_completion_tokens * 0.60) / 1_000_000

    def summary(self) -> dict:
        return {
            "calls": self.call_count,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }


class LLMClient:
    """Universal LLM client with OpenClaw auto-detection (OpenAI-compatible API)."""

    def __init__(self, llm_config: dict):
        oc_key = os.getenv("OPENCLAW_API_KEY") or os.getenv("OPENCLAW_TOKEN")
        oc_url = os.getenv("OPENCLAW_BASE_URL") or os.getenv("OPENCLAW_LLM_URL")

        if oc_key and oc_url:
            self.api_key = oc_key
            self.base_url = oc_url.rstrip("/")
            self.model = os.getenv("OPENCLAW_MODEL", llm_config.get("model", "gpt-4o-mini"))
            self._provider = "openclaw"
        else:
            self.api_key = llm_config.get("api_key") or os.getenv("BAILIAN_API_KEY", "")
            self.base_url = (
                llm_config.get("base_url")
                or os.getenv("BAILIAN_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
            )
            self.model = llm_config.get("model") or os.getenv("BAILIAN_MODEL", "kimi-k2.5")
            self._provider = "custom"

        self.timeout = llm_config.get("timeout", 180)
        self.usage = LLMUsage()

        if not self.api_key:
            raise ValueError(
                "LLM API Key not configured. Set OPENCLAW_API_KEY (OpenClaw) "
                "or BAILIAN_API_KEY env var, or specify in config.local.yaml."
            )

    @property
    def provider(self) -> str:
        return self._provider

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8000,
    ) -> str:
        """Standard multi-turn chat completion."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if "usage" in data:
                    self.usage.record(data["usage"])
                return data["choices"][0]["message"]["content"]
            print(f"[LLM] API error: {resp.status_code} - {resp.text[:200]}")
            return ""
        except Exception as e:
            print(f"[LLM] Request failed: {type(e).__name__}: {e}")
            return ""

    def classify(self, system: str, user: str) -> str:
        """Lightweight single-turn classification call (low temp, small max_tokens)."""
        return self.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=256,
        )

    def stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8000,
    ):
        """Streaming chat completion. Yields content chunks as they arrive."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            resp = requests.post(
                url, headers=headers, json=payload,
                timeout=self.timeout, stream=True,
            )
            if resp.status_code != 200:
                print(f"[LLM] Stream error: {resp.status_code}")
                return

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
        except Exception as e:
            print(f"[LLM] Stream failed: {type(e).__name__}: {e}")
