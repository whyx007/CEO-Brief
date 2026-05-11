# CEO参阅 Python 后端 MVP 启动说明

## 安装依赖

推荐使用专用 conda 环境 `ceo-brief-py310`。

创建环境：

```powershell
conda create -y -n ceo-brief-py310 python=3.10
```

激活环境：

```powershell
conda activate ceo-brief-py310
```

安装依赖：

```powershell
cd ceo-brief
python -m pip install -r requirements.txt
```

如果当前 shell 没有正确继承 conda，也可以直接使用环境里的解释器：

```powershell
D:\ProgramData\miniconda3\envs\ceo-brief-py310\python.exe -m pip install -r requirements.txt
```

## 启动服务

```powershell
D:\ProgramData\miniconda3\envs\ceo-brief-py310\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

或使用脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-python.ps1
```

## 停止服务

```powershell
powershell -ExecutionPolicy Bypass -File .\stop-python.ps1
```

## 接口
- `GET /health`
- `GET /api/ceo-brief/today`
- `POST /api/ceo-brief/generate`
- `POST /api/ceo-brief/jobs/generate`
- `GET /api/ceo-brief/latest-run`
- settings 相关读写接口

## 当前定位
- Python / FastAPI 版 MVP
- 基于 mock 数据跑通主链路
- 适合后续接 AI 生态、真实新闻源和数据库
