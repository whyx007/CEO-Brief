from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from modules.ceo_brief.routes import router as ceo_brief_router
from modules.company_query.routes import router as company_query_router
from modules.competitive_analysis.routes import router as competitive_analysis_router
from modules.industry_chain.routes import router as industry_chain_router

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / 'frontend'
LOGO_DIR = ROOT / 'logo'
COMPANY_SUMMARY_DIR = Path('/data/company-summary')
VENDOR_DIR = FRONTEND_DIR / 'vendor'

app = FastAPI(title='AI Post-Invest Platform', version='0.5.0')
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r'^(https?://(localhost|127\.0\.0\.1)(:\d+)?|null)$',
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)
app.include_router(ceo_brief_router)
app.include_router(company_query_router)
app.include_router(competitive_analysis_router)
app.include_router(industry_chain_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            'ok': False,
            'detail': 'internal_server_error',
            'message': str(exc) or exc.__class__.__name__,
            'path': request.url.path,
        },
    )


if FRONTEND_DIR.exists():
    app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIR / 'assets')), name='platform-assets')
if VENDOR_DIR.exists():
    app.mount('/vendor', StaticFiles(directory=str(VENDOR_DIR)), name='platform-vendor')
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
