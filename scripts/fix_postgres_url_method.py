#!/usr/bin/env python3
"""修复文档中的 postgres_url 属性为 get_postgres_url() 方法调用。"""

import re
from pathlib import Path


def fix_postgres_url_in_file(file_path: Path) -> bool:
    """修复文件中的 postgres_url 引用。

    Args:
        file_path: 文件路径

    Returns:
        是否进行了修改
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # 替换模式：config.postgres_url -> config.get_postgres_url()
    patterns = [
        # TokenStorageService(postgres_url=config.postgres_url)
        (
            r"TokenStorageService\(postgres_url=config\.postgres_url\)",
            "TokenStorageService(config.get_postgres_url())",
        ),
        # postgres_url=config.postgres_url
        (
            r"postgres_url=config\.postgres_url",
            "config.get_postgres_url()",
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

    # 查找所有包含 postgres_url 的 Markdown 文件
    md_files = list(docs_dir.rglob("*.md"))

    fixed_files = []
    for file_path in md_files:
        if fix_postgres_url_in_file(file_path):
            fixed_files.append(file_path)
            print(f"✅ 已修复: {file_path.relative_to(docs_dir.parent)}")

    if fixed_files:
        print(f"\n总计修复 {len(fixed_files)} 个文件")
    else:
        print("没有需要修复的文件")


if __name__ == "__main__":
    main()
