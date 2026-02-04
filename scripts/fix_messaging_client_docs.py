#!/usr/bin/env python3
"""修复文档中的 MessagingClient 初始化参数。"""

import re
from pathlib import Path


def fix_messaging_client_in_file(file_path: Path) -> bool:
    """修复文件中的 MessagingClient 初始化。

    Args:
        file_path: 文件路径

    Returns:
        是否进行了修改
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # 替换模式：MessagingClient(pool=credential_pool) -> MessagingClient(credential_pool)
    patterns = [
        (
            r"MessagingClient\(pool=credential_pool\)",
            "MessagingClient(credential_pool)",
        ),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    """主函数。"""
    docs_dir = Path(__file__).parent.parent / "docs"

    # 查找所有 Markdown 文件
    md_files = list(docs_dir.rglob("*.md"))

    fixed_files = []
    for file_path in md_files:
        if fix_messaging_client_in_file(file_path):
            fixed_files.append(file_path)
            print(f"✅ 已修复: {file_path.relative_to(docs_dir.parent)}")

    if fixed_files:
        print(f"\n总计修复 {len(fixed_files)} 个文件")
    else:
        print("没有需要修复的文件")


if __name__ == "__main__":
    main()
