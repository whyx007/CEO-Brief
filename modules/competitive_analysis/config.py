"""
全局配置 — 中科天塔竞情分析周报
"""

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────
# 时间窗口（周报）
# ──────────────────────────────────────
TZ = timezone(timedelta(hours=8))
# 使用“上一个完整自然周（周一~周日）”作为周报窗口，确保前后期不重叠。
_now = datetime.now(TZ)
_current_week_start = (_now - timedelta(days=_now.weekday())).replace(
    hour=0, minute=0, second=0, microsecond=0
)
REPORT_START = _current_week_start - timedelta(days=7)
REPORT_END = _current_week_start - timedelta(days=1)
WINDOW_LABEL = f"{REPORT_START.strftime('%Y.%m.%d')} ~ {REPORT_END.strftime('%Y.%m.%d')}"

# ──────────────────────────────────────
# DeepSeek LLM
# ──────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ──────────────────────────────────────
# 阿里 Qwen LLM
# ──────────────────────────────────────
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# # ──────────────────────────────────────
# # 搜索 API
# # ──────────────────────────────────────
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
# SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
# BING_API_KEY = os.getenv("BING_API_KEY", "")
# TIANYANCHA_API_KEY = os.getenv("TIANYANCHA_API_KEY", "")

# ──────────────────────────────────────
# 搜索引擎
# ──────────────────────────────────────
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")          # 🥇 推荐
JINA_API_KEY = os.getenv("JINA_API_KEY", "")            # 深度抓取
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")        # 备选
BING_API_KEY = os.getenv("BING_API_KEY", "")            # 备选

# ──────────────────────────────────────
# 输出
# ──────────────────────────────────────
PDF_NAME = f"天塔竞情战略情报（{REPORT_END.strftime('%Y%m%d')}）.pdf"
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "both")  # 可选值："md"、"pdf"、"both"

OUTPUT_DIR = os.path.join(
    "output",
    f"{REPORT_END.strftime('%Y%m%d')}_weekly"
)

# ──────────────────────────────────────
# 威胁评分权重（CEO 视角）
# ──────────────────────────────────────
THREAT_WEIGHTS = {
    "talent":  0.18,   # 人才团队
    "market":  0.22,   # 市场客户
    "tech":    0.22,   # 技术方向
    "bidding": 0.22,   # 竞标
    "funding": 0.16,   # 融资
}

# ──────────────────────────────────────
# 中科天塔核心业务关键词（用于搜索 & 相关度判断）

# ──────────────────────────────────────
TIANTA_KEYWORDS = [
    "卫星测控", "在轨管理", "航天器管理", "测运控软件", "测运控技术服务","测运控硬件",
    "卫星激光通讯", "激光通讯终端","星间链路",
    "地面站", "卫星健康管理", "卫星星座管理",
    # 避免泛泛的"大模型"概念，聚焦于天塔核心业务
    "智能地面测控系统", "航天云平台", "航天私域大模型", "卫星数字星座仿真与智能平台",
    "航天卫星轨道计算", "TT&C",

]

