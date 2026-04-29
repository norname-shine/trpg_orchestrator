# -*- coding: gbk -*-
from __future__ import annotations

import os
import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .env_loader import load_project_env


class DeepSeekClient:
    def __init__(self) -> None:
        load_project_env()
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用 DeepSeek V4。")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek API 调用失败: HTTP {exc.code} {detail}") from exc
        return data["choices"][0]["message"]["content"]
