#!/usr/bin/env python3
"""
文档代码示例验证脚本

自动提取并验证文档中的 Python 代码示例
"""

import ast
import re
import sys
from pathlib import Path


def extract_python_blocks(md_file: Path) -> list[tuple[int, str]]:
    """提取 Markdown 文件中的 Python 代码块"""
    content = md_file.read_text(encoding="utf-8")
    blocks = []

    # 匹配 ```python ... ``` 代码块
    pattern = r"```python\n(.*?)\n```"
    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        code = match.group(1)
        line_num = content[: match.start()].count("\n") + 1
        blocks.append((line_num, code))

    return blocks


def check_imports(code: str) -> list[str]:
    """检查代码中的导入语句是否有效"""
    errors = []

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module
                if module and module.startswith("lark_service"):
                    # 检查已知的错误导入
                    for alias in node.names:
                        name = alias.name

                        # 错误 1: token_storage 模块不存在
                        if (
                            "token_storage" in module
                            and module != "lark_service.core.storage.postgres_storage"
                        ):
                            errors.append(
                                f"❌ 错误导入: {module}.{name} (应该从 lark_service.core.storage 或 postgres_storage 导入)"
                            )

                        # 错误 2: 直接从子模块导入应该从 __init__ 导入的类
                        if name in ["ApplicationManager", "TokenStorageService"] and module not in [
                            "lark_service.core.storage",
                            "lark_service.core.storage.sqlite_storage",
                            "lark_service.core.storage.postgres_storage",
                        ]:
                            errors.append(
                                f"❌ 错误导入: {name} from {module} (应该从 lark_service.core.storage 导入)"
                            )

    except SyntaxError as e:
        errors.append(f"⚠️  语法错误: {e}")

    return errors


def validate_document(doc_path: Path) -> dict:
    """验证单个文档"""
    result = {"file": str(doc_path), "blocks": 0, "errors": []}

    blocks = extract_python_blocks(doc_path)
    result["blocks"] = len(blocks)

    for line_num, code in blocks:
        errors = check_imports(code)
        if errors:
            result["errors"].append(
                {
                    "line": line_num,
                    "errors": errors,
                    "code_preview": code[:100] + "..." if len(code) > 100 else code,
                }
            )

    return result


def main():
    """主函数"""
    docs_dir = Path(__file__).parent.parent / "docs"

    # 要验证的文档列表
    priority_docs = [
        "quickstart.md",
        "installation.md",
        "api-examples.md",
        "usage/app-management.md",
        "usage/messaging.md",
        "usage/card.md",
        "usage/contact.md",
        "usage/clouddoc.md",
        "usage/auth.md",
        "usage/scheduler.md",
    ]

    print("🔍 开始验证文档代码示例...\n")

    total_files = 0
    total_blocks = 0
    files_with_errors = 0

    for doc_rel_path in priority_docs:
        doc_path = docs_dir / doc_rel_path
        if not doc_path.exists():
            print(f"⚠️  文件不存在: {doc_rel_path}")
            continue

        result = validate_document(doc_path)
        total_files += 1
        total_blocks += result["blocks"]

        if result["errors"]:
            files_with_errors += 1
            print(f"❌ {doc_rel_path}")
            print(f"   发现 {len(result['errors'])} 个代码块有问题:\n")

            for error_info in result["errors"]:
                print(f"   行 {error_info['line']}:")
                for err in error_info["errors"]:
                    print(f"      {err}")
                print()
        else:
            print(f"✅ {doc_rel_path} - {result['blocks']} 个代码块")

    print(f"\n{'=' * 60}")
    print("验证完成:")
    print(f"  总文件数: {total_files}")
    print(f"  总代码块: {total_blocks}")
    print(f"  有错误的文件: {files_with_errors}")
    print(f"{'=' * 60}\n")

    return 0 if files_with_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
