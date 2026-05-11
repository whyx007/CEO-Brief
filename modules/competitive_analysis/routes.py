from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any



from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

ROOT = Path(__file__).resolve().parent
PLATFORM_ROOT = ROOT.parents[1]
WORKSPACE_ROOT = PLATFORM_ROOT.parents[1]
OUTPUT_ROOT = ROOT / 'output'
MOCK_DIR = ROOT / 'mock'
RUNTIME_DIR = MOCK_DIR / 'runtime'
SETTINGS_FILE = MOCK_DIR / 'competitive-analysis-settings.json'
JOB_STATUS_FILE = RUNTIME_DIR / 'competitive-analysis-job.json'
LATEST_SUCCESS_FILE = RUNTIME_DIR / 'competitive-analysis-latest-success.json'
LATEST_FAILURE_FILE = RUNTIME_DIR / 'competitive-analysis-latest-failure.json'
REPORTS_TITLE_KEYWORD = '竞情战略周报'
COMPETITIVE_PYTHON = os.getenv('COMPETITIVE_ANALYSIS_PYTHON', r'D:\ProgramData\miniconda3\envs\tianta_ci\python.exe').strip()

load_dotenv(PLATFORM_ROOT / '.env')

router = APIRouter()


def now_iso() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz=tz).replace(microsecond=0).isoformat()


def _is_report_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(path.glob('*.md')) and ((path / 'raw_data.json').exists() or (path / 'checkpoint.json').exists())


def _report_dirs() -> list[Path]:
    if not OUTPUT_ROOT.exists():
        return []
    return sorted([p for p in OUTPUT_ROOT.iterdir() if _is_report_dir(p)], key=lambda p: p.name, reverse=True)


def _find_report_markdown(folder: Path) -> Path | None:
    candidates = list(folder.glob('*.md'))
    if not candidates:
        return None

    primary = []
    backups = []
    for p in candidates:
        lowered = p.name.lower()
        if 'backup' in lowered or 'onepager' in lowered or 'top20' in lowered or 'all_companies' in lowered:
            backups.append(p)
        else:
            primary.append(p)

    pool = primary or candidates
    preferred = [p for p in pool if REPORTS_TITLE_KEYWORD in p.name]
    if preferred:
        return sorted(preferred, key=lambda p: p.name, reverse=True)[0]
    return sorted(pool, key=lambda p: p.name, reverse=True)[0]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _extract_markdown_sections(markdown: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_title = '摘要'
    buffer: list[str] = []

    for line in markdown.splitlines():
        title_match = re.match(r'^(##+|###)\s+(.*)$', line.strip())
        if title_match:
            body = '\n'.join(buffer).strip()
            if body:
                sections.append({'title': current_title, 'content': body})
            current_title = title_match.group(2).strip()
            buffer = []
            continue
        buffer.append(line)

    tail = '\n'.join(buffer).strip()
    if tail:
        sections.append({'title': current_title, 'content': tail})
    return sections


def _first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        text = line.strip()
        if text.startswith('#'):
            return text.lstrip('#').strip()
    return '竞情分析报告'


def _derive_period(folder_name: str, markdown: str) -> str:
    m = re.search(r'（?(\d{4}\.\d{2}\.\d{2}\s*[~～-]\s*\d{4}\.\d{2}\.\d{2})）?', markdown)
    if m:
        return m.group(1)
    m = re.search(r'(\d{8})', folder_name)
    if not m:
        return folder_name
    s = m.group(1)
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}'


