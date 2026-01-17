# GitHub Actions 测试失败问题报告

**日期**: 2026-01-17
**影响范围**: Messaging 和 CardKit 模块集成测试
**严重程度**: 中等 (不影响 Phase 5 aPaaS 功能)

---

## 📊 问题概述

GitHub Actions 中有 **21 个集成测试失败**，分为两类问题：

### 1. Lambda 函数参数错误 (19 个失败) ❌

**错误信息**:
```
TypeError: ....<lambda>() got an unexpected keyword argument 'operation_name'
```

**根本原因**:
`RetryStrategy.execute()` 方法将 `**kwargs` 传递给 lambda 函数，但这些 lambda 没有接收 `**kwargs`。

**受影响的模块**:
- `src/lark_service/messaging/client.py` - MessagingClient._send_message
- `src/lark_service/messaging/lifecycle.py` - MessageLifecycleManager (recall/edit/reply)
- `src/lark_service/cardkit/updater.py` - CardUpdater.update_card_content

**失败的测试**:
1. `test_send_text_message_integration` ❌
2. `test_send_rich_text_message_integration` ❌
3. `test_send_image_message_with_key_integration` ❌
4. `test_send_file_message_with_key_integration` ❌
5. `test_send_card_message_integration` ❌
6. `test_batch_send_messages_integration` ❌
7. `test_batch_send_with_partial_failure_integration` ❌
8. `test_recall_message_integration` ❌
9. `test_edit_message_integration` ❌
10. `test_reply_message_integration` ❌
11. `test_update_card_content_integration` ❌
12. `test_build_send_and_update_card_scenario` ❌
13. `test_send_message_and_recall_scenario` ❌
14. `test_send_message_and_edit_scenario` ❌
15. `test_send_message_and_reply_scenario` ❌
16. `test_batch_send_to_multiple_users_scenario` ❌

**典型错误栈**:
```python
src/lark_service/messaging/client.py:136: in _send_message
    response = self.retry_strategy.execute(
src/lark_service/core/retry.py:119: in execute
    result = func(*args, **kwargs)
               ^^^^^^^^^^^^^^^^^^^^^
E   TypeError: MessagingClient._send_message.<locals>.<lambda>() got an unexpected keyword argument 'operation_name'
```

---

### 2. Masking 工具测试失败 (5 个失败) ❌

**受影响的文件**: `src/lark_service/utils/masking.py`

**失败的测试**:
1. `test_mask_short_email` - 期望 `"ab***@cd***.com"`，实际 `"a***@c***.com"`
2. `test_mask_invalid_email` - 期望 `"***"`，实际 `"***@***.***"`
3. `test_mask_short_mobile` - 期望 `"1***5"`，实际 `"123***45"`
4. `test_mask_normal_token` - 期望 `"cli_***7h8"`，实际 `"cli_***g7h8"`
5. `test_mask_multiple_sensitive_data` - token 未被正确掩码

**根本原因**:
Masking 函数的实现逻辑与测试用例的预期不一致。

---

## 🔍 修复建议

### 修复 1: Lambda 参数问题

**方案 A**: 修改 lambda 函数接收 `**kwargs`

```python
# 当前代码 (错误)
lambda: make_api_call()

# 修复后
lambda **kwargs: make_api_call()
```

**方案 B**: 不在 retry_strategy.execute() 中传递额外的 kwargs

移除 `operation_name` 参数，或者不通过 `**kwargs` 传递。

**影响范围**:
- `src/lark_service/messaging/client.py`
- `src/lark_service/messaging/lifecycle.py`
- `src/lark_service/cardkit/updater.py`

---

### 修复 2: Masking 函数

需要审查 `src/lark_service/utils/masking.py` 的实现，确保与测试用例预期一致。

或者，如果实现是正确的，需要更新测试用例。

---

## 📈 测试统计

| 类别 | 总数 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 总计 | 457 | 353 | 21 | 83 |
| **通过率** | | **77.2%** | **4.6%** | **18.2%** |

### 模块级统计

| 模块 | 通过 | 失败 | 跳过 |
|------|------|------|------|
| aPaaS (Phase 5) | 30 | 0 | 9 |
| Messaging | 4 | 16 | 0 |
| CardKit | 8 | 2 | 0 |
| Masking Utils | 15 | 5 | 0 |
| 其他 | 296 | 0 | 74 |

---

## ⚠️ 重要说明

### 不影响 Phase 5

✅ **Phase 5 aPaaS 相关测试全部通过**:
- 30 个单元测试通过
- 合约测试全部通过
- 集成测试因配置原因跳过（正常）

### 不影响代码质量工具

✅ **本次修改的代码质量工具运行正常**:
- `git check` ✅
- `git cadd` ✅
- `git csync` ✅
- src/ 代码 100% 通过 mypy --strict

---

## 🎯 行动建议

### 优先级

1. **高优先级**: 修复 Lambda 参数问题（影响 16 个测试）
2. **中优先级**: 修复 Masking 工具问题（影响 5 个测试）
3. **低优先级**: 优化跳过的集成测试配置

### 时间估算

- Lambda 问题修复: 1-2 小时
- Masking 问题修复: 30分钟 - 1小时
- 总计: 约 2-3 小时

---

## 📚 相关文件

- `src/lark_service/core/retry.py` - RetryStrategy 实现
- `src/lark_service/messaging/client.py` - MessagingClient
- `src/lark_service/messaging/lifecycle.py` - MessageLifecycleManager
- `src/lark_service/cardkit/updater.py` - CardUpdater
- `src/lark_service/utils/masking.py` - Masking utilities
- `tests/integration/test_messaging_integration.py` - 失败的测试
- `tests/integration/test_cardkit_integration.py` - 失败的测试
- `tests/unit/utils/test_masking.py` - 失败的测试

---

## 🔗 相关提交

这些问题**不是由今天的修改引入的**，是历史遗留问题：

- Phase 5 代码质量修复: `1b60a7c`
- 暂存区同步修复: `af2d450`
- 代码质量工具: `676fb2d`

---

**创建时间**: 2026-01-17
**创建人**: AI Assistant
**状态**: 待修复
**标签**: bug, messaging, cardkit, testing
