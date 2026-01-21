# 监控指南

请参考 `docs/monitoring/` 目录中的监控文档。

## Prometheus 监控

- [Grafana 仪表板](../docs/monitoring/grafana-dashboard.json)
- [告警规则](../docs/monitoring/alert-rules.yaml)

## 关键指标

### WebSocket 连接
- `lark_service_websocket_connection_status`
- `lark_service_websocket_reconnect_total`

### 授权流程
- `lark_service_auth_session_total`
- `lark_service_auth_success_total`
- `lark_service_auth_failure_total`
- `lark_service_auth_duration_seconds`

### Token 管理
- `lark_service_token_refresh_total`
- `lark_service_token_active_count`
