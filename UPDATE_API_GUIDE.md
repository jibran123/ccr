# UPDATE API Guide

Complete guide for updating API deployments in the CCR API Manager.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Endpoints](#endpoints)
3. [Full Update (PUT)](#full-update-put)
4. [Partial Update (PATCH)](#partial-update-patch)
5. [Status Update](#status-update)
6. [Properties Update](#properties-update)
7. [Get Deployment](#get-deployment)
8. [Delete Deployment](#delete-deployment)
9. [Best Practices](#best-practices)
10. [Examples](#examples)

---

## Overview

The UPDATE API provides multiple ways to modify existing deployments:

- **Full Update (PUT)**: Replace entire deployment
- **Partial Update (PATCH)**: Update specific fields
- **Status Update**: Change only the status
- **Properties Update**: Modify properties without affecting status
- **Delete**: Remove a deployment

All updates are **idempotent** - running the same update multiple times produces the same result.

---

## Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `PUT` | `/api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}` | Full update |
| `PATCH` | `/api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}` | Partial update |
| `PATCH` | `/api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/status` | Status only |
| `PATCH` | `/api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/properties` | Properties only |
| `GET` | `/api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}` | Get details |
| `DELETE` | `/api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}` | Delete deployment |

---

## Full Update (PUT)

**Replace the entire deployment** with new values.

### Endpoint
```
PUT /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
```

### Request Body
```json
{
  "status": "RUNNING",
  "updated_by": "john.doe",
  "properties": {
    "api.id": "12345",
    "version": "2.0.0",
    "endpoint": "https://api.example.com"
  }
}
```

### Required Fields
- `status` - Must be valid status from config
- `updated_by` - User making the update
- `properties` - Complete properties object (replaces old properties)

### Example
```bash
curl -X PUT http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst \
  -H "Content-Type: application/json" \
  -d '{
    "status": "RUNNING",
    "updated_by": "admin",
    "properties": {
      "version": "2.0.0",
      "replicas": "3"
    }
  }'
```

### Response
```json
{
  "status": "success",
  "message": "Updated deployment for my-api on IP4/tst",
  "data": {
    "api_name": "my-api",
    "platform": "IP4",
    "environment": "tst",
    "action": "updated"
  }
}
```

### Use Cases
- Replacing configuration completely
- Major version upgrades
- Resetting to known state

---

## Partial Update (PATCH)

**Update only specified fields**, keeping others unchanged.

### Endpoint
```
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
```

### Request Body
```json
{
  "status": "STOPPED",
  "updated_by": "operator",
  "properties": {
    "debug": "true"
  }
}
```

### Optional Fields
- `status` - Update status
- `updated_by` - Update user
- `properties` - **Merge** with existing properties

### Example: Update Status Only
```bash
curl -X PATCH http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst \
  -H "Content-Type: application/json" \
  -d '{
    "status": "MAINTENANCE",
    "updated_by": "admin"
  }'
```

### Example: Add Properties
```bash
curl -X PATCH http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst \
  -H "Content-Type: application/json" \
  -d '{
    "updated_by": "developer",
    "properties": {
      "feature.flag": "enabled",
      "cache.ttl": "3600"
    }
  }'
```

### Response
```json
{
  "status": "success",
  "message": "Partially updated deployment for my-api on IP4/tst",
  "data": {
    "api_name": "my-api",
    "platform": "IP4",
    "environment": "tst",
    "action": "updated",
    "modified_fields": ["status", "properties"]
  }
}
```

### Use Cases
- Status changes
- Adding new properties
- Incremental configuration updates

---

## Status Update

**Quick status changes** without touching properties.

### Endpoint
```
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/status
```

### Request Body
```json
{
  "status": "RUNNING",
  "updated_by": "monitoring-system"
}
```

### Required Fields
- `status` - New status
- `updated_by` - User making the change

### Example
```bash
curl -X PATCH http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "STOPPED",
    "updated_by": "operator"
  }'
```

### Response
```json
{
  "status": "success",
  "message": "Partially updated deployment for my-api on IP4/tst",
  "data": {
    "api_name": "my-api",
    "platform": "IP4",
    "environment": "tst",
    "new_status": "STOPPED"
  }
}
```

### Use Cases
- Service health updates
- Automated monitoring
- Start/stop operations

---

## Properties Update

**Update configuration** without changing status.

### Endpoint
```
PATCH /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}/properties
```

### Request Body
```json
{
  "updated_by": "config-manager",
  "properties": {
    "version": "2.1.0",
    "feature.new": "enabled"
  }
}
```

### Required Fields
- `updated_by` - User making the change
- `properties` - Properties to add/update (**merges** with existing)

### Example
```bash
curl -X PATCH http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst/properties \
  -H "Content-Type: application/json" \
  -d '{
    "updated_by": "developer",
    "properties": {
      "version": "2.1.0",
      "cache.enabled": "true",
      "debug.mode": "false"
    }
  }'
```

### Response
```json
{
  "status": "success",
  "message": "Partially updated deployment for my-api on IP4/tst",
  "data": {
    "api_name": "my-api",
    "platform": "IP4",
    "environment": "tst",
    "updated_properties": ["version", "cache.enabled", "debug.mode"]
  }
}
```

### Property Merging Behavior
- **Existing properties are preserved**
- **New properties are added**
- **Specified properties are updated**
- Status and timestamps remain unchanged

### Use Cases
- Configuration changes
- Feature flag updates
- Version updates

---

## Get Deployment

**Retrieve current deployment details**.

### Endpoint
```
GET /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
```

### Example
```bash
curl http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst
```

### Response
```json
{
  "status": "success",
  "data": {
    "api_name": "my-api",
    "platform": "IP4",
    "environment": "tst",
    "status": "RUNNING",
    "deployment_date": "2025-10-01T10:00:00Z",
    "last_updated": "2025-10-01T12:30:00Z",
    "updated_by": "admin",
    "properties": {
      "api.id": "12345",
      "version": "2.1.0",
      "cache.enabled": "true"
    }
  }
}
```

### Use Cases
- Checking current state
- Verifying updates
- Configuration audits

---

## Delete Deployment

**Remove a specific deployment**.

### Endpoint
```
DELETE /api/apis/{api_name}/platforms/{platform_id}/environments/{env_id}
```

### Example
```bash
curl -X DELETE http://localhost:5000/api/apis/my-api/platforms/IP4/environments/tst
```

### Response
```json
{
  "status": "success",
  "message": "Deleted deployment my-api on IP4/tst",
  "data": {
    "api_name": "my-api",
    "platform": "IP4",
    "environment": "tst",
    "action": "deleted"
  }
}
```

### Automatic Cleanup
- If platform has no more environments → **Platform is removed**
- If API has no more deployments → **API is removed**

### Example: Last Deployment
```json
{
  "status": "success",
  "message": "Deleted last deployment for my-api - API removed",
  "data": {
    "action": "deleted_api"
  }
}
```

### Use Cases
- Decommissioning environments
- Cleanup after testing
- Removing obsolete deployments

---

## Best Practices

### 1. Choose the Right Update Method

| Scenario | Method | Endpoint |
|----------|--------|----------|
| Complete replacement | `PUT` | Full update |
| Status change only | `PATCH` | `/status` |
| Add/update properties | `PATCH` | `/properties` |
| Multiple field updates | `PATCH` | Base endpoint |

### 2. Partial Updates Over Full Updates
✅ **Do**: Use PATCH for incremental changes
```bash
# Good - preserves other properties
PATCH /properties { "version": "2.0" }
```

❌ **Don't**: Use PUT unless replacing everything
```bash
# Bad - loses other properties
PUT / { "status": "RUNNING", "properties": {"version": "2.0"} }
```

### 3. Always Include `updated_by`
```json
{
  "status": "RUNNING",
  "updated_by": "john.doe"  // ✅ Good - tracks who made the change
}
```

### 4. Verify Updates
```bash
# Update
curl -X PATCH .../status -d '{"status": "RUNNING", "updated_by": "admin"}'

# Verify
curl .../  # Check the result
```

### 5. Handle Errors Gracefully
```bash
response=$(curl -X PATCH ... -d '...')
if [[ $(echo $response | jq -r '.status') == "error" ]]; then
  echo "Update failed: $(echo $response | jq -r '.message')"
fi
```

---

## Examples

### Example 1: Rolling Update
```bash
# 1. Deploy new version to TST
curl -X POST http://localhost:5000/api/deploy \
  -d '{
    "api_name": "user-service",
    "platform_id": "IP4",
    "environment_id": "tst",
    "status": "DEPLOYING",
    "updated_by": "ci-cd",
    "properties": {"version": "2.0.0"}
  }'

# 2. Test and promote to PRD
curl -X POST http://localhost:5000/api/deploy \
  -d '{
    "api_name": "user-service",
    "platform_id": "IP4",
    "environment_id": "prd",
    "status": "DEPLOYING",
    "updated_by": "release-manager",
    "properties": {"version": "2.0.0"}
  }'

# 3. Update status after deployment
curl -X PATCH http://localhost:5000/api/apis/user-service/platforms/IP4/environments/prd/status \
  -d '{"status": "RUNNING", "updated_by": "ci-cd"}'
```

### Example 2: Feature Flag Management
```bash
# Enable feature flag
curl -X PATCH http://localhost:5000/api/apis/user-service/platforms/IP4/environments/prd/properties \
  -d '{
    "updated_by": "feature-manager",
    "properties": {
      "feature.new_ui": "enabled",
      "feature.rollout_percentage": "10"
    }
  }'

# Increase rollout
curl -X PATCH .../properties \
  -d '{
    "updated_by": "feature-manager",
    "properties": {
      "feature.rollout_percentage": "50"
    }
  }'

# Full rollout
curl -X PATCH .../properties \
  -d '{
    "updated_by": "feature-manager",
    "properties": {
      "feature.rollout_percentage": "100"
    }
  }'
```

### Example 3: Maintenance Window
```bash
# Start maintenance
curl -X PATCH .../status \
  -d '{"status": "MAINTENANCE", "updated_by": "ops-team"}'

# Add maintenance note
curl -X PATCH .../properties \
  -d '{
    "updated_by": "ops-team",
    "properties": {
      "maintenance.reason": "database upgrade",
      "maintenance.end": "2025-10-01T14:00:00Z"
    }
  }'

# End maintenance
curl -X PATCH .../status \
  -d '{"status": "RUNNING", "updated_by": "ops-team"}'
```

### Example 4: Bulk Status Update
```bash
#!/bin/bash
# Stop all services on IP4/tst for maintenance

APIS=("api-1" "api-2" "api-3")

for api in "${APIS[@]}"; do
  echo "Stopping $api..."
  curl -X PATCH \
    http://localhost:5000/api/apis/$api/platforms/IP4/environments/tst/status \
    -H "Content-Type: application/json" \
    -d '{
      "status": "STOPPED",
      "updated_by": "maintenance-script"
    }'
done
```

---

## Error Handling

### Common Errors

#### 404 - Deployment Not Found
```json
{
  "status": "error",
  "message": "Deployment not found: my-api on IP4/tst"
}
```

#### 400 - Invalid Status
```json
{
  "status": "error",
  "message": "Invalid status. Must be one of: RUNNING, STOPPED, DEPLOYING, ..."
}
```

#### 400 - Missing Required Field
```json
{
  "status": "error",
  "message": "Missing required field: updated_by"
}
```

---

## Quick Reference Card

```bash
# Full Update (replace everything)
curl -X PUT .../apis/{api}/platforms/{plat}/environments/{env} \
  -d '{"status": "...", "updated_by": "...", "properties": {...}}'

# Partial Update (keep existing)
curl -X PATCH .../apis/{api}/platforms/{plat}/environments/{env} \
  -d '{"status": "...", "properties": {...}}'

# Status Only
curl -X PATCH .../apis/{api}/platforms/{plat}/environments/{env}/status \
  -d '{"status": "...", "updated_by": "..."}'

# Properties Only
curl -X PATCH .../apis/{api}/platforms/{plat}/environments/{env}/properties \
  -d '{"updated_by": "...", "properties": {...}}'

# Get Details
curl .../apis/{api}/platforms/{plat}/environments/{env}

# Delete
curl -X DELETE .../apis/{api}/platforms/{plat}/environments/{env}
```

---

## Testing

Run the comprehensive test suite:
```bash
python tests/test_update_api.py
```

---

For more information, see:
- [CREATE API Guide](CREATE_API_GUIDE.md)
- [Configuration Guide](MAINTENANCE_GUIDE.md)
- [README](README.md)