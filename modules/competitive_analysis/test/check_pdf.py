#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查PDF文件的内容和格式"""

import sys
import os
from PyPDF2 import PdfReader

def analyze_pdf(pdf_path):
    """分析PDF文件"""
    try:
        reader = PdfReader(pdf_path)

        # 写入文件而不是打印到控制台
        output_file = "pdf_analysis.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"\n=== PDF文件分析: {pdf_path} ===\n")
            f.write(f"总页数: {len(reader.pages)}\n")
            f.write(f"PDF版本: {reader.pdf_header}\n")

            # 获取第一页
            first_page = reader.pages[0]
            f.write(f"\n第一页尺寸: {first_page.mediabox.width} x {first_page.mediabox.height}\n")

            # 提取文本
            text = first_page.extract_text()
            f.write(f"\n第一页文本内容:\n")
            f.write(text)
            f.write("\n\n")

            # 检查所有页面
            for i, page in enumerate(reader.pages, 1):
                f.write(f"\n--- 第{i}页 ---\n")
                page_text = page.extract_text()
                f.write(page_text[:200] + "...\n")

        print(f"分析结果已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "output/20260305_biweekly/测试.pdf"

    analyze_pdf(pdf_path)
