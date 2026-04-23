# CEO参阅后端主线说明

## 当前主线
项目后端主线已切换为：
- **Python 3.10 + FastAPI**

当前推荐服务入口：
- `app.py`

## Conda 环境
推荐环境名：
- `ceo-brief-py310`

创建：
```powershell
conda create -y -n ceo-brief-py310 python=3.10
```

激活：
```powershell
conda activate ceo-brief-py310
```

## 安装依赖
```powershell
python -m pip install -r requirements.txt
```

## 启动
```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

或：
```powershell
powershell -ExecutionPolicy Bypass -File .\start-python.ps1
```

## 当前可用接口
- `GET /health`
- `GET /api/ceo-brief/today`
- `POST /api/ceo-brief/generate`
- `POST /api/ceo-brief/jobs/generate`
- `GET /api/ceo-brief/latest-run`
- settings 相关接口

## JS 版本说明
旧的 JS MVP 后端已移除。

后续继续开发时，默认以 Python 版本为准。
