from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

ROOT = Path(__file__).resolve().parent.parent
USAGE_FILE = ROOT / 'data' / 'deepseek-daily-usage.json'


def _today_key() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')


def _read_usage() -> dict[str, Any]:
    try:
        return json.loads(USAGE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_usage(data: dict[str, Any]) -> None:
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '').strip()
        self.base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat').strip()
        self.timeout_seconds = int(os.getenv('LLM_TIMEOUT_SECONDS', '60'))
        try:
            self.daily_budget_cny = float(os.getenv('DEEPSEEK_DAILY_BUDGET_CNY', '5') or '5')
        except ValueError:
            self.daily_budget_cny = 5.0

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError('deepseek_not_configured')

        usage = self.refresh_daily_usage()
        used = usage.get('usedCny')
        if isinstance(used, (int, float)) and self.daily_budget_cny > 0 and used >= self.daily_budget_cny:
            raise RuntimeError('deepseek_daily_budget_exceeded')
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
        self.refresh_daily_usage()
        data = response.json()
        content = data['choices'][0]['message']['content']
        return {
            'provider': 'deepseek',
            'model': self.model,
            'content': content,
            'raw': data,
        }

    def balance(self) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError('deepseek_not_configured')
        response = requests.get(
            f'{self.base_url}/user/balance',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            timeout=min(self.timeout_seconds, 10),
        )
        response.raise_for_status()
        data = response.json()
        balance = None
        currency = 'CNY'
        if 'total_balance' in data:
            balance = float(data.get('total_balance') or 0)
            currency = data.get('currency') or currency
        elif isinstance(data.get('balance_infos'), list) and data['balance_infos']:
            total = 0.0
            for item in data['balance_infos']:
                try:
                    total += float(item.get('total_balance') or 0)
                except (TypeError, ValueError):
                    continue
                currency = item.get('currency') or currency
            balance = total
        return {
            'ok': True,
            'balance': balance,
            'currency': currency,
            'raw': data,
        }

    def ensure_daily_usage_start(self) -> dict[str, Any]:
        usage = _read_usage()
        today = _today_key()
        if usage.get('date') == today and isinstance(usage.get('startBalanceCny'), (int, float)):
            return usage
        balance = self.balance()
        current = balance.get('balance')
        usage = {
            'date': today,
            'startBalanceCny': current,
            'currentBalanceCny': current,
            'usedCny': 0.0,
            'currency': balance.get('currency') or 'CNY',
            'startedAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat(),
        }
        _write_usage(usage)
        return usage

    def refresh_daily_usage(self) -> dict[str, Any]:
        usage = self.ensure_daily_usage_start()
        balance = self.balance()
        current = balance.get('balance')
        start = usage.get('startBalanceCny')
        used = None
        if isinstance(start, (int, float)) and isinstance(current, (int, float)):
            used = max(0.0, round(float(start) - float(current), 6))
        usage = {
            **usage,
            'currentBalanceCny': current,
            'usedCny': used,
            'currency': balance.get('currency') or usage.get('currency') or 'CNY',
            'updatedAt': datetime.now(timezone.utc).isoformat(),
        }
        _write_usage(usage)
        return usage

    def daily_usage(self) -> dict[str, Any]:
        usage = _read_usage()
        today = _today_key()
        if usage.get('date') == today:
            used = usage.get('usedCny')
            return {
                **usage,
                'dailyLimitCny': self.daily_budget_cny,
                'limited': isinstance(used, (int, float)) and self.daily_budget_cny > 0 and used >= self.daily_budget_cny,
            }
        return {
            'date': today,
            'startBalanceCny': None,
            'currentBalanceCny': None,
            'usedCny': 0.0,
            'currency': 'CNY',
            'dailyLimitCny': self.daily_budget_cny,
            'limited': False,
        }
