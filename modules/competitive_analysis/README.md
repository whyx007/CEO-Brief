# 中科天塔竞情分析信息生成器

本项目使用 [CrewAI](https://github.com/crewai) 多智能体框架及若干自定义工具，自动从互联网搜索并生成商业航天/测运控行业的竞情分析半月报，适合作为内部情报、CEO 汇报或业务决策参考。

## 📘 项目概述

- **目标**：自动收集竞争对手、市场、技术、人才、竞标/融资、政策等信息，并通过 LLM（DeepSeek）撰写结构化的 CEO 一页式摘要与 TOP15 竞争对手卡片。
- **搜索源**：博查(Bocha)、百度新闻、DuckDuckGo、政采网等；备用引擎包括 Serper、Bing。
- **LLM**：DeepSeek 并通过 CrewAI 管理七个分析智能体。
- **输出**：Markdown 报告+PDF、JSON 原始数据、备份文件，存放于 `output/<日期>_biweekly/`。

## 🔧 环境准备

1. 克隆仓库并进入目录：
   ```powershell
   git clone <repo_url> d:\Code\tianta_ci
   cd d:\Code\tianta_ci
   ```
2. 创建 Python 虚拟环境并激活（可选）：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. 安装依赖：
   ```powershell
   pip install -r requirements.txt
   ```
4. 环境变量：复制示例并编辑 API Key。
   ```powershell
   copy .env.example .env    # Windows
   # 在 .env 中填写以下键:
   # DEEPSEEK_API_KEY、BOCHA_API_KEY、JINA_API_KEY 等
   ```

> ⚠️ `DEEPSEEK_API_KEY` 为必填，否则程序不会运行；`BOCHA_API_KEY` 未配置时会退回到百度/ DuckDuckGo 检索。

## 🚀 使用方法

执行主脚本开始报告生成：

```powershell
python main.py
```

运行过程中会输出执行进度与日志，完成后在 `output/` 目录下生成本期分析目录。主要文件说明：

| 文件 | 描述 |
|------|------|
| `CEO_OnePager.md` | CEO 一页式摘要（最终报告正文） |
| `TOP15_Competitors.md` | TOP15 竞争对手详情卡片 |
| `raw_data.json` | 智能体输出的原始 JSON 数据 |
| `*_Data_Backup.md` | 若干备份列表，如商业航天测运控 TOP20、激光通讯终端数据等 |
| `report.pdf` | 从 Markdown 生成的 PDF（根据 `OUTPUT_FORMAT` 设置） |

## 🧱 项目结构

```
.
├── agents.py           # CrewAI 智能体定义
├── config.py           # 配置与默认参数
├── tasks.py            # 各类分析任务（Discover/Talent/Market/Tech/...）
├── utils/              # 工具模块
│   ├── pdf_generator.py
│   ├── report_renderer.py
│   ├── scoring.py
│   └── ...
├── tools/              # CrewAI 使用的自定义工具
│   ├── search_tool.py  # 搜索/深读/竞品检索
│   └── ...
├── output/             # 运行结果目录（自动生成）
└── main.py             # 程序入口
```

- `agents.py` 定义了七个分析角色（情报侦察、人才/市场/技术/...）。
- `tasks.py` 依序构建每个任务的 prompt 和逻辑，并处理数据流。
- `utils/report_renderer.py` 负责将结构化数据渲染为 Markdown/PDF。
- `tools/search_tool.py` 封装了外部搜索引擎接口。

## 🛠️ 配置选项

`config.py` 中包含可调参数：

```python
OUTPUT_DIR = "output"
WINDOW_LABEL = "2026-03-01 to 2026-03-15"
PDF_NAME = "report.pdf"
OUTPUT_FORMAT = "markdown"  # 可选 markdown/pdf
TZ = "Asia/Shanghai"
# API Key 通过 .env 静默注入
```

可以在运行前修改日程窗口、输出格式等。

## 📝 开发与调试

- 修改任务提示时请参考 `tasks.py` 内文档注释。
- 通过 `python main.py --dry-run`（待实现）或直接打印 `result.raw` 来调试 LLM 输出。
- 添加搜索引擎支持可在 `tools/search_tool.py` 扩展 `BaseTool`。
- 生成 PDF 的样式可在 `utils/pdf_generator.py` 调整。

## 📂 输出目录示例

```
output/20260308_biweekly/
├── CEO_OnePager.md
├── TOP15_Competitors.md
├── All_Companies_Data_Backup.md
├── raw_data.json
└── report.pdf  # 当 OUTPUT_FORMAT 设置为 pdf
```

## 📌 许可证

本项目遵循 MIT 许可证，详见 `LICENSE` 文件。

---

如有问题或改进建议，请提交 issue 或 pull request。祝使用愉快！
