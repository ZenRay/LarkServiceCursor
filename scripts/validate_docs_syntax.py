#!/usr/bin/env python3
"""
验证文档中 Python 代码示例的语法正确性

扫描文档目录中的 Markdown 文件,提取 Python 代码块并验证语法。
"""

import ast
import re
import sys
from pathlib import Path


def extract_python_blocks(markdown_file: Path) -> list[tuple[int, str]]:
    """从 Markdown 文件中提取 Python 代码块"""
    content = markdown_file.read_text(encoding="utf-8")
    pattern = r"```python\n(.*?)```"
    blocks = []

    for match in re.finditer(pattern, content, re.DOTALL):
        code = match.group(1)
        start_line = content[: match.start()].count("\n") + 1
        blocks.append((start_line, code))

    return blocks


def validate_syntax(code: str) -> tuple[bool, str]:
    """验证 Python 代码语法"""
    try:
        ast.parse(code)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


def main():
    """主函数"""
    docs_dir = Path("docs")
    total_files = 0
    total_blocks = 0
    failed_blocks = 0
    errors = []

    print("🔍 扫描文档目录:", docs_dir.absolute())
    print()

    # 扫描所有 Markdown 文件
    for md_file in sorted(docs_dir.rglob("*.md")):
        # 跳过 _build 目录
        if "_build" in str(md_file):
            continue

        blocks = extract_python_blocks(md_file)
        if not blocks:
            continue

        total_files += 1
        print(f"📄 {md_file.relative_to(docs_dir)}")

        for line_num, code in blocks:
            total_blocks += 1
            valid, msg = validate_syntax(code)

            if valid:
                print(f"  ✅ Line {line_num}: {msg}")
            else:
                print(f"  ❌ Line {line_num}: {msg}")
                failed_blocks += 1
                errors.append((md_file, line_num, msg))

        print()

    # 打印总结
    print("=" * 60)
    print("📊 验证总结:")
    print(f"  - 扫描文件数: {total_files}")
    print(f"  - 代码块总数: {total_blocks}")
    print(f"  - 通过验证: {total_blocks - failed_blocks}")
    print(f"  - 验证失败: {failed_blocks}")
    print("=" * 60)

    if failed_blocks > 0:
        print()
        print("❌ 发现语法错误:")
        for file, line, msg in errors:
            print(f"  {file.relative_to(docs_dir)}:{line} - {msg}")
        return 1

    print("✅ 所有代码块语法正确!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
