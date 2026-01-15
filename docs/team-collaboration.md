# 团队协作指南

**版本**: 1.0.0  
**更新时间**: 2026-01-15

---

## 多开发者配置同步 (CHK055)

### 配置文件管理策略

```
项目配置文件层次:
.env.example        → 提交到 Git (配置模板)
.env.development    → 提交到 Git (开发环境示例)
.env.production     → 不提交 (生产环境)
.env                → 不提交 (个人本地配置)
```

### 配置同步流程

**新成员入职**:
```bash
# 1. Clone 项目
git clone <repo-url>
cd lark-service

# 2. 复制配置模板
cp .env.example .env

# 3. 填充必需配置
# 编辑 .env 文件,设置个人密钥

# 4. 从团队密钥管理服务获取测试密钥
# (可选) 使用团队共享的开发环境密钥
```

**配置变更同步**:
```bash
# 开发者 A 添加新配置
echo "NEW_FEATURE_FLAG=true" >> .env.example

# 提交变更
git add .env.example
git commit -m "feat: add NEW_FEATURE_FLAG config"
git push

# 开发者 B 同步
git pull
# 手动添加到个人 .env 文件
echo "NEW_FEATURE_FLAG=true" >> .env
```

## 第三方库封装 (CHK125)

### 封装策略

**问题**: 直接使用第三方库,版本升级可能破坏代码

**解决**: 封装第三方库,隔离版本变更影响

**示例**:
```python
# ❌ 直接使用 (耦合严重)
from lark_oapi import Client
client = Client.builder().build()

# ✅ 封装后使用
from lark_service.core.lark_client import LarkClient
client = LarkClient(config)
```

### 封装模式

```python
# src/lark_service/core/lark_client.py
from lark_oapi import Client as LarkOapiClient

class LarkClient:
    """Wrapper for lark-oapi SDK.
    
    隔离 lark-oapi 版本变更的影响。
    """
    def __init__(self, app_id: str, app_secret: str):
        self._client = LarkOapiClient.builder()\\
            .app_id(app_id)\\
            .app_secret(app_secret)\\
            .build()
    
    def fetch_app_token(self) -> str:
        """Fetch app access token.
        
        如果 SDK API 变更,仅需修改此方法。
        """
        req = self._client.auth.v3.app_access_token.internal\\
            .create()
        resp = req.do()
        
        if resp.code != 0:
            raise APIError(f"Failed: {resp.msg}")
        
        return resp.data.app_access_token
```

---

**维护者**: Lark Service Team
