from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / 'output'
RUNTIME_DIR = ROOT / 'mock' / 'runtime'
JOB_STATUS_FILE = RUNTIME_DIR / 'competitive-analysis-job.json'
LATEST_SUCCESS_FILE = RUNTIME_DIR / 'competitive-analysis-latest-success.json'
LATEST_FAILURE_FILE = RUNTIME_DIR / 'competitive-analysis-latest-failure.json'


def now_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz=tz).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def is_report_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(path.glob('*.md')) and ((path / 'raw_data.json').exists() or (path / 'checkpoint.json').exists())


def report_dirs() -> list[Path]:
    if not OUTPUT_ROOT.exists():
        return []
    return sorted([p for p in OUTPUT_ROOT.iterdir() if is_report_dir(p)], key=lambda p: p.stat().st_mtime, reverse=True)


def latest_report_info() -> dict[str, Any] | None:
    dirs = report_dirs()
    if not dirs:
        return None
    folder = dirs[0]
    md_candidates = sorted(folder.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
    md_file = md_candidates[0] if md_candidates else None
    return {
        'id': folder.name,
        'folder': folder.name,
        'reportFile': str(md_file) if md_file else None,
        'rawDataFile': str(folder / 'raw_data.json'),
        'updatedAt': now_iso(),
    }


def main() -> int:
    from main import main as competitive_main

    job = load_json(JOB_STATUS_FILE)
    started_at = now_iso()
    pid = os.getpid()
    job.update({
        'status': 'running',
        'startedAt': job.get('startedAt') or started_at,
        'runnerStartedAt': started_at,
        'pid': pid,
        'updatedAt': started_at,
        'message': '竞情分析后台生成中...',
    })
    write_json(JOB_STATUS_FILE, job)

    before = latest_report_info()
    try:
        competitive_main()
        after = latest_report_info()
        finished = now_iso()
        success_payload = {
            'status': 'success',
            'finishedAt': finished,
            'updatedAt': finished,
            'message': '竞情分析生成完成。',
            'pid': pid,
            'previousLatest': before,
            'latestReport': after,
        }
        write_json(JOB_STATUS_FILE, {**job, **success_payload})
        write_json(LATEST_SUCCESS_FILE, success_payload)
        return 0
    except Exception as exc:
        finished = now_iso()
        detail = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:]
        fail_payload = {
            'status': 'failed',
            'finishedAt': finished,
            'updatedAt': finished,
            'message': '竞情分析生成失败。',
            'pid': pid,
            'error': str(exc),
            'traceback': detail,
            'previousLatest': before,
        }
        write_json(JOB_STATUS_FILE, {**job, **fail_payload})
        write_json(LATEST_FAILURE_FILE, fail_payload)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
