#!/usr/bin/env python3
"""
从crew_raw_output.txt提取报告并生成PDF
"""
import re
import os
from utils.pdf_generator import generate_pdf_from_markdown

def extract_main_report(raw_output: str) -> str:
    """从原始输出中提取主报告"""
    # 尝试匹配主报告 - 使用更宽松的空白字符匹配
    # 注意：crew_raw_output.txt第一行末尾可能有额外空格
    main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*?)\s*===\s*主报告结束\s*===", raw_output, re.S)

    if main_report_match:
        return main_report_match.group(1).strip()

    # 如果没有找到结束标记，尝试从开始标记到文件末尾
    main_report_match = re.search(r"===\s*主报告开始\s*===\s*(.*)", raw_output, re.S)
    if main_report_match:
        content = main_report_match.group(1).strip()
        # 移除可能的其他备份文件标记
        content = re.sub(r"===\s*商业航天测运控备份文件开始\s*===.*", "", content, flags=re.S)
        content = re.sub(r"===\s*激光通讯终端备份文件开始\s*===.*", "", content, flags=re.S)
        content = re.sub(r"===\s*汇总备份文件开始\s*===.*", "", content, flags=re.S)
        return content.strip()

    return None

def main():
    # 读取crew_raw_output.txt
    output_dir = "output/20260313_biweekly"
    raw_output_path = os.path.join(output_dir, "crew_raw_output.txt")

    print(f"正在读取: {raw_output_path}")
    with open(raw_output_path, 'r', encoding='utf-8') as f:
        raw_output = f.read()

    print(f"原始输出长度: {len(raw_output)} 字符")

    # 提取主报告
    main_report = extract_main_report(raw_output)

    if main_report:
        print(f"成功提取主报告，长度: {len(main_report)} 字符")

        # 保存到天塔竞情战略半月报.md
        md_path = os.path.join(output_dir, "天塔竞情战略半月报.md")
        print(f"正在保存到: {md_path}")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(main_report)

        # 生成PDF
        pdf_path = os.path.join(output_dir, "W11_20260313.pdf")
        print(f"正在生成PDF: {pdf_path}")
        success = generate_pdf_from_markdown(md_path, pdf_path)

        if success:
            print(f"PDF generated successfully: {pdf_path}")
        else:
            print("PDF generation failed")
    else:
        print("Failed to extract main report")
        # Don't print raw output to avoid encoding issues

if __name__ == "__main__":
    main()
