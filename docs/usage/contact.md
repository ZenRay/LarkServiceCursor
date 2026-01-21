# 通讯录服务

## 应用管理

LarkService 支持多应用管理和灵活的应用切换。详细信息请参考 [应用管理文档](app-management.md)。

### 快速示例

```python
from pathlib import Path

from lark_service.core.config import Config
from lark_service.core.credential_pool import CredentialPool
from lark_service.core.storage.sqlite_storage import ApplicationManager, TokenStorageService

# 初始化
config = Config()
app_manager = ApplicationManager(db_path="data/applications.db")
token_storage = TokenStorageService(db_path="data/tokens.db")
credential_pool = CredentialPool(
    config=config,
    app_manager=app_manager,
    token_storage=token_storage,
    lock_dir=Path("data/locks")
)

# 添加应用
app_manager.add_application(
    app_id="cli_your_app_id_here",
    app_secret="your_app_secret_min_16_chars_required",
    description="我的应用"
)

# 使用工厂方法创建客户端
client = credential_pool.create_contact_client(app_id="cli_your_app_id_here")

# 使用上下文管理器临时切换应用
with client.use_app("cli_another_app_id"):
    # 在此代码块内使用另一个应用
    pass

# 方法参数覆盖 (最高优先级)
# result = client.some_method(..., app_id="cli_override_app")
```

更多应用管理功能:
- [5层 app_id 解析优先级](app-management.md#5层-app_id-解析优先级)
- [多应用场景](app-management.md#场景-2-多应用场景---客户端级别默认值)
- [动态切换应用](app-management.md#场景-3-动态切换应用---使用上下文管理器)
- [高级用法](advanced.md)
