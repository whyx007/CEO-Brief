#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查PDF每一页的内容"""

import sys
from PyPDF2 import PdfReader

def check_all_pages(pdf_path):
    """检查PDF所有页面"""
    try:
        reader = PdfReader(pdf_path)

        output_file = "pdf_pages_check.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"=== PDF页面检查: {pdf_path} ===\n")
            f.write(f"总页数: {len(reader.pages)}\n\n")

            # 检查每一页
            for i, page in enumerate(reader.pages, 1):
                f.write(f"\n{'='*60}\n")
                f.write(f"第{i}页内容（前300字符）:\n")
                f.write(f"{'='*60}\n")
                page_text = page.extract_text()
                f.write(page_text[:300] + "\n")

        print(f"检查结果已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "output/20260305_biweekly/天塔竞情战略半月报_最终版.pdf"

    check_all_pages(pdf_path)
