"""
PDF报告生成器 - 参考政府工作报告样式
使用reportlab生成PDF，支持中文字体
"""

import os
import re
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, BaseDocTemplate, PageTemplate, Frame, NextPageTemplate
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_chinese_fonts():
    """注册中文字体"""
    # 尝试注册常见的中文字体
    font_paths = [
        # Windows 系统字体路径
        (r"C:\Windows\Fonts\simsun.ttc", "SimSun"),  # 宋体
        (r"C:\Windows\Fonts\simhei.ttf", "SimHei"),  # 黑体
        (r"C:\Windows\Fonts\simkai.ttf", "SimKai"),  # 楷体
        (r"C:\Windows\Fonts\msyh.ttc", "Microsoft YaHei"),  # 微软雅黑
    ]

    registered_fonts = []
    for font_path, font_name in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                registered_fonts.append(font_name)
            except Exception as e:
                print(f"注册字体 {font_name} 失败: {e}")

    return registered_fonts


def draw_page_header(canvas_obj, doc):
    """绘制页眉：参考测试.pdf的格式（仅在第一页显示）"""
    # 只在第一页绘制抬头
    if doc.page > 1:
        return

    canvas_obj.saveState()

    page_width, page_height = A4

    # 标题：中 科 天 塔 竞 情 分 析 简 报（红色，在红线之上，字间距大，居中）
    canvas_obj.setFillColor(colors.red)
    canvas_obj.setFont("SimSun", 18)
    title = "中 科 天 塔 竞 情 分 析 简 报"
    title_width = canvas_obj.stringWidth(title, "SimSun", 18)
    title_x = (page_width - title_width) / 2
    title_y = page_height - 1.5 * cm
    canvas_obj.drawString(title_x, title_y, title)

    # 绘制两条红色横线（在标题下方）
    canvas_obj.setStrokeColor(colors.red)
    line1_y = title_y - 0.6 * cm
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(2 * cm, line1_y, page_width - 2 * cm, line1_y)

    line2_y = line1_y - 0.2 * cm
    canvas_obj.setLineWidth(1)
    canvas_obj.line(2 * cm, line2_y, page_width - 2 * cm, line2_y)

    # 设置黑色文字
    canvas_obj.setFillColor(colors.black)
    canvas_obj.setFont("SimSun", 11)

    # 第二行：密级和期数（左右分布）
    line2_y_pos = line2_y - 0.6 * cm

    # 左侧：密 级 ： 内 部 绝 密
    secret_text = "内 部 文 件 "
    canvas_obj.drawString(2 * cm, line2_y_pos, secret_text)

    # 右侧：期数信息（动态计算）
    # 锚点规则：2026-04-13 固定为第5期，后续每7天递增1期。
    import datetime

    anchor_date = datetime.date(2026, 4, 13)
    anchor_total_period = 5
    anchor_year_period = 5

    today = datetime.date.today()
    weeks_offset = (today - anchor_date).days // 7

    # 总第X期：以锚点为基准递增
    period_num = max(anchor_total_period, anchor_total_period + weeks_offset)

    # 2026年第X期：在2026年内与锚点规则保持一致；跨年后按自然年从1期重新计
    if today.year == anchor_date.year:
        year_period = max(anchor_year_period, anchor_year_period + weeks_offset)
    elif today.year > anchor_date.year:
        year_start = datetime.date(today.year, 1, 1)
        year_period = (today - year_start).days // 7 + 1
    else:
        year_period = 1
    year = today.year

    period_text = f"期数：{year}年第{year_period}期 (总第{period_num}期)"
    period_width = canvas_obj.stringWidth(period_text, "SimSun", 11)
    canvas_obj.drawString(page_width - 2 * cm - period_width, line2_y_pos, period_text)

    # 第三行：报送和日期（左右分布）
    line3_y_pos = line2_y_pos - 0.6 * cm

    # 左侧：报送
    report_to_text = "报送：公司决策委员会"
    canvas_obj.drawString(2 * cm, line3_y_pos, report_to_text)

    # 右侧：日期
    import datetime
    date_text = f"日期：{datetime.datetime.now().strftime('%Y年%m月%d日')}"
    date_width = canvas_obj.stringWidth(date_text, "SimSun", 11)
    canvas_obj.drawString(page_width - 2 * cm - date_width, line3_y_pos, date_text)

    canvas_obj.restoreState()


