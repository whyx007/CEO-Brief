from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules.ceo_brief.routes import router as ceo_brief_router
from modules.company_query.routes import router as company_query_router
from modules.competitive_analysis.routes import router as competitive_analysis_router

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / 'frontend'
LOGO_DIR = ROOT / 'logo'
COMPANY_SUMMARY_DIR = Path('/data/company-summary')

app = FastAPI(title='AI Post-Invest Platform', version='0.5.0')
app.include_router(ceo_brief_router)
app.include_router(company_query_router)
app.include_router(competitive_analysis_router)

if FRONTEND_DIR.exists():
    app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIR / 'assets')), name='platform-assets')
if COMPANY_SUMMARY_DIR.exists():
    app.mount('/company-summary', StaticFiles(directory=str(COMPANY_SUMMARY_DIR)), name='company-summary')
if LOGO_DIR.exists():
    app.mount('/logo', StaticFiles(directory=str(LOGO_DIR)), name='logo')


@app.get('/')
def frontend_index() -> FileResponse:
    index_path = FRONTEND_DIR / 'index.html'
    if not index_path.exists():
        raise HTTPException(status_code=404, detail='frontend_not_built')
    return FileResponse(index_path)
