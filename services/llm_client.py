from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
        self.base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat').strip()
        self.timeout_seconds = int(os.getenv('LLM_TIMEOUT_SECONDS', '60'))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError('deepseek_not_configured')

        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'temperature': temperature,
                'stream': False,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        return {
            'provider': 'deepseek',
            'model': self.model,
            'content': content,
            'raw': data,
        }