def _build_summary_cards(raw_data: dict[str, Any]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for key, title in [
        ('executive_summary', '执行摘要'),
        ('onepager_text', 'CEO 一页式摘要'),
        ('top15_text', 'TOP15 竞情总览'),
        ('satellite_backup_text', '测运控 TOP20 备份'),
        ('laser_backup_text', '激光通信备份'),
        ('summary_backup_text', '摘要备份'),
    ]:
        value = raw_data.get(key)
        if isinstance(value, str) and value.strip():
            cards.append({
                'key': key,
                'title': title,
                'summary': value.strip()[:3600],
            })
    return cards


def _task_settings() -> list[dict[str, str]]:
    return [
        {'key': 'discover', 'label': '目标发现与确认', 'source': 'tasks.py / task_discover'},
        {'key': 'talent', 'label': '人才团队情报', 'source': 'tasks.py / task_talent'},
        {'key': 'market', 'label': '市场客户情报', 'source': 'tasks.py / task_market'},
        {'key': 'tech', 'label': '技术方向情报', 'source': 'tasks.py / task_tech'},
        {'key': 'bidding_funding', 'label': '竞标与融资情报', 'source': 'tasks.py / task_bidding_funding'},
        {'key': 'policy', 'label': '政策情报', 'source': 'tasks.py / task_policy'},
        {'key': 'global_tech', 'label': '全球前沿技术', 'source': 'tasks.py / task_global_tech'},
        {'key': 'scoring', 'label': '评分与排序', 'source': 'tasks.py / task_scoring'},
        {'key': 'report', 'label': '报告生成', 'source': 'tasks.py / task_report'},
    ]


def _runtime_settings() -> dict[str, Any]:
    searxng_base = os.getenv('SEARXNG_BASE_URL', '').strip()
    return {
        'searchProvider': 'searxng',
        'searxngBaseUrl': searxng_base,
        'searxngVerifySsl': os.getenv('SEARXNG_VERIFY_SSL', 'false').strip().lower() in {'1', 'true', 'yes', 'on'},
        'searchFallbacksBlocked': ['bocha', 'serper', 'bing', 'serpapi'],
        'llmProvider': os.getenv('LLM_PROVIDER', 'deepseek').strip() or 'deepseek',
        'deepseekModel': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat').strip() or 'deepseek-chat',
        'qwenModel': os.getenv('QWEN_MODEL', 'qwen-plus').strip() or 'qwen-plus',
        'outputFormat': os.getenv('OUTPUT_FORMAT', 'both').strip() or 'both',
        'pythonExecutable': COMPETITIVE_PYTHON,
    }


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _read_job_status() -> dict[str, Any]:
    data = _load_json(JOB_STATUS_FILE)
    if not data:
        return {
            'status': 'idle',
            'message': '当前无运行中的竞情生成任务。',
            'updatedAt': now_iso(),
        }
    return data


def _latest_success_info() -> dict[str, Any]:
    return _load_json(LATEST_SUCCESS_FILE)


def _latest_failure_info() -> dict[str, Any]:
    return _load_json(LATEST_FAILURE_FILE)


def _is_job_running() -> bool:
    job = _read_job_status()
    if job.get('status') != 'running':
        return False
    pid = job.get('pid')
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _ensure_settings_file() -> dict[str, Any]:
    if SETTINGS_FILE.exists():
        data = _load_json(SETTINGS_FILE)
        if data:
            return data

    config = _config_settings()
    payload = {
        'runtime': _runtime_settings(),
        'display': {
            'featuredSectionKeys': ['executive_summary', 'onepager_text', 'top15_text', 'satellite_backup_text'],
            'featuredSectionLimit': 4,
            'reportListLimit': 12,
            'sectionPreviewLimit': 8,
            'defaultReportId': 'latest',
        },
        'analysis': {
            'windowMode': config.get('windowMode', '上一个完整自然周（周一~周日）'),
            'taskFlow': [item.get('key') for item in config.get('taskFlow', []) if item.get('key')],
            'seedCompetitorNames': config.get('seedCompetitorSample', []),
            'tiantaKeywords': config.get('tiantaKeywordsSample', []),
        },
        'notes': [
            '当前统一由平台接管搜索入口，旧的 Bocha / Serper / Bing / SerpAPI 不再作为执行链的一部分。',
            '生成链优先使用 SearXNG + 招投标公开站点 + DuckDuckGo 兜底。',
            '本设置文件用于页面设置读写；底层 config.py 仍保留原工程定义供兼容使用。',
        ],
        'updatedAt': now_iso(),
    }
    _write_json(SETTINGS_FILE, payload)
    return payload


def _config_settings() -> dict[str, Any]:
    config_path = ROOT / 'config.py'
    text = config_path.read_text(encoding='utf-8') if config_path.exists() else ''
    seed_names = re.findall(r'"name":\s*"([^"]+)"', text)
    keywords_match = re.search(r'TIANTA_KEYWORDS\s*=\s*\[(.*?)\]', text, re.S)
    keywords = re.findall(r'"([^"]+)"', keywords_match.group(1)) if keywords_match else []
    return {
        'configPath': str(config_path),
        'settingsFile': str(SETTINGS_FILE),
        'windowMode': '上一个完整自然周（周一~周日）',
        'seedCompetitorCount': len(seed_names),
        'seedCompetitorSample': seed_names[:24],
        'tiantaKeywordsSample': keywords[:40],
        'taskFlow': _task_settings(),
    }


def _get_report_bundle(folder: Path) -> dict[str, Any]:
    report_file = _find_report_markdown(folder)
    raw_file = folder / 'raw_data.json'
    checkpoint_file = folder / 'checkpoint.json'
    if not report_file or not report_file.exists():
        raise HTTPException(status_code=404, detail='competitive_report_not_found')

    raw = report_file.read_bytes()
    for enc in ('utf-8', 'gbk', 'gb18030', 'utf-8-sig'):
        try:
            markdown = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        markdown = raw.decode('utf-8', errors='replace')
    # clean up remaining corruption mojibake: replace common garbage patterns
    markdown = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', markdown)
    raw_data = _load_json(raw_file)
    checkpoint = _load_json(checkpoint_file)

    return {
        'id': folder.name,
        'folder': folder.name,
        'title': _first_heading(markdown),
        'period': _derive_period(folder.name, markdown),
        'reportFile': str(report_file),
        'rawDataFile': str(raw_file),
        'checkpointFile': str(checkpoint_file),
        'generatedAt': checkpoint.get('updated_at') or checkpoint.get('generated_at') or now_iso(),
        'markdown': markdown,
        'sections': _extract_markdown_sections(markdown),
        'summaryCards': _build_summary_cards(raw_data),
        'rawDataKeys': list(raw_data.keys())[:30],
        'checkpointKeys': list(checkpoint.keys())[:20],
    }


@router.get('/api/competitive-analysis/status')
def competitive_analysis_status() -> dict[str, Any]:
    report_dirs = _report_dirs()
    latest = report_dirs[0] if report_dirs else None
    latest_bundle = _get_report_bundle(latest) if latest else None
    job = _read_job_status()
    running = _is_job_running()
    if job.get('status') == 'running' and not running:
        job = {
            **job,
            'status': 'stopped',
            'message': '后台生成任务已停止，请查看最近失败记录。',
            'updatedAt': now_iso(),
        }
        _write_json(JOB_STATUS_FILE, job)
    return {
        'ok': True,
        'module': 'competitive-analysis',
        'ready': bool(latest_bundle),
        'outputRoot': str(OUTPUT_ROOT),
        'availableRuns': [p.name for p in report_dirs[:20]],
        'latestRun': latest_bundle['id'] if latest_bundle else None,
        'latestTitle': latest_bundle['title'] if latest_bundle else None,
        'latestPeriod': latest_bundle['period'] if latest_bundle else None,
        'message': '竞情分析模块已接入，当前优先展示 output 中现有周报结果。' if latest_bundle else '未找到竞情分析输出目录，请先生成报告。',
        'runtime': _runtime_settings(),
        'job': job,
        'latestSuccess': _latest_success_info(),
        'latestFailure': _latest_failure_info(),
    }


@router.get('/api/competitive-analysis/reports')
def competitive_analysis_reports() -> dict[str, Any]:
    items = []
    for folder in _report_dirs()[:20]:
        try:
            bundle = _get_report_bundle(folder)
        except HTTPException:
            continue
        items.append({
            'id': bundle['id'],
            'title': bundle['title'],
            'period': bundle['period'],
            'generatedAt': bundle['generatedAt'],
            'reportFile': bundle['reportFile'],
        })
    return {'ok': True, 'items': items}


@router.get('/api/competitive-analysis/report/latest')
def competitive_analysis_report_latest() -> dict[str, Any]:
    folders = _report_dirs()
    if not folders:
        raise HTTPException(status_code=404, detail='competitive_report_not_found')
    bundle = _get_report_bundle(folders[0])
    return {'ok': True, 'report': bundle}


@router.get('/api/competitive-analysis/report/{report_id}')
def competitive_analysis_report_detail(report_id: str) -> dict[str, Any]:
    folder = OUTPUT_ROOT / report_id
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail='competitive_report_not_found')
    bundle = _get_report_bundle(folder)
    return {'ok': True, 'report': bundle}


