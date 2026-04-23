from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


class JinaReaderClient:
    def __init__(self) -> None:
        self.api_key = os.getenv('JINA_API_KEY', '').strip()
        self.timeout_seconds = int(os.getenv('JINA_TIMEOUT_SECONDS', '30'))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def read_url(self, url: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError('jina_not_configured')
        response = requests.get(
            f'https://r.jina.ai/http://{url.removeprefix("https://").removeprefix("http://")}',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'text/plain',
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return {'url': url, 'content': response.text[:12000]}
