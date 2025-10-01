# Configuration Maintenance Guide

All valid platforms, environments, and statuses are centrally managed in `app/config.py`.

## ✅ Single Source of Truth

**File: `app/config.py`**

All deployment-related configuration is defined here. No need to update any other files!

---

## 🎯 How to Add a New Platform

### Step 1: Edit `app/config.py`

```python
PLATFORM_MAPPING = {
    'IP2': 'IP2 Platform',
    'IP3': 'IP3 Platform',
    'IP4': 'IP4 Platform',
    'IP5': 'IP5 Platform',
    'NEW_PLATFORM': 'New Platform Display Name',  # ← Add here
    # ... rest of platforms
}
```

### Step 2: Restart Application

```bash
podman-compose restart flask-app
```

### Step 3: Test

```bash
# Get all platforms
curl http://localhost:5000/api/platforms

# Should include your new platform
```

**That's it!** No code changes needed.

---

## 🌍 How to Add a New Environment

### Step 1: Edit `app/config.py`

```python
ENVIRONMENT_MAPPING = {
    'dev': 'Development',
    'tst': 'Test',
    'prd': 'Production',
    'new-env': 'New Environment Name',  # ← Add here
    # ... rest of environments
}
```

### Step 2: Restart Application

```bash
podman-compose restart flask-app
```

### Step 3: Test

```bash
# Get all environments
curl http://localhost:5000/api/environments

# Should include your new environment
```

---

## 📊 How to Add a New Status

### Step 1: Edit `app/config.py`

```python
STATUS_OPTIONS = [
    'RUNNING',
    'STOPPED',
    'DEPLOYING',
    'NEW_STATUS',  # ← Add here
    # ... rest of statuses
]
```

### Step 2: Restart Application

```bash
podman-compose restart flask-app
```

### Step 3: Test

```bash
# Get all statuses
curl http://localhost:5000/api/statuses

# Should include your new status
```

---

## 🗑️ How to Decommission a Platform/Environment

### Option 1: Remove Completely

**⚠️ WARNING:** Only do this if NO APIs are currently deployed on this platform/environment!

```python
# In config.py - just delete the line
PLATFORM_MAPPING = {
    'IP2': 'IP2 Platform',
    # 'IP3': 'IP3 Platform',  # ← Commented out / removed
    'IP4': 'IP4 Platform',
}
```

### Option 2: Mark as Deprecated (Recommended)

Keep it in the config but mark as deprecated:

```python
PLATFORM_MAPPING = {
    'IP2': 'IP2 Platform',
    'IP3': 'IP3 Platform (DEPRECATED)',  # ← Mark as deprecated
    'IP4': 'IP4 Platform',
}
```

**Benefits:**
- Existing deployments still work
- New deployments can still target it if needed
- Clear visibility that it's deprecated
- Can remove later after all APIs migrated

---

## 🔍 Checking What's Currently Deployed

Before removing a platform/environment, check if anything is using it:

```bash
# Connect to MongoDB
podman exec -it mongo mongosh

use ccr

# Check which platforms are in use
db.apis.aggregate([
  {$unwind: "$Platform"},
  {$group: {_id: "$Platform.PlatformID", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

# Check which environments are in use
db.apis.aggregate([
  {$unwind: "$Platform"},
  {$unwind: "$Platform.Environment"},
  {$group: {_id: "$Platform.Environment.environmentID", count: {$sum: 1}}},
  {$sort: {count: -1}}
])
```

---

## 📝 Example: Real-World Scenario

### Scenario: Decommissioning IP3, Adding IP8

**Current State:**
- IP3 has 5 APIs deployed
- Want to add new IP8 platform

**Steps:**

1. **Add IP8 to config:**
```python
PLATFORM_MAPPING = {
    'IP2': 'IP2 Platform',
    'IP3': 'IP3 Platform (DEPRECATED - Migrate to IP8)',
    'IP4': 'IP4 Platform',
    'IP8': 'IP8 Platform',  # ← New platform
}
```

2. **Restart application**

3. **Migrate APIs from IP3 to IP8** (via deploy endpoint)

4. **Verify all APIs migrated:**
```bash
# Check if IP3 still has deployments
db.apis.find({"Platform.PlatformID": "IP3"}).count()
# Should return 0
```

5. **Remove IP3 from config:**
```python
PLATFORM_MAPPING = {
    'IP2': 'IP2 Platform',
    # IP3 removed
    'IP4': 'IP4 Platform',
    'IP8': 'IP8 Platform',
}
```

6. **Final restart**

---

## 🔒 Validation Happens Automatically

Once you update `app/config.py`:

✅ **Deploy endpoint** - Validates against your config  
✅ **Validation endpoint** - Uses your config  
✅ **API endpoints** - Return your updated lists  
✅ **Error messages** - Show correct valid values  

**No code changes required!**

---

## 📊 Get Current Configuration via API

Useful for building UIs or checking current values:

```bash
# Get all configuration at once
curl http://localhost:5000/api/config

# Get just platforms
curl http://localhost:5000/api/platforms

# Get just environments
curl http://localhost:5000/api/environments

# Get just statuses
curl http://localhost:5000/api/statuses
```

---

## 🎯 Best Practices

1. **Always restart application** after config changes
2. **Check existing deployments** before removing platforms/environments
3. **Use deprecation markers** before complete removal
4. **Document changes** in your change log
5. **Test after changes** using the `/api/config` endpoint
6. **Communicate** platform/environment changes to your team

---

## 🆘 Troubleshooting

### "Invalid platform" error after adding new platform

**Cause:** Application not restarted

**Solution:**
```bash
podman-compose restart flask-app
podman logs -f flask-app  # Verify it started correctly
```

### Error shows old platform list

**Cause:** Cache or old instance running

**Solution:**
```bash
podman-compose down
podman-compose up -d
```

### Can't deploy to old platform after removal

**Expected behavior!** Once removed from config, deployments are blocked.

**Solution:** Either:
- Re-add to config if needed
- Deploy to different platform

---

## 📞 Questions?

Check the logs:
```bash
podman logs -f flask-app
```

Configuration issues will show up with clear error messages.