# aPaaS Integration Test Configuration Guide

## Overview

aPaaS (Application Platform as a Service) integration tests require **user-level access tokens** with elevated permissions, separate from standard integration tests. This guide explains how to securely configure and run aPaaS tests.

## Security Requirements

⚠️ **CRITICAL SECURITY NOTICE**

aPaaS operations require `user_access_token` (NOT `tenant_access_token`), which grants:
- User-level permissions to workspace data
- Access to sensitive data tables
- Ability to create/modify/delete records

**Security Best Practices:**
1. ✅ **NEVER** commit `.env.apaas` to version control
2. ✅ Store credentials in secure vault (password manager, secrets manager)
3. ✅ Use dedicated test workspace (NOT production workspace)
4. ✅ Rotate tokens regularly (recommended: every 30 days)
5. ✅ Grant minimum required permissions
6. ✅ Revoke tokens immediately after testing

## Configuration Steps

### 1. Create Configuration File

Copy the example file to create your configuration:

```bash
cp .env.apaas.example .env.apaas
```

### 2. Obtain User Access Token

aPaaS requires `user_access_token`. Obtain via Feishu Open Platform:

**Method 1: OAuth 2.0 Flow (Recommended)**
- Navigate to: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/authen-v1/authen/access_token
- Follow OAuth authorization flow
- Request scopes: `apaas:workspace.table:read`, `apaas:workspace.table:write`

**Method 2: Manual Token (Development Only)**
- Feishu Developer Console → Your App → Permissions & Scopes
- Grant aPaaS workspace permissions
- Generate user access token
- **Note:** Manual tokens expire quickly, use for development only

### 3. Configure Test Workspace

Create a dedicated test workspace:

1. Log in to Feishu aPaaS platform
2. Create new workspace: "Integration Test Workspace"
3. Create test table with fields:
   - Text field (e.g., "Name")
   - Number field (e.g., "Count")
   - Single select field (e.g., "Status")
4. Copy workspace ID (format: `ws_xxx`)
5. Copy table ID (format: `tbl_xxx`)

### 4. Fill Configuration File

Edit `.env.apaas`:

```bash
# Application Credentials
TEST_APAAS_APP_ID=cli_a1b2c3d4e5f6g7h8
TEST_APAAS_APP_SECRET=your_app_secret_here

# User Access Token
TEST_APAAS_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxxxxx

# Test Workspace and Table IDs
TEST_APAAS_WORKSPACE_ID=ws_a1b2c3d4e5f6g7h8
TEST_APAAS_TABLE_ID=tbl_a1b2c3d4e5f6g7h8
```

### 5. Verify Configuration

Check that `.env.apaas` is properly ignored by Git:

```bash
git status .env.apaas
# Should output: "nothing to commit" (file is ignored)
```

## Running Tests

### Run All aPaaS Integration Tests

```bash
pytest tests/integration/test_apaas_e2e.py -v
```

### Run Specific Test Classes

```bash
# Read operations only
pytest tests/integration/test_apaas_e2e.py::TestWorkspaceTableReadOperations -v

# Write operations only
pytest tests/integration/test_apaas_e2e.py::TestWorkspaceTableWriteOperations -v

# Batch operations only
pytest tests/integration/test_apaas_e2e.py::TestWorkspaceTableBatchOperations -v
```

### Skip aPaaS Tests

aPaaS tests are automatically skipped if:
- `.env.apaas` file does not exist
- Any required environment variable is missing
- Methods are not yet implemented (NotImplementedError)

## Test Coverage

### Current Status (Phase 5)

All tests are currently **skipped** because:
- WorkspaceTableClient methods are placeholder implementations
- Real API calls will be added in future phases

### Planned Test Scenarios

**Read Operations:**
- `test_list_workspace_tables` - List tables in workspace
- `test_list_fields` - Get field definitions
- `test_query_records_no_filter` - Query without filter
- `test_query_records_with_filter` - Query with filter expression

**Write Operations:**
- `test_create_and_delete_record` - Create and cleanup
- `test_update_record` - Update existing record

**Batch Operations:**
- `test_batch_create_records` - Batch create (5 records)
- `test_batch_update_records` - Batch update (3 records)

## Troubleshooting

### Error: "Missing aPaaS test configuration"

**Cause:** `.env.apaas` not found or incomplete

**Solution:**
```bash
# Check file exists
ls -la .env.apaas

# Verify all variables are set
grep TEST_APAAS .env.apaas
```

### Error: "Permission denied" or "403 Forbidden"

**Cause:** Insufficient permissions or expired token

**Solution:**
1. Verify token is `user_access_token` (NOT `tenant_access_token`)
2. Check token hasn't expired
3. Verify user has workspace permissions
4. Regenerate token if necessary

### Error: "Invalid workspace_id or table_id"

**Cause:** Incorrect ID format or non-existent resource

**Solution:**
1. Verify ID formats: `ws_xxx` for workspace, `tbl_xxx` for table
2. Check IDs exist in Feishu aPaaS platform
3. Ensure user has access to specified workspace/table

### Tests Still Skipped After Configuration

**Cause:** WorkspaceTableClient methods not yet implemented

**Solution:**
- This is expected behavior in Phase 5
- Methods are placeholder implementations (raise `NotImplementedError`)
- Real API implementation will be added in future phases
- Tests will automatically run once methods are implemented

## Security Checklist

Before running tests, verify:

- [ ] `.env.apaas` exists and is properly configured
- [ ] `.env.apaas` is in `.gitignore`
- [ ] Using dedicated test workspace (NOT production)
- [ ] Token has minimum required permissions
- [ ] Token expiration is monitored
- [ ] Backup credentials stored securely

After testing:

- [ ] Review test data created in workspace
- [ ] Clean up test records if necessary
- [ ] Rotate token if exposed or compromised
- [ ] Document any security incidents

## Related Documentation

- [aPaaS API Specification](../specs/001-lark-service-core/contracts/apaas.yaml)
- [Integration Test Guide](./integration-test-guide.md)
- [Feishu aPaaS Documentation](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/apaas-v1/workspace-table/list)

## Support

For issues or questions:
1. Check Feishu Open Platform documentation
2. Review test logs: `pytest tests/integration/test_apaas_e2e.py -v -s`
3. Verify token permissions in Feishu Developer Console
4. Contact Feishu Open Platform support if API issues persist
