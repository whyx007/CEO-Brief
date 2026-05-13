from pathlib import Path
import re

root = Path(r"C:\Users\Administrator\.openclaw\workspace\finance-postinvest-ai-platform\ceo-brief")
app_path = root / 'app.py'
app_src = app_path.read_text(encoding='utf-8')

routes_src = app_src
routes_src = routes_src.replace('from fastapi import FastAPI, HTTPException', 'from fastapi import APIRouter, HTTPException')
routes_src = routes_src.replace("ROOT = Path(__file__).resolve().parent", "ROOT = Path(__file__).resolve().parents[2]")
routes_src = routes_src.replace("app = FastAPI(title='AI Post-Invest Platform', version='0.3.0')\nFRONTEND_DIR = ROOT / 'frontend'\n\napp.include_router(company_query_router)\n", "router = APIRouter()\nFRONTEND_DIR = ROOT / 'frontend'\n")
routes_src = routes_src.replace('from modules.company_query.routes import router as company_query_router\n', '')
routes_src = routes_src.replace('@app.', '@router.')
# remove static mount + frontend route at end
routes_src = re.sub(r"\nif FRONTEND_DIR.exists\(\):[\s\S]*?@router.get\('/'\)[\s\S]*?$", "\n", routes_src)

ceo_dir = root / 'modules' / 'ceo_brief'
ceo_dir.mkdir(parents=True, exist_ok=True)
(ceo_dir / '__init__.py').write_text('# ceo_brief package\n', encoding='utf-8')
(ceo_dir / 'routes.py').write_text(routes_src, encoding='utf-8')

new_app = '''from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules.ceo_brief.routes import router as ceo_brief_router
from modules.company_query.routes import router as company_query_router

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / 'frontend'

app = FastAPI(title='AI Post-Invest Platform', version='0.4.0')
app.include_router(ceo_brief_router)
app.include_router(company_query_router)

if FRONTEND_DIR.exists():
    app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIR / 'assets')), name='platform-assets')


@app.get('/')
def frontend_index() -> FileResponse:
    index_path = FRONTEND_DIR / 'index.html'
    if not index_path.exists():
        raise HTTPException(status_code=404, detail='frontend_not_built')
    return FileResponse(index_path)
'''
app_path.write_text(new_app, encoding='utf-8')
print('migrated')
