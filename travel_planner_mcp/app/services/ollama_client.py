from __future__ import annotations

import json

import httpx

from app.utils.config import Settings


class OllamaClient:
    """Small wrapper around the local Ollama HTTP API."""

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def generate_text(self, prompt: str, system_prompt: str = "You are a helpful travel planning assistant.") -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "system": system_prompt,
            "prompt": prompt,
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
        except (httpx.HTTPError, json.JSONDecodeError):
            return ""