def create_custom_styles():
    """创建自定义样式 - 参考政府工作报告"""
    styles = getSampleStyleSheet()

    # 注册中文字体
    registered_fonts = register_chinese_fonts()
    base_font = registered_fonts[0] if registered_fonts else "Helvetica"

    # 标题样式（一级标题）- 使用较大字号
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontName=base_font,
        fontSize=22,  # 政府报告标题通常较大
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#000000'),
    ))

    # 二级标题样式
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontName=base_font,
        fontSize=16,  # 政府报告二级标题
        leading=22,
        alignment=TA_LEFT,
        spaceAfter=12,
        spaceBefore=12,
        textColor=colors.HexColor('#000000'),
    ))

    # 三级标题样式
    styles.add(ParagraphStyle(
        name='CustomHeading3',
        parent=styles['Heading3'],
        fontName=base_font,
        fontSize=14,  # 政府报告三级标题
        leading=20,
        alignment=TA_LEFT,
        spaceAfter=10,
        spaceBefore=10,
        textColor=colors.HexColor('#000000'),
    ))

    # 四级标题样式
    styles.add(ParagraphStyle(
        name='CustomHeading4',
        parent=styles['Heading4'],
        fontName=base_font,
        fontSize=12,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=8,
        spaceBefore=8,
        textColor=colors.HexColor('#000000'),
    ))

    # 正文样式 - 参考政府报告正文
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['BodyText'],
        fontName=base_font,
        fontSize=11,  # 政府报告正文字号
        leading=18,  # 行距
        alignment=TA_JUSTIFY,  # 两端对齐
        spaceAfter=8,
        firstLineIndent=22,  # 首行缩进2字符
        textColor=colors.HexColor('#000000'),
    ))

    # 列表样式
    styles.add(ParagraphStyle(
        name='CustomBullet',
        parent=styles['BodyText'],
        fontName=base_font,
        fontSize=11,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=6,
        leftIndent=20,
        textColor=colors.HexColor('#000000'),
    ))

    # 表格标题样式
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['BodyText'],
        fontName=base_font,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#FFFFFF'),
    ))

    return styles


def markdown_to_pdf_elements(markdown_text: str, styles):
    """将Markdown文本转换为PDF元素"""
    elements = []

    # 添加指令：从第二页开始使用Later模板（无抬头）
    elements.append(NextPageTemplate('Later'))

    lines = markdown_text.split('\n')

    i = 0
    first_h1_skipped = False  # 标志：是否已跳过第一个一级标题
    skip_explanation_21 = False  # 标志：是否跳过2.1节的说明段落
    skip_explanation_23 = False  # 标志：是否跳过2.3节的说明段落

    while i < len(lines):
        line = lines[i].strip()

        # 跳过空行
        if not line:
            elements.append(Spacer(1, 0.3*cm))
            i += 1
            continue

        # 一级标题 (# 标题)
        if line.startswith('# '):
            # 跳过第一个一级标题（与抬头重复）
            if not first_h1_skipped:
                first_h1_skipped = True
                i += 1
                continue

            title = line[2:].strip()
            # 移除emoji
            title = re.sub(r'[🛰️📊🏛️🚀🎯🏢⚠️📋📰📚]', '', title).strip()
            elements.append(Paragraph(title, styles['CustomTitle']))
            elements.append(Spacer(1, 0.5*cm))
            i += 1
            continue

        # 二级标题 (## 标题)
        if line.startswith('## '):
            title = line[3:].strip()
            title = re.sub(r'[🛰️📊🏛️🚀🎯🏢⚠️📋📰📚]', '', title).strip()

            # 检测是否是2.1或2.3节
            if '2.1' in title:
                skip_explanation_21 = True
            elif '2.3' in title:
                skip_explanation_23 = True
            else:
                skip_explanation_21 = False
                skip_explanation_23 = False

            elements.append(Paragraph(title, styles['CustomHeading2']))
            elements.append(Spacer(1, 0.3*cm))
            i += 1
            continue

        # 三级标题 (### 标题)
        if line.startswith('### '):
            title = line[4:].strip()
            title = re.sub(r'[🛰️📊🏛️🚀🎯🏢⚠️📋📰📚🌍💼]', '', title).strip()

            # 检测是否是2.1或2.3节
            if '2.1' in title:
                skip_explanation_21 = True
            elif '2.3' in title:
                skip_explanation_23 = True
            else:
                skip_explanation_21 = False
                skip_explanation_23 = False

            elements.append(Paragraph(title, styles['CustomHeading3']))
            elements.append(Spacer(1, 0.2*cm))
            i += 1
            continue

        # 四级标题 (#### 标题)
        if line.startswith('#### '):
            title = line[5:].strip()
            title = re.sub(r'[🛰️📊🏛️🚀🎯🏢⚠️📋📰📚]', '', title).strip()
            elements.append(Paragraph(title, styles['CustomHeading4']))
            elements.append(Spacer(1, 0.2*cm))
            i += 1
            continue

        # 分隔线 (---)
        if line.startswith('---'):
            elements.append(Spacer(1, 0.5*cm))
            i += 1
            continue

        # 列表项 (- 或 * 开头)
        if line.startswith('- ') or line.startswith('* '):
            bullet_text = line[2:].strip()
            # 移除markdown链接格式 [text](url)，但保留引用标记 [1] [2] 等
            bullet_text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1', bullet_text)
            # 移除加粗标记
            bullet_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', bullet_text)
            # 移除所有星号
            bullet_text = bullet_text.replace('*', '')
            elements.append(Paragraph(f"• {bullet_text}", styles['CustomBullet']))
            i += 1
            continue

        # 表格检测 (| 开头)
        if line.startswith('|'):
            # 收集表格行
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) > 2:  # 至少有表头、分隔线、数据行
                table_data = []
                for table_line in table_lines:
                    # 跳过分隔线
                    if re.match(r'\|[\s\-:]+\|', table_line):
                        continue
                    cells = [cell.strip() for cell in table_line.split('|')[1:-1]]
                    table_data.append(cells)

                if table_data:
                    # 创建表格 - 使用页面宽度
                    from reportlab.lib.pagesizes import A4
                    page_width = A4[0] - 4*cm  # 减去左右边距

                    # 将每个单元格内容转换为Paragraph对象以支持自动换行
                    table_data_with_paragraphs = []
                    cell_style = ParagraphStyle(
                        'TableCell',
                        parent=styles['Normal'],
                        fontName='SimSun',
                        fontSize=10,
                        leading=14,
                        alignment=0,  # 左对齐
                    )
                    for row in table_data:
                        paragraph_row = [Paragraph(cell, cell_style) for cell in row]
                        table_data_with_paragraphs.append(paragraph_row)

                    table = Table(table_data_with_paragraphs, colWidths=[page_width/len(table_data[0])]*len(table_data[0]))
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('FONTNAME', (0, 0), (-1, -1), 'SimSun'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 0.5*cm))
            continue

        # 普通段落
        # 移除markdown链接格式，但保留引用标记
        line = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1', line)
        # 移除加粗标记
        line = re.sub(r'\*\*([^\*]+)\*\*', r'\1', line)
        # 移除所有星号
        line = line.replace('*', '')
        # 移除(客户)和(竞争对手)标签
        line = re.sub(r'\(客户\)', '', line)
        line = re.sub(r'\(竞争对手\)', '', line)

        # 转换【】格式为"信号N:"格式
        # 匹配【信号1】、【信号2】等模式
        signal_match = re.match(r'【信号(\d+)】(.*)$', line)
        if signal_match:
            signal_num = signal_match.group(1)
            signal_content = signal_match.group(2).strip()
            if signal_content.startswith('：') or signal_content.startswith(':'):
                signal_content = signal_content[1:].strip()
            line = f'信号{signal_num}：{signal_content}'

        # 处理2.1和2.3节的说明段落跳过逻辑
        if skip_explanation_21 or skip_explanation_23:
            # 检查是否是编号项（如"1."、"2."等）
            if re.match(r'^\d+[\.、]', line):
                # 遇到编号项，清除跳过标志
                skip_explanation_21 = False
                skip_explanation_23 = False
            else:
                # 不是编号项，跳过这个段落
                i += 1
                continue

        # 跳过特定行
        if '--对中科天塔有影响的政策动向：--' in line:
            i += 1
            continue

        if line:
            elements.append(Paragraph(line, styles['CustomBody']))

        i += 1

    return elements


def generate_pdf_from_markdown(markdown_file: str, output_pdf: str) -> bool:
    """
    从Markdown文件生成PDF

    Args:
        markdown_file: Markdown文件路径
        output_pdf: 输出PDF文件路径

    Returns:
        bool: 是否成功生成
    """
    try:
        # 读取Markdown文件
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        # 先注册中文字体（确保HeaderCanvas可以使用）
        register_chinese_fonts()

        # 创建PDF文档（使用BaseDocTemplate以支持自定义页眉）
        doc = BaseDocTemplate(
            output_pdf,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,  # 默认顶部边距
            bottomMargin=2*cm,
        )

        # 创建两个页面模板：第一页有抬头，其他页面无抬头
        # 第一页模板（有抬头，需要更大的topMargin）
        frame_first = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height - 2*cm,  # 减少高度以容纳抬头
            id='first'
        )
        template_first = PageTemplate(id='First', frames=[frame_first], onPage=draw_page_header)

        # 其他页面模板（无抬头，正常topMargin）
        frame_later = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='later'
        )
        template_later = PageTemplate(id='Later', frames=[frame_later], onPage=draw_page_header)

        doc.addPageTemplates([template_first, template_later])

        # 创建样式
        styles = create_custom_styles()

        # 转换Markdown为PDF元素
        elements = markdown_to_pdf_elements(markdown_text, styles)

        # 生成PDF
        doc.build(elements)

        print(f"PDF生成成功: {output_pdf}")
        return True

    except Exception as e:
        print(f"PDF生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    sys.argv = ['1', 'D:\\Code\\tianta_ci\\output\\20260407_weekly\\天塔竞情战略周报.md', 'D:\\Code\\tianta_ci\\output\\20260407_weekly\\20260407_weekly.pdf']

    import os

    # 获取当前工作目录
    current_path = os.getcwd()

    # 支持命令行参数
    if len(sys.argv) >= 3:
        markdown_file = sys.argv[1]
        output_pdf = sys.argv[2]

        markdown_file = './output/20260419_weekly/天塔竞情战略周报(20260419).md'
        output_pdf = './output/20260419_weekly/天塔竞情战略周报(20260419).pdf'
        generate_pdf_from_markdown(markdown_file, output_pdf)
    else:
        # 测试代码
        test_md = """# 🛰️ 竞情半月报（2026.02.18 ~ 2026.03.05）

## 第一部分：政府政策内容

### 🏛️ 宏观政策面影响分析
--对中科天塔有影响的政策动向（3-5条）：--
- [政策1]：国家无线电管理机构 - 2025年底至2026年1月初集中申报20.3万颗卫星频轨资源
- [政策2]：工业和信息化部 - 新版《技术合同认定登记管理办法》自2026年3月1日起施行

---

## 第二部分：主要竞情目标分析

### 🎯 核心判断：平台围猎加剧
本周期监测显示，行业竞争态势发生结构性变化。

### 🏢 主要竞情目标动向分析（TOP5）

#### 一、长光卫星（客户）：重要客户流失风险
--关键动向：--
- 2026年2月20日重启IPO，估值145亿元
- 全面自建"吉星云"测运控平台

--可能对公司的影响：--
- 长光正从天塔的客户蜕变为直接竞对
"""

        generate_pdf_from_markdown("test.md", "test.pdf")