@router.get('/api/competitive-analysis/settings')
def competitive_analysis_settings() -> dict[str, Any]:
    stored = _ensure_settings_file()
    return {
        'ok': True,
        'module': 'competitive-analysis',
        'runtime': stored.get('runtime') or _runtime_settings(),
        'display': stored.get('display') or {},
        'analysis': stored.get('analysis') or {},
        'config': _config_settings(),
        'notes': stored.get('notes') or [],
        'updatedAt': stored.get('updatedAt'),
    }


@router.put('/api/competitive-analysis/settings')
def competitive_analysis_save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = _ensure_settings_file()
    runtime = payload.get('runtime') if isinstance(payload.get('runtime'), dict) else current.get('runtime', {})
    display = payload.get('display') if isinstance(payload.get('display'), dict) else current.get('display', {})
    analysis = payload.get('analysis') if isinstance(payload.get('analysis'), dict) else current.get('analysis', {})
    notes = payload.get('notes') if isinstance(payload.get('notes'), list) else current.get('notes', [])

    runtime['searchProvider'] = 'searxng'
    runtime['searchFallbacksBlocked'] = ['bocha', 'serper', 'bing', 'serpapi']

    merged = {
        'runtime': runtime,
        'display': display,
        'analysis': analysis,
        'notes': notes,
        'updatedAt': now_iso(),
    }
    _write_json(SETTINGS_FILE, merged)
    return {'ok': True, 'data': merged}


