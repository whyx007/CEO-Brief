# CEO参阅启动说明

## 当前主线

当前项目以后端 **Python 3.10 + FastAPI** 为准。

- 主入口：`app.py`
- 默认地址：`http://127.0.0.1:8000`
- 前端页面由 FastAPI 直接挂载，访问根路径 `/` 即可打开

> 说明：旧的 JS MVP 后端已移除，后续联调与优化请统一以 Python / FastAPI 版本为准。

## 安装依赖

推荐使用专用 conda 环境 `ceo-brief-py310`：

```powershell
conda create -y -n ceo-brief-py310 python=3.10
conda activate ceo-brief-py310
cd ceo-brief
python -m pip install -r requirements.txt
```

如果当前 shell 没有继承 conda，也可以直接使用环境解释器：

```powershell
D:\ProgramData\miniconda3\envs\ceo-brief-py310\python.exe -m pip install -r requirements.txt
```

## 启动服务

```powershell
D:\ProgramData\miniconda3\envs\ceo-brief-py310\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

或直接使用脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-python.ps1
```

## 停止服务

```powershell
powershell -ExecutionPolicy Bypass -File .\stop-python.ps1
```

## 当前已验证可用接口

- `GET /health`
- `GET /api/ceo-brief/today`
- `POST /api/ceo-brief/generate`
- `POST /api/ceo-brief/jobs/generate`
- `GET /api/ceo-brief/latest-run`
- `GET /api/ceo-brief/latest-brief`
- `GET /api/ceo-brief/settings/targets`
- `PUT /api/ceo-brief/settings/targets`
- `GET /api/ceo-brief/settings/prompts`
- `PUT /api/ceo-brief/settings/prompts`
- `POST /api/ceo-brief/settings/prompts/reset`
- `GET /api/ceo-brief/llm/status`
- `POST /api/ceo-brief/generate/free`

## 当前实现说明

- 前端页面位于 `frontend/`，由 FastAPI 直接提供
- 首页、设置页、最新 Markdown 正文查看已可打开
- 基础 mock regenerate 与免费源生成接口均已接入 Python 主服务
- settings 读写直接落到 JSON 文件
- 当前最适合推进的工作是：前端联调、字段/状态优化、免费源生成质量提升
