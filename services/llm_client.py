from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

ROOT = Path(__file__).resolve().parent.parent
USAGE_DIR = Path(os.getenv('DEEPSEEK_USAGE_DIR', str(ROOT / 'data'))).expanduser()
USAGE_FILE = USAGE_DIR / 'deepseek-daily-usage.json'
USAGE_EVENTS_FILE = USAGE_DIR / 'deepseek-usage-events.jsonl'

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


INPUT_PRICE_CNY_PER_1M = _env_float('DEEPSEEK_INPUT_PRICE_CNY_PER_1M', 2.0)
OUTPUT_PRICE_CNY_PER_1M = _env_float('DEEPSEEK_OUTPUT_PRICE_CNY_PER_1M', 8.0)


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


def _empty_usage_summary() -> dict[str, Any]:
    return {
        'requestCount': 0,
        'promptTokens': 0,
        'completionTokens': 0,
        'totalTokens': 0,
        'estimatedCostCny': 0.0,
    }


def _estimate_cost_cny(prompt_tokens: int, completion_tokens: int) -> float:
    cost = (prompt_tokens / 1_000_000) * INPUT_PRICE_CNY_PER_1M
    cost += (completion_tokens / 1_000_000) * OUTPUT_PRICE_CNY_PER_1M
    return round(cost, 6)


def _read_usage_summary(date_key: str) -> dict[str, Any]:
    summary = _empty_usage_summary()
    try:
        lines = USAGE_EVENTS_FILE.read_text(encoding='utf-8').splitlines()
    except Exception:
        return summary

    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if event.get('date') != date_key:
            continue
        usage = event.get('usage') if isinstance(event.get('usage'), dict) else {}
        prompt_tokens = int(usage.get('prompt_tokens') or 0)
        completion_tokens = int(usage.get('completion_tokens') or 0)
        total_tokens = int(usage.get('total_tokens') or prompt_tokens + completion_tokens)
        summary['requestCount'] += 1
        summary['promptTokens'] += prompt_tokens
        summary['completionTokens'] += completion_tokens
        summary['totalTokens'] += total_tokens
        summary['estimatedCostCny'] += float(event.get('estimatedCostCny') or 0)

    summary['estimatedCostCny'] = round(summary['estimatedCostCny'], 6)
    return summary


def _append_usage_event(event: dict[str, Any]) -> None:
    USAGE_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_EVENTS_FILE.open('a', encoding='utf-8') as file:
        file.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')


def _usage_from_response(data: dict[str, Any]) -> dict[str, int]:
    raw_usage = data.get('usage')
    if not isinstance(raw_usage, dict):
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    prompt_tokens = int(raw_usage.get('prompt_tokens') or 0)
    completion_tokens = int(raw_usage.get('completion_tokens') or 0)
    total_tokens = int(raw_usage.get('total_tokens') or prompt_tokens + completion_tokens)
    return {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
    }


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
        data = response.json()
        event = self.record_usage_event(data)
        try:
            self.refresh_daily_usage()
        except Exception:
            pass
        content = data['choices'][0]['message']['content']
        return {
            'provider': 'deepseek',
            'model': self.model,
            'content': content,
            'usage': event.get('usage'),
            'estimatedCostCny': event.get('estimatedCostCny'),
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
            return {**usage, **_read_usage_summary(today)}
        balance = self.balance()
        current = balance.get('balance')
        summary = _read_usage_summary(today)
        usage = {
            'date': today,
            'startBalanceCny': current,
            'currentBalanceCny': current,
            'usedCny': 0.0,
            'currency': balance.get('currency') or 'CNY',
            'startedAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat(),
            **summary,
        }
        _write_usage(usage)
        return usage

    def record_usage_event(self, response_data: dict[str, Any]) -> dict[str, Any]:
        usage = _usage_from_response(response_data)
        event = {
            'id': uuid4().hex,
            'date': _today_key(),
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'provider': 'deepseek',
            'model': response_data.get('model') or self.model,
            'usage': usage,
            'estimatedCostCny': _estimate_cost_cny(
                usage['prompt_tokens'],
                usage['completion_tokens'],
            ),
        }
        _append_usage_event(event)
        return event

    def refresh_daily_usage(self) -> dict[str, Any]:
        usage = self.ensure_daily_usage_start()
        balance = self.balance()
        current = balance.get('balance')
        start = usage.get('startBalanceCny')
        summary = _read_usage_summary(usage.get('date') or _today_key())
        used = None
        if isinstance(start, (int, float)) and isinstance(current, (int, float)):
            used = max(0.0, round(float(start) - float(current), 6))
        usage = {
            **usage,
            'currentBalanceCny': current,
            'usedCny': used,
            'currency': balance.get('currency') or usage.get('currency') or 'CNY',
            'updatedAt': datetime.now(timezone.utc).isoformat(),
            **summary,
        }
        _write_usage(usage)
        return usage

    def daily_usage(self) -> dict[str, Any]:
        usage = _read_usage()
        today = _today_key()
        summary = _read_usage_summary(today)
        if usage.get('date') == today:
            used = usage.get('usedCny')
            return {
                **usage,
                **summary,
                'dailyLimitCny': self.daily_budget_cny,
                'limited': isinstance(used, (int, float)) and self.daily_budget_cny > 0 and used >= self.daily_budget_cny,
            }
        return {
            'date': today,
            'startBalanceCny': None,
            'currentBalanceCny': None,
            'usedCny': 0.0,
            'currency': 'CNY',
            **summary,
            'dailyLimitCny': self.daily_budget_cny,
            'limited': False,
        }