@router.get('/api/competitive-analysis/job')
def competitive_analysis_job() -> dict[str, Any]:
    job = _read_job_status()
    running = _is_job_running()
    if job.get('status') == 'running' and not running:
        job = {
            **job,
            'status': 'stopped',
            'message': '后台生成任务已停止，请查看最近失败记录。',
            'updatedAt': now_iso(),
        }
        _write_json(JOB_STATUS_FILE, job)
    return {
        'ok': True,
        'job': job,
        'latestSuccess': _latest_success_info(),
        'latestFailure': _latest_failure_info(),
    }


@router.post('/api/competitive-analysis/generate')
def competitive_analysis_generate() -> dict[str, Any]:
    if _is_job_running():
        job = _read_job_status()
        return {
            'ok': True,
            'accepted': False,
            'message': '已有竞情分析后台任务在运行，请等待完成。',
            'job': job,
        }

    env = os.environ.copy()
    settings = _ensure_settings_file()
    runtime = settings.get('runtime') if isinstance(settings.get('runtime'), dict) else {}
    env['SEARCH_PROVIDER'] = 'searxng'
    env['BOCHA_API_KEY'] = ''
    env['SERPER_API_KEY'] = ''
    env['BING_API_KEY'] = ''
    env['SERPAPI_API_KEY'] = ''
    env['SEARXNG_BASE_URL'] = str(runtime.get('searxngBaseUrl') or os.getenv('SEARXNG_BASE_URL', env.get('SEARXNG_BASE_URL', '')))
    env['SEARXNG_VERIFY_SSL'] = 'true' if bool(runtime.get('searxngVerifySsl')) else 'false'
    env['OUTPUT_FORMAT'] = str(runtime.get('outputFormat') or os.getenv('OUTPUT_FORMAT', env.get('OUTPUT_FORMAT', 'both')))
    env['DEEPSEEK_MODEL'] = str(runtime.get('deepseekModel') or os.getenv('DEEPSEEK_MODEL', env.get('DEEPSEEK_MODEL', 'deepseek-chat')))
    env['QWEN_MODEL'] = str(runtime.get('qwenModel') or os.getenv('QWEN_MODEL', env.get('QWEN_MODEL', 'qwen-plus')))

    python_executable = COMPETITIVE_PYTHON if Path(COMPETITIVE_PYTHON).exists() else sys.executable
    job_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    job_payload = {
        'jobId': job_id,
        'status': 'queued',
        'message': '竞情分析任务已提交，后台开始生成。',
        'submittedAt': now_iso(),
        'updatedAt': now_iso(),
        'pythonExecutable': python_executable,
    }
    _write_json(JOB_STATUS_FILE, job_payload)

    try:
        process = subprocess.Popen(
            [python_executable, str(ROOT / 'job_runner.py')],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except Exception as exc:
        fail_payload = {
            **job_payload,
            'status': 'failed',
            'message': f'后台任务启动失败: {exc}',
            'updatedAt': now_iso(),
            'error': str(exc),
        }
        _write_json(JOB_STATUS_FILE, fail_payload)
        _write_json(LATEST_FAILURE_FILE, fail_payload)
        raise HTTPException(status_code=500, detail=f'competitive_generate_failed: {exc}')

    queued_payload = {
        **job_payload,
        'status': 'running',
        'pid': process.pid,
        'startedAt': now_iso(),
        'updatedAt': now_iso(),
        'message': '竞情分析后台生成中，请稍后刷新查看结果。',
    }
    _write_json(JOB_STATUS_FILE, queued_payload)
    return {
        'ok': True,
        'accepted': True,
        'message': queued_payload['message'],
        'job': queued_payload,
    }
