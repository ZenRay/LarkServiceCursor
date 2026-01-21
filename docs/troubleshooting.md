# 故障排查

请参考 `docs/error-recovery-guide.md` 中的详细故障排查指南。

## 常见问题

### 数据库连接失败

```bash
# 检查 PostgreSQL 服务
docker compose ps postgres

# 查看日志
docker compose logs postgres
```

### Token 获取失败

```bash
# 检查应用配置
lark-service-cli app list

# 验证 app_id 和 app_secret
lark-service-cli app show --app-id cli_xxx
```

### OAuth 回调失败

- 检查 `OAUTH_REDIRECT_URI` 配置
- 确认飞书开发者后台配置的重定向 URL
- 验证回调服务器是否运行：`curl http://localhost:8000/callback?code=test&state=test`
