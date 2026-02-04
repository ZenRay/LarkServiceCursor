#!/usr/bin/env python3
"""修复文档中的 CardBuilder 使用方式。"""

import re
from pathlib import Path


def fix_card_builder_in_file(file_path: Path) -> bool:
    """修复文件中的 CardBuilder 使用。

    Args:
        file_path: 文件路径

    Returns:
        是否进行了修改
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # 替换模式：链式调用 -> build_notification_card 方法
    old_pattern = r"""# 创建卡片
card = CardBuilder\(\) \\
    \.add_header\("欢迎使用 Lark Service", color="blue"\) \\
    \.add_text\("这是一条交互式卡片消息"\) \\
    \.add_button\("点击我", value=\{"action": "click"\}\) \\
    \.build\(\)"""

    new_pattern = """# 创建通知卡片
card = CardBuilder().build_notification_card(
    title="欢迎使用 Lark Service",
    content="这是一条交互式卡片消息，支持 **Markdown** 格式！",
    level="info",
    action_text="查看详情",
    action_url="https://example.com"
)"""

    content = re.sub(old_pattern, new_pattern, content)

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
        if fix_card_builder_in_file(file_path):
            fixed_files.append(file_path)
            print(f"✅ 已修复: {file_path.relative_to(docs_dir.parent)}")

    if fixed_files:
        print(f"\n总计修复 {len(fixed_files)} 个文件")
    else:
        print("没有需要修复的文件")


if __name__ == "__main__":
    main()
