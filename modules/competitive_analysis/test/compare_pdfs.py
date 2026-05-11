#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对比两个PDF文件"""

import sys
from PyPDF2 import PdfReader

def compare_pdfs(pdf1_path, pdf2_path):
    """对比两个PDF文件"""
    try:
        reader1 = PdfReader(pdf1_path)
        reader2 = PdfReader(pdf2_path)

        output_file = "pdf_comparison.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"=== PDF对比分析 ===\n\n")

            f.write(f"【参考PDF】: {pdf1_path}\n")
            f.write(f"总页数: {len(reader1.pages)}\n")
            page1 = reader1.pages[0]
            text1 = page1.extract_text()
            f.write(f"第一页前800字符:\n{text1[:800]}\n\n")

            f.write(f"\n{'='*60}\n\n")

            f.write(f"【生成的PDF】: {pdf2_path}\n")
            f.write(f"总页数: {len(reader2.pages)}\n")
            page2 = reader2.pages[0]
            text2 = page2.extract_text()
            f.write(f"第一页前800字符:\n{text2[:800]}\n\n")

        print(f"对比结果已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"对比失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    pdf1 = "output/20260305_biweekly/测试.pdf"
    pdf2 = "output/20260305_biweekly/天塔竞情战略半月报_测试3.pdf"

    if len(sys.argv) >= 3:
        pdf1 = sys.argv[1]
        pdf2 = sys.argv[2]

    compare_pdfs(pdf1, pdf2)
