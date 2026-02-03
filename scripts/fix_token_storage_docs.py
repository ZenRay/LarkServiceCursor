#!/usr/bin/env python3
"""修复文档中 TokenStorageService 的初始化参数"""

import re
from pathlib import Path

# 需要修复的文件列表
docs_to_fix = [
    "docs/quickstart.md",
    "docs/DOC_TESTING_GUIDE.md",
    "docs/usage/advanced.md",
    "docs/usage/apaas.md",
    "docs/usage/app-management.md",
    "docs/usage/auth.md",
    "docs/usage/card.md",
    "docs/usage/clouddoc.md",
    "docs/usage/contact.md",
    "docs/usage/messaging.md",
    "docs/usage/scheduler.md",
]

# 替换模式
patterns = [
    (
        r"token_storage = TokenStorageService\(db_path=config\.config_db_path\)",
        "token_storage = TokenStorageService(postgres_url=config.postgres_url)",
    ),
    (
        r'token_storage = TokenStorageService\(db_path="data/tokens\.db"\)',
        "token_storage = TokenStorageService(postgres_url=config.postgres_url)",
    ),
    (
        r"ts = TokenStorageService\(db_path=config\.config_db_path\)",
        "ts = TokenStorageService(postgres_url=config.postgres_url)",
    ),
]


def fix_file(file_path: Path) -> bool:
    """修复单个文件"""
    if not file_path.exists():
        return False

    content = file_path.read_text(encoding="utf-8")
    original_content = content

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


# 执行修复
root = Path(__file__).parent.parent
fixed_count = 0

for doc_path in docs_to_fix:
    file_path = root / doc_path
    if fix_file(file_path):
        print(f"✅ 已修复: {doc_path}")
        fixed_count += 1
    elif file_path.exists():
        print(f"⏭️  跳过: {doc_path} (无需修改)")
    else:
        print(f"⚠️  未找到: {doc_path}")

print(f"\n总计修复 {fixed_count} 个文件")