# ──────────────────────────────────────
# 种子竞情目标名单（包含客户、竞争对手、潜在客户）
# Agent 会自动发现更多并精选 TOP15
# type: "客户" / "竞争对手" / "客户+竞争对手" / "潜在客户"
# importance: "高" / "中" / "低"
# ──────────────────────────────────────
SEED_COMPETITORS = [
    # ── 主要客户（高价值，需密切关注动向，防止流失或自建体系） ──
    {
        "name": "长光卫星",
        "aka": ["长光卫星技术股份有限公司", "吉林一号"],
        "type": "客户",
        "reason": "重要客户，但已自建测运控体系（吉星云平台），存在客户流失风险；已实现星地100Gbps激光通信，技术能力强",
        "importance": "高"
    },
    {
        "name": "上海垣信卫星",
        "aka": ["上海垣信卫星科技有限公司"],
        "type": "客户",
        "reason": "商业航天重要客户，卫星星座运营商，测控服务需求持续",
        "importance": "高"
    },
    {
        "name": "国科量子",
        "aka": ["国科量子通信网络有限公司"],
        "type": "客户",
        "reason": "中科院体系重要客户，量子通信+航天信息化，战略价值高",
        "importance": "高"
    },
    {
        "name": "中国卫星互联网集团",
        "aka": ["中国卫星互联网集团公司"],
        "type": "客户",
        "reason": "国家队卫星互联网主力，超大规模星座建设，测控需求巨大，战略级客户",
        "importance": "高"
    },
    {
        "name": "西安卫星测控中心",
        "aka": ["西安卫星测控中心"],
        "type": "客户",
        "reason": "国家级卫星测控中心，航天测控核心单位，战略级客户",
        "importance": "高"
    },
    {
        "name": "北京飞行控制中心",
        "aka": ["北京飞行控制中心", "北京航天飞行控制中心"],
        "type": "客户",
        "reason": "国家级航天飞行控制中心，载人航天及深空探测核心单位，战略级客户",
        "importance": "高"
    },
    {
        "name": "中国科学院空天信息创新研究院",
        "aka": ["中科院空天信息创新研究院"],
        "type": "客户",
        "reason": "中科院体系重要客户，空天信息技术研发核心单位，科研合作价值高",
        "importance": "高"
    },
    {
        "name": "中国科学院国家空间科学中心",
        "aka": ["中科院国家空间科学中心"],
        "type": "客户",
        "reason": "中科院体系重要客户，空间科学任务核心单位，科研合作价值高",
        "importance": "高"
    },
    {
        "name": "国防科技大学",
        "aka": ["国防科技大学", "国防科大"],
        "type": "客户",
        "reason": "军队重点高校，航天测控技术研发及人才培养，战略合作价值高",
        "importance": "高"
    },
    {
        "name": "航天工程大学",
        "aka": ["航天工程大学"],
        "type": "客户",
        "reason": "军队航天专业高校，航天测控技术研发及人才培养，战略合作价值高",
        "importance": "高"
    },
    {
        "name": "航天科技集团",
        "aka": ["中国航天科技集团", "航天科技"],
        "type": "客户",
        "reason": "国家队航天主力，卫星研制及发射主力军，战略级客户",
        "importance": "高"
    },
    {
        "name": "航天科工集团",
        "aka": ["中国航天科工集团", "航天科工"],
        "type": "客户",
        "reason": "国家队航天主力，商业航天及军工业务，战略级客户",
        "importance": "高"
    },
    {
        "name": "中电科集团",
        "aka": ["中国电子科技集团", "中电科"],
        "type": "客户",
        "reason": "国家队电子信息主力，卫星测控通信设备及系统集成，战略级客户",
        "importance": "高"
    },
    {
        "name": "银河航天",
        "aka": ["银河航天（北京）科技有限公司"],
        "type": "客户",
        "reason": "低轨宽带星座，自建测控+在轨管理体系，透明转发架构直连卫星技术",
        "importance": "高"
    },

    # ── 发射场客户（已有客户及目标客户） ──
    {
        "name": "酒泉卫星发射中心",
        "aka": ["酒泉卫星发射中心"],
        "type": "客户",
        "reason": "国家级卫星发射场，测控服务需求方，战略合作价值高",
        "importance": "高"
    },
    {
        "name": "西昌卫星发射中心",
        "aka": ["西昌卫星发射中心"],
        "type": "客户",
        "reason": "国家级卫星发射场，测控服务需求方，战略合作价值高",
        "importance": "高"
    },
    {
        "name": "太原卫星发射中心",
        "aka": ["太原卫星发射中心"],
        "type": "客户",
        "reason": "国家级卫星发射场，测控服务需求方，战略合作价值高",
        "importance": "高"
    },
    {
        "name": "文昌卫星发射中心",
        "aka": ["文昌卫星发射中心", "文昌航天发射场"],
        "type": "客户",
        "reason": "国家级卫星发射场，测控服务需求方，战略合作价值高",
        "importance": "高"
    },
    {
        "name": "海南国际商业航天发射",
        "aka": ["海南国际商业航天发射有限公司"],
        "type": "客户",
        "reason": "商业航天发射场，测控服务需求方，战略合作价值高",
        "importance": "高"
    },

    # ── 主要竞争对手（直接竞争测控、在轨管理业务） ──
    {
        "name": "星图测控",
        "aka": ["中科星图测控技术股份有限公司", "北京星图测控"],
        "type": "竞争对手",
        "reason": "专业商业航天测控、在轨管理服务，北交所上市，提供全链路测运控解决方案，直接竞争",
        "importance": "高"
    },
    {
        "name": "寰宇卫星",
        "aka": ["西安寰宇卫星测控与数据应用有限公司", "寰宇卫星科技有限公司"],
        "type": "竞争对手",
        "reason": "商业卫星测控网建设龙头，为300+卫星提供服务，直接竞争天塔测控业务",
        "importance": "高"
    },
    {
        "name": "开运联合",
        "aka": ["北京开运联合信息技术集团股份有限公司"],
        "type": "竞争对手",
        "reason": "航天信息化综合服务商，测控软件及系统集成，与天塔业务重叠",
        "importance": "中"
    },
    {
        "name": "星邑空间",
        "aka": ["陕西星邑空间技术有限公司"],
        "type": "竞争对手",
        "reason": "西安本地竞争对手，卫星测控及在轨管理服务",
        "importance": "中"
    },
    {
        "name": "航天驭星",
        "aka": ["北京航天驭星科技有限公司", "ASES"],
        "type": "竞争对手",
        "reason": "商业航天测控龙头，已建全球测控网络，测运控定标一体化云平台",
        "importance": "高"
    },

    # ── 航天软件平台（平台化竞争） ──
    {
        "name": "中科星图",
        "aka": ["中科星图股份有限公司", "GEOVIS"],
        "type": "竞争对手",
        "reason": "空天信息平台，GEOVIS数字地球，星图太空云，上市公司资源强，平台化竞争",
        "importance": "高"
    },
    {
        "name": "航天宏图",
        "aka": ["航天宏图信息技术股份有限公司", "PIE"],
        "type": "竞争对手",
        "reason": "遥感+空间信息平台，PIE生态扩展到在轨管理，PIE-Engine天权大模型",
        "importance": "高"
    },
    # ── 激光通讯终端（直接竞争天塔激光通讯业务） ──
    {
        "name": "极光星通",
        "aka": ["北京极光星通科技有限公司", "极光星通（北京）空间技术有限公司", "Laser Starcom"],
        "type": "竞争对手",
        "reason": "国内领先星载激光通信终端供应商，已完成400Gbps星间激光通信在轨验证，高速星间/星地链路直接竞争",
        "importance": "高"
    },
    {
        "name": "氦星光联",
        "aka": ["氦星光联科技（深圳）有限公司", "HiStarlink"],
        "type": "竞争对手",
        "reason": "专注低功耗小型化星载激光通讯终端，国内最大产能产线（数百台/年），与天塔终端业务高度重叠",
        "importance": "高"
    },
    {
        "name": "蓝星光域",
        "aka": ["蓝星光域（上海）航天科技有限公司"],
        "type": "竞争对手",
        "reason": "我国首家完成星载激光通信终端交付验证的商业企业，全面掌握激光链路、终端总体、捕获跟踪（PAT）核心技术",
        "importance": "高"
    },
    {
        "name": "比羿激光",
        "aka": ["比羿激光科技（湖州）有限公司"],
        "type": "竞争对手",
        "reason": "空间激光通信终端创新企业，近期多轮融资，专注高性能星载终端，10Gbps星间激光载荷",
        "importance": "中"
    },

    # ── 卫星运营/星座（潜在客户变竞争） ──
    {
        "name": "时空道宇",
        "aka": ["浙江时空道宇科技有限公司", "吉利卫星"],
        "type": "客户+竞争对手",
        "reason": "吉利系，未来出行星座+自建地面段，全栈自主设计研发",
        "importance": "中"
    },
    {
        "name": "天仪研究院",
        "aka": ["天仪空间科技研究院（长沙）有限公司"],
        "type": "客户+竞争对手",
        "reason": "微小卫星制造+运营，自研在轨管理，IPO进程中",
        "importance": "中"
    },
    {
        "name": "国电高科",
        "aka": ["国电高科科技有限公司", "天启星座"],
        "type": "客户+竞争对手",
        "reason": "窄带物联网星座，自研测运控系统已接入全部38颗在轨卫星",
        "importance": "中"
    },

    # ── 地面站设备/测控通信 ──
    {
        "name": "海格通信",
        "aka": ["广州海格通信集团股份有限公司"],
        "type": "竞争对手",
        "reason": "卫星通信+导航，大型上市军工集团，天腾低空管理平台",
        "importance": "中"
    },
]

# ──────────────────────────────────────
# 搜索查询模板
# ──────────────────────────────────────
SEARCH_QUERIES = {
    "talent": [
        "{company} 招聘 测控 在轨管理 架构师 算法",
        "{company} 人才 团队 扩张 CTO 首席科学家",
        "{company} 组织架构 核心团队 技术负责人",
    ],
    "market": [
        "{company} 签约 合同 客户 卫星运营 星座",
        "{company} 市场 合作 中标 交付 应用",
        "{company} 客户 案例 落地 部署 应用场景",
    ],
    "tech": [
        "{company} 在轨管理 技术 平台 发布 升级",
        "{company} 卫星 大模型 AI 智能化 专利",
        "{company} 测控 软件 系统 架构 创新 论文",
    ],
    "bidding": [
        "{company} 中标 招标 入围 采购 项目",
        "{company} 政府采购 军队采购 国防 框架协议",
        "{company} 卫星 地面站 测控 中标公告",
    ],
    "funding": [
        "{company} 融资 投资 A轮 B轮 C轮 估值",
        "{company} 股权变更 增资 国资 产业基金",
        "{company} 上市 IPO 科创板 北交所",
    ],
}