#!/usr/bin/env node
/**
 * AI竞情分析系统介绍PPT
 * 面向不懂软件的同事,通俗易懂,图文并茂
 */

const pptxgen = require("pptxgenjs");

// 创建演示文稿
let pres = new pptxgen();

// 设置演示文稿属性
pres.author = "中科天塔";
pres.company = "中科天塔";
pres.subject = "AI竞情分析系统介绍";
pres.title = "AI竞情分析系统 - 让竞争情报收集变得简单高效";

// 配色方案 - Midnight Executive (专业深蓝色主题)
const colors = {
  primary: "1E2761",    // 深蓝色
  secondary: "CADCFC",  // 浅蓝色
  accent: "FFFFFF",     // 白色
  text: "2C3E50",       // 深灰色文字
  lightBg: "F5F7FA"     // 浅灰色背景
};

// ============================================
// 幻灯片 1: 封面
// ============================================
let slide1 = pres.addSlide();
slide1.background = { color: colors.primary };

slide1.addText("AI竞情分析系统", {
  x: 0.5, y: 2.0, w: 9, h: 1.5,
  fontSize: 48, bold: true, color: colors.accent,
  align: "center"
});

slide1.addText("让竞争情报收集变得简单高效", {
  x: 0.5, y: 3.5, w: 9, h: 0.6,
  fontSize: 24, color: colors.secondary,
  align: "center"
});

slide1.addText("中科天塔 AI 项目案例", {
  x: 0.5, y: 5.0, w: 9, h: 0.5,
  fontSize: 18, color: colors.secondary,
  align: "center", italic: true
});

// ============================================
// 幻灯片 2: 为什么需要竞情分析?
// ============================================
let slide2 = pres.addSlide();
slide2.background = { color: colors.accent };

slide2.addText("为什么需要竞情分析?", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

// 左侧: 痛点
slide2.addShape(pres.ShapeType.roundRect, {
  x: 0.5, y: 1.5, w: 4.2, h: 4.0,
  fill: { color: "FEE2E2" },
  line: { color: "EF4444", width: 2 }
});

slide2.addText("传统方式的痛点", {
  x: 0.7, y: 1.7, w: 3.8, h: 0.5,
  fontSize: 20, bold: true, color: "DC2626"
});

const painPoints = [
  "⏰ 耗时长: 每次收集需要3-5天",
  "👥 人力多: 需要多人协作",
  "📊 覆盖不全: 容易遗漏关键信息",
  "🔄 更新慢: 难以实时跟踪",
  "📝 格式乱: 报告质量不稳定"
];

painPoints.forEach((point, i) => {
  slide2.addText(point, {
    x: 0.9, y: 2.4 + i * 0.6, w: 3.6, h: 0.5,
    fontSize: 14, color: "7F1D1D"
  });
});

// 右侧: 需求
slide2.addShape(pres.ShapeType.roundRect, {
  x: 5.3, y: 1.5, w: 4.2, h: 4.0,
  fill: { color: "DBEAFE" },
  line: { color: "3B82F6", width: 2 }
});

slide2.addText("我们需要什么?", {
  x: 5.5, y: 1.7, w: 3.8, h: 0.5,
  fontSize: 20, bold: true, color: "1E40AF"
});

const needs = [
  "⚡ 快速: 几小时内完成",
  "🤖 自动化: 无需人工干预",
  "🎯 全面: 覆盖所有竞争对手",
  "📈 实时: 持续监测动态",
  "📄 标准化: 统一格式输出"
];

needs.forEach((point, i) => {
  slide2.addText(point, {
    x: 5.5, y: 2.4 + i * 0.6, w: 3.6, h: 0.5,
    fontSize: 14, color: "1E3A8A"
  });
});

// ============================================
// 幻灯片 3: 传统方式 vs AI方式
// ============================================
let slide3 = pres.addSlide();
slide3.background = { color: colors.accent };

slide3.addText("传统方式 vs AI方式", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

// 对比表格
const comparisonData = [
  ["对比维度", "传统人工方式", "AI自动化方式"],
  ["时间成本", "3-5天", "2-4小时 ⚡"],
  ["人力投入", "3-5人", "0人 (全自动) 🤖"],
  ["信息覆盖", "10-15家公司", "20+家公司 📊"],
  ["更新频率", "每月1次", "每半月1次 🔄"],
  ["报告质量", "依赖个人能力", "标准化输出 ✅"],
  ["数据来源", "手动搜索", "多源自动采集 🌐"]
];

slide3.addTable(comparisonData, {
  x: 0.8, y: 1.5, w: 8.4, h: 4.0,
  fontSize: 14,
  border: { pt: 1, color: colors.primary },
  fill: { color: colors.lightBg },
  color: colors.text,
  align: "center",
  valign: "middle",
  rowH: [0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6]
});

// 表头样式
slide3.addShape(pres.ShapeType.rect, {
  x: 0.8, y: 1.5, w: 8.4, h: 0.6,
  fill: { color: colors.primary }
});

// ============================================
// 幻灯片 4: 系统如何工作?
// ============================================
let slide4 = pres.addSlide();
slide4.background = { color: colors.accent };

slide4.addText("系统如何工作?", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

// 流程图
const steps = [
  { title: "1. 设定目标", icon: "🎯", desc: "确定要监测的\n竞争对手" },
  { title: "2. 自动搜索", icon: "🔍", desc: "AI从多个网站\n采集信息" },
  { title: "3. 智能分析", icon: "🧠", desc: "AI分析整理\n提取关键信息" },
  { title: "4. 生成报告", icon: "📄", desc: "自动生成\n标准化报告" }
];

steps.forEach((step, i) => {
  const x = 0.8 + i * 2.2;

  // 步骤卡片
  slide4.addShape(pres.ShapeType.roundRect, {
    x: x, y: 1.8, w: 2.0, h: 3.0,
    fill: { color: colors.lightBg },
    line: { color: colors.primary, width: 2 }
  });

  // 图标
  slide4.addText(step.icon, {
    x: x, y: 2.0, w: 2.0, h: 0.8,
    fontSize: 48, align: "center"
  });

  // 标题
  slide4.addText(step.title, {
    x: x, y: 3.0, w: 2.0, h: 0.5,
    fontSize: 16, bold: true, color: colors.primary, align: "center"
  });

  // 描述
  slide4.addText(step.desc, {
    x: x, y: 3.6, w: 2.0, h: 1.0,
    fontSize: 12, color: colors.text, align: "center"
  });

  // 箭头
  if (i < steps.length - 1) {
    slide4.addShape(pres.ShapeType.rightArrow, {
      x: x + 2.1, y: 3.1, w: 0.5, h: 0.3,
      fill: { color: colors.primary }
    });
  }
});

// ============================================
// 幻灯片 5: 7个AI助手的分工
// ============================================
let slide5 = pres.addSlide();
slide5.background = { color: colors.accent };

slide5.addText("7个AI助手协同工作", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

slide5.addText("就像一个专业团队,每个AI助手负责不同的工作", {
  x: 0.5, y: 1.2, w: 9, h: 0.4,
  fontSize: 16, color: colors.text, align: "center", italic: true
});

const agents = [
  { name: "情报侦察员", icon: "🔍", role: "发现竞争对手" },
  { name: "人才分析师", icon: "👥", role: "分析招聘动态" },
  { name: "市场分析师", icon: "📊", role: "跟踪市场动向" },
  { name: "技术分析师", icon: "💡", role: "监测技术进展" },
  { name: "竞标分析师", icon: "📋", role: "追踪中标信息" },
  { name: "融资分析师", icon: "💰", role: "关注融资动态" },
  { name: "政策分析师", icon: "📜", role: "解读政策影响" }
];

// 第一行: 4个
agents.slice(0, 4).forEach((agent, i) => {
  const x = 0.8 + i * 2.2;

  slide5.addShape(pres.ShapeType.roundRect, {
    x: x, y: 2.0, w: 2.0, h: 1.2,
    fill: { color: colors.secondary },
    line: { color: colors.primary, width: 1 }
  });

  slide5.addText(agent.icon, {
    x: x + 0.2, y: 2.15, w: 0.6, h: 0.6,
    fontSize: 32
  });

  slide5.addText(agent.name, {
    x: x + 0.9, y: 2.2, w: 1.0, h: 0.4,
    fontSize: 14, bold: true, color: colors.primary
  });

  slide5.addText(agent.role, {
    x: x + 0.2, y: 2.7, w: 1.6, h: 0.4,
    fontSize: 11, color: colors.text
  });
});

// 第二行: 3个
agents.slice(4).forEach((agent, i) => {
  const x = 2.0 + i * 2.2;

  slide5.addShape(pres.ShapeType.roundRect, {
    x: x, y: 3.5, w: 2.0, h: 1.2,
    fill: { color: colors.secondary },
    line: { color: colors.primary, width: 1 }
  });

  slide5.addText(agent.icon, {
    x: x + 0.2, y: 3.65, w: 0.6, h: 0.6,
    fontSize: 32
  });

  slide5.addText(agent.name, {
    x: x + 0.9, y: 3.7, w: 1.0, h: 0.4,
    fontSize: 14, bold: true, color: colors.primary
  });

  slide5.addText(agent.role, {
    x: x + 0.2, y: 4.2, w: 1.6, h: 0.4,
    fontSize: 11, color: colors.text
  });
});

// CEO参谋
slide5.addShape(pres.ShapeType.roundRect, {
  x: 3.5, y: 5.0, w: 3.0, h: 0.8,
  fill: { color: colors.primary }
});

slide5.addText("👔 CEO参谋: 整合所有信息,生成最终报告", {
  x: 3.5, y: 5.2, w: 3.0, h: 0.4,
  fontSize: 14, bold: true, color: colors.accent, align: "center"
});

// ============================================
// 幻灯片 5A: 监测目标展示
// ============================================
let slide5a = pres.addSlide();
slide5a.background = { color: colors.accent };

slide5a.addText("我们监测哪些公司?", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

slide5a.addText("系统自动监测30+家商业航天和激光通讯领域的重要公司", {
  x: 0.5, y: 1.2, w: 9, h: 0.4,
  fontSize: 14, color: colors.text, align: "center", italic: true
});

// 监测目标分类
const targetCategories = [
  {
    title: "客户 (15家)",
    color: "DBEAFE",
    borderColor: "3B82F6",
    examples: [
      "• 长光卫星 (吉林一号)",
      "• 中国卫星互联网集团",
      "• 西安卫星测控中心",
      "• 航天科技/科工集团",
      "• 酒泉/西昌发射中心"
    ]
  },
  {
    title: "竞争对手 (12家)",
    color: "FEE2E2",
    borderColor: "EF4444",
    examples: [
      "• 星图测控 (测控服务)",
      "• 航天驭星 (测控网络)",
      "• 中科星图 (空天平台)",
      "• 极光星通 (激光通讯)",
      "• 氦星光联 (激光终端)"
    ]
  },
  {
    title: "客户+竞争对手 (5家)",
    color: "FEF3C7",
    borderColor: "F59E0B",
    examples: [
      "• 时空道宇 (吉利卫星)",
      "• 天仪研究院",
      "• 国电高科 (天启星座)",
      "• 银河航天",
      "• 长光卫星"
    ]
  }
];

targetCategories.forEach((cat, i) => {
  const x = 0.6 + i * 3.1;

  slide5a.addShape(pres.ShapeType.roundRect, {
    x: x, y: 1.8, w: 2.8, h: 3.8,
    fill: { color: cat.color },
    line: { color: cat.borderColor, width: 2 }
  });

  slide5a.addText(cat.title, {
    x: x, y: 2.0, w: 2.8, h: 0.5,
    fontSize: 16, bold: true, color: cat.borderColor, align: "center"
  });

  cat.examples.forEach((example, j) => {
    slide5a.addText(example, {
      x: x + 0.2, y: 2.6 + j * 0.5, w: 2.4, h: 0.4,
      fontSize: 11, color: colors.text
    });
  });
});

// 底部说明
slide5a.addShape(pres.ShapeType.roundRect, {
  x: 1.5, y: 5.8, w: 7.0, h: 0.5,
  fill: { color: colors.secondary }
});

slide5a.addText("💡 系统每半月自动搜索这些公司的最新动态,确保不遗漏任何重要信息", {
  x: 1.5, y: 5.85, w: 7.0, h: 0.4,
  fontSize: 12, color: colors.primary, align: "center", bold: true
});

// ============================================
// 幻灯片 5B: 分析维度详解
// ============================================
let slide5b = pres.addSlide();
slide5b.background = { color: colors.accent };

slide5b.addText("5大分析维度", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

slide5b.addText("从5个关键维度全面分析竞争对手动态", {
  x: 0.5, y: 1.2, w: 9, h: 0.4,
  fontSize: 14, color: colors.text, align: "center", italic: true
});

const dimensions = [
  {
    icon: "👥",
    title: "人才团队 (18%)",
    items: [
      "高端人才引进",
      "关键岗位招聘",
      "核心高管变动",
      "组织架构调整"
    ]
  },
  {
    icon: "📊",
    title: "市场客户 (22%)",
    items: [
      "新签客户",
      "战略合作",
      "市场拓展",
      "客户重叠度"
    ]
  },
  {
    icon: "💡",
    title: "技术方向 (22%)",
    items: [
      "产品发布",
      "技术专利",
      "平台化能力",
      "AI大模型"
    ]
  },
  {
    icon: "📋",
    title: "竞标情况 (22%)",
    items: [
      "中标公告",
      "招标入围",
      "项目金额",
      "军采资质"
    ]
  },
  {
    icon: "💰",
    title: "融资动态 (16%)",
    items: [
      "融资轮次",
      "投资方",
      "估值变化",
      "IPO进展"
    ]
  }
];

// 第一行: 3个
dimensions.slice(0, 3).forEach((dim, i) => {
  const x = 0.8 + i * 3.0;

  slide5b.addShape(pres.ShapeType.roundRect, {
    x: x, y: 1.8, w: 2.7, h: 2.0,
    fill: { color: colors.lightBg },
    line: { color: colors.primary, width: 2 }
  });

  slide5b.addText(dim.icon, {
    x: x + 0.2, y: 1.95, w: 0.6, h: 0.6,
    fontSize: 32
  });

  slide5b.addText(dim.title, {
    x: x + 0.9, y: 2.0, w: 1.6, h: 0.5,
    fontSize: 13, bold: true, color: colors.primary
  });

  dim.items.forEach((item, j) => {
    slide5b.addText("• " + item, {
      x: x + 0.2, y: 2.7 + j * 0.35, w: 2.3, h: 0.3,
      fontSize: 10, color: colors.text
    });
  });
});

// 第二行: 2个
dimensions.slice(3).forEach((dim, i) => {
  const x = 2.3 + i * 3.0;

  slide5b.addShape(pres.ShapeType.roundRect, {
    x: x, y: 4.0, w: 2.7, h: 2.0,
    fill: { color: colors.lightBg },
    line: { color: colors.primary, width: 2 }
  });

  slide5b.addText(dim.icon, {
    x: x + 0.2, y: 4.15, w: 0.6, h: 0.6,
    fontSize: 32
  });

  slide5b.addText(dim.title, {
    x: x + 0.9, y: 4.2, w: 1.6, h: 0.5,
    fontSize: 13, bold: true, color: colors.primary
  });

  dim.items.forEach((item, j) => {
    slide5b.addText("• " + item, {
      x: x + 0.2, y: 4.9 + j * 0.35, w: 2.3, h: 0.3,
      fontSize: 10, color: colors.text
    });
  });
});

// ============================================
// 幻灯片 5C: 任务流程详解
// ============================================
let slide5c = pres.addSlide();
slide5c.background = { color: colors.accent };

slide5c.addText("8个任务协同执行", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

slide5c.addText("任务之间有依赖关系,确保数据准确性和完整性", {
  x: 0.5, y: 1.2, w: 9, h: 0.4,
  fontSize: 14, color: colors.text, align: "center", italic: true
});

const tasks = [
  {
    num: "1",
    name: "竞情目标发现",
    desc: "确认15-20家监测目标",
    color: "3B82F6"
  },
  {
    num: "2-6",
    name: "5维度情报收集",
    desc: "人才/市场/技术/竞标/融资",
    color: "8B5CF6"
  },
  {
    num: "7",
    name: "威胁评分排名",
    desc: "加权计算,TOP15排名",
    color: "EC4899"
  },
  {
    num: "8",
    name: "报告生成",
    desc: "生成半月竞情报告",
    color: "10B981"
  }
];

tasks.forEach((task, i) => {
  const y = 2.0 + i * 1.0;

  slide5c.addShape(pres.ShapeType.roundRect, {
    x: 1.5, y: y, w: 7.0, h: 0.8,
    fill: { color: colors.lightBg },
    line: { color: task.color, width: 3 }
  });

  // 任务编号
  slide5c.addShape(pres.ShapeType.ellipse, {
    x: 1.7, y: y + 0.15, w: 0.5, h: 0.5,
    fill: { color: task.color }
  });

  slide5c.addText(task.num, {
    x: 1.7, y: y + 0.15, w: 0.5, h: 0.5,
    fontSize: 16, bold: true, color: colors.accent, align: "center", valign: "middle"
  });

  // 任务名称
  slide5c.addText(task.name, {
    x: 2.4, y: y + 0.1, w: 3.5, h: 0.4,
    fontSize: 16, bold: true, color: colors.primary
  });

  // 任务描述
  slide5c.addText(task.desc, {
    x: 2.4, y: y + 0.45, w: 3.5, h: 0.3,
    fontSize: 12, color: colors.text
  });

  // 箭头
  if (i < tasks.length - 1) {
    slide5c.addShape(pres.ShapeType.downArrow, {
      x: 4.8, y: y + 0.85, w: 0.4, h: 0.3,
      fill: { color: colors.primary }
    });
  }
});

// 右侧说明
slide5c.addShape(pres.ShapeType.roundRect, {
  x: 6.2, y: 2.0, w: 2.3, h: 3.8,
  fill: { color: colors.secondary },
  line: { color: colors.primary, width: 1 }
});

slide5c.addText("⚙️ 执行特点", {
  x: 6.4, y: 2.2, w: 1.9, h: 0.4,
  fontSize: 14, bold: true, color: colors.primary
});

const features = [
  "✅ 自动执行",
  "✅ 并行处理",
  "✅ 依赖管理",
  "✅ 错误重试",
  "✅ 结果验证"
];

features.forEach((feature, i) => {
  slide5c.addText(feature, {
    x: 6.4, y: 2.8 + i * 0.5, w: 1.9, h: 0.4,
    fontSize: 11, color: colors.text
  });
});

// ============================================
// 幻灯片 6: 核心能力展示
// ============================================
let slide6 = pres.addSlide();
slide6.background = { color: colors.accent };

slide6.addText("核心能力展示", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

const capabilities = [
  {
    title: "多源数据采集",
    icon: "🌐",
    items: [
      "• 新闻网站",
      "• 招聘平台",
      "• 招投标网站",
      "• 融资公告",
      "• 专利数据库"
    ]
  },
  {
    title: "智能分析处理",
    icon: "🧠",
    items: [
      "• 自动提取关键信息",
      "• 识别重要动态",
      "• 评估威胁等级",
      "• 发现竞争趋势",
      "• 生成战略建议"
    ]
  },
  {
    title: "自动报告生成",
    icon: "📄",
    items: [
      "• 标准化格式",
      "• 图表可视化",
      "• PDF自动生成",
      "• 引用来源标注",
      "• 支持定制化"
    ]
  }
];

capabilities.forEach((cap, i) => {
  const x = 0.6 + i * 3.1;

  slide6.addShape(pres.ShapeType.roundRect, {
    x: x, y: 1.5, w: 2.8, h: 4.0,
    fill: { color: colors.lightBg },
    line: { color: colors.primary, width: 2 }
  });

  slide6.addText(cap.icon, {
    x: x, y: 1.7, w: 2.8, h: 0.8,
    fontSize: 48, align: "center"
  });

  slide6.addText(cap.title, {
    x: x, y: 2.6, w: 2.8, h: 0.5,
    fontSize: 18, bold: true, color: colors.primary, align: "center"
  });

  cap.items.forEach((item, j) => {
    slide6.addText(item, {
      x: x + 0.3, y: 3.3 + j * 0.4, w: 2.2, h: 0.35,
      fontSize: 12, color: colors.text
    });
  });
});

// ============================================
// 幻灯片 7: 实际效果展示
// ============================================
let slide7 = pres.addSlide();
slide7.background = { color: colors.accent };

slide7.addText("实际效果展示", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

// 数据对比
const metrics = [
  { label: "监测公司数量", before: "10-15家", after: "20+家", improvement: "+50%" },
  { label: "信息更新频率", before: "每月1次", after: "每半月1次", improvement: "2倍" },
  { label: "报告生成时间", before: "3-5天", after: "2-4小时", improvement: "20倍" },
  { label: "人力投入", before: "3-5人", after: "0人", improvement: "100%" }
];

slide7.addShape(pres.ShapeType.rect, {
  x: 1.0, y: 1.8, w: 8.0, h: 0.5,
  fill: { color: colors.primary }
});

slide7.addText("指标", {
  x: 1.0, y: 1.85, w: 2.5, h: 0.4,
  fontSize: 14, bold: true, color: colors.accent, align: "center"
});

slide7.addText("传统方式", {
  x: 3.5, y: 1.85, w: 2.0, h: 0.4,
  fontSize: 14, bold: true, color: colors.accent, align: "center"
});

slide7.addText("AI方式", {
  x: 5.5, y: 1.85, w: 2.0, h: 0.4,
  fontSize: 14, bold: true, color: colors.accent, align: "center"
});

slide7.addText("提升", {
  x: 7.5, y: 1.85, w: 1.5, h: 0.4,
  fontSize: 14, bold: true, color: colors.accent, align: "center"
});

metrics.forEach((metric, i) => {
  const y = 2.4 + i * 0.7;
  const bgColor = i % 2 === 0 ? colors.lightBg : "FFFFFF";

  slide7.addShape(pres.ShapeType.rect, {
    x: 1.0, y: y, w: 8.0, h: 0.6,
    fill: { color: bgColor },
    line: { color: "E5E7EB", width: 1 }
  });

  slide7.addText(metric.label, {
    x: 1.2, y: y + 0.1, w: 2.3, h: 0.4,
    fontSize: 13, color: colors.text
  });

  slide7.addText(metric.before, {
    x: 3.5, y: y + 0.1, w: 2.0, h: 0.4,
    fontSize: 13, color: "DC2626", align: "center"
  });

  slide7.addText(metric.after, {
    x: 5.5, y: y + 0.1, w: 2.0, h: 0.4,
    fontSize: 13, color: "059669", align: "center", bold: true
  });

  slide7.addText(metric.improvement, {
    x: 7.5, y: y + 0.1, w: 1.5, h: 0.4,
    fontSize: 13, color: "059669", align: "center", bold: true
  });
});

// 底部说明
slide7.addText("✅ 效率提升显著  ✅ 质量更加稳定  ✅ 成本大幅降低", {
  x: 1.0, y: 5.2, w: 8.0, h: 0.5,
  fontSize: 16, color: colors.primary, align: "center", bold: true
});

// ============================================
// 幻灯片 8: 价值与收益
// ============================================
let slide8 = pres.addSlide();
slide8.background = { color: colors.accent };

slide8.addText("价值与收益", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

const benefits = [
  {
    icon: "💰",
    title: "降低成本",
    desc: "节省人力成本\n提高工作效率"
  },
  {
    icon: "⚡",
    title: "提升速度",
    desc: "快速响应市场\n及时把握机会"
  },
  {
    icon: "🎯",
    title: "提高质量",
    desc: "标准化输出\n减少人为错误"
  },
  {
    icon: "📈",
    title: "增强竞争力",
    desc: "洞察市场动态\n制定战略决策"
  }
];

benefits.forEach((benefit, i) => {
  const row = Math.floor(i / 2);
  const col = i % 2;
  const x = 1.0 + col * 4.5;
  const y = 1.8 + row * 2.0;

  slide8.addShape(pres.ShapeType.roundRect, {
    x: x, y: y, w: 4.0, h: 1.6,
    fill: { color: colors.lightBg },
    line: { color: colors.primary, width: 2 }
  });

  slide8.addText(benefit.icon, {
    x: x + 0.3, y: y + 0.3, w: 0.8, h: 0.8,
    fontSize: 48
  });

  slide8.addText(benefit.title, {
    x: x + 1.3, y: y + 0.3, w: 2.4, h: 0.5,
    fontSize: 20, bold: true, color: colors.primary
  });

  slide8.addText(benefit.desc, {
    x: x + 1.3, y: y + 0.8, w: 2.4, h: 0.7,
    fontSize: 13, color: colors.text
  });
});

// ============================================
// 幻灯片 9: AI工具开发的借鉴
// ============================================
let slide9 = pres.addSlide();
slide9.background = { color: colors.accent };

slide9.addText("AI工具开发的借鉴", {
  x: 0.5, y: 0.5, w: 9, h: 0.8,
  fontSize: 36, bold: true, color: colors.primary
});

slide9.addText("这个项目可以给我们什么启发?", {
  x: 0.5, y: 1.2, w: 9, h: 0.4,
  fontSize: 16, color: colors.text, align: "center", italic: true
});

const lessons = [
  {
    title: "1. 找准痛点",
    content: "从实际工作中的重复性、耗时的任务入手,这些最适合用AI来解决"
  },
  {
    title: "2. 分工协作",
    content: "复杂任务可以拆分成多个小任务,让不同的AI助手各司其职,就像团队协作"
  },
  {
    title: "3. 标准化输出",
    content: "AI的优势在于能够持续输出标准化、高质量的结果,减少人为差异"
  },
  {
    title: "4. 持续优化",
    content: "AI系统可以不断学习和改进,随着使用越来越智能,效果越来越好"
  },
  {
    title: "5. 人机协同",
    content: "AI不是替代人,而是帮助人做得更好。人负责决策,AI负责执行"
  }
];

lessons.forEach((lesson, i) => {
  const y = 1.8 + i * 0.75;

  slide9.addShape(pres.ShapeType.roundRect, {
    x: 1.0, y: y, w: 8.0, h: 0.65,
    fill: { color: colors.lightBg },
    line: { color: colors.primary, width: 1 }
  });

  slide9.addText(lesson.title, {
    x: 1.3, y: y + 0.08, w: 1.5, h: 0.5,
    fontSize: 14, bold: true, color: colors.primary
  });

  slide9.addText(lesson.content, {
    x: 2.9, y: y + 0.08, w: 5.8, h: 0.5,
    fontSize: 13, color: colors.text
  });
});

// ============================================
// 幻灯片 10: 未来展望
// ============================================
let slide10 = pres.addSlide();
slide10.background = { color: colors.primary };

slide10.addText("未来展望", {
  x: 0.5, y: 1.5, w: 9, h: 0.8,
  fontSize: 40, bold: true, color: colors.accent, align: "center"
});

const future = [
  "🚀 扩展到更多业务场景",
  "🌍 覆盖全球竞争对手",
  "📊 更智能的数据分析",
  "🤝 与其他系统集成",
  "💡 持续优化和升级"
];

future.forEach((item, i) => {
  slide10.addText(item, {
    x: 2.0, y: 2.8 + i * 0.5, w: 6.0, h: 0.4,
    fontSize: 18, color: colors.secondary, align: "center"
  });
});

slide10.addText("让AI成为我们的得力助手", {
  x: 0.5, y: 5.0, w: 9, h: 0.6,
  fontSize: 24, color: colors.accent, align: "center", italic: true
});

// ============================================
// 幻灯片 11: 感谢页
// ============================================
let slide11 = pres.addSlide();
slide11.background = { color: colors.primary };

slide11.addText("感谢观看", {
  x: 0.5, y: 2.5, w: 9, h: 1.0,
  fontSize: 48, bold: true, color: colors.accent, align: "center"
});

slide11.addText("欢迎交流讨论", {
  x: 0.5, y: 3.8, w: 9, h: 0.6,
  fontSize: 24, color: colors.secondary, align: "center"
});

// 保存演示文稿
pres.writeFile({ fileName: "AI竞情分析系统介绍.pptx" })
  .then(() => {
    console.log("✅ PPT生成成功: AI竞情分析系统介绍.pptx");
  })
  .catch((err) => {
    console.error("❌ PPT生成失败:", err);
  });
