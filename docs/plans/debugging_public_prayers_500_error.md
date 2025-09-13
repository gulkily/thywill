# Debugging Public Prayers 500 Error

## Problem Statement
The `/api/public/prayers` endpoint is returning a 500 Internal Server Error, but no detailed error information is appearing in the logs. The frontend shows "Unable to load prayers. Please try again later."

## Rubber Duck Debugging Process

### What We Know
1. HTTP 500 status = server-side error in our code
2. No error details in logs = error is being caught and suppressed
3. Error occurs on first API call (`page=1&page_size=10`)
4. Frontend JavaScript handles the error gracefully

### Most Likely Causes (in order of probability)

#### 1. Database Connection/Query Issues
**Symptoms**: 500 error on database operations
**Possible causes**:
- Database doesn't exist or isn't accessible
- Missing tables (Prayer, PrayerAttribute, User)
- SQL syntax errors in complex queries
- Database permissions

#### 2. Import/Module Issues  
**Symptoms**: 500 error during module loading
**Possible causes**:
- Missing imports in `public_routes.py`
- Circular import dependencies
- Missing service dependencies

#### 3. Data Type/Serialization Issues
**Symptoms**: 500 error when formatting response
**Possible causes**:
- DateTime serialization issues
- None/NULL values in unexpected places
- HTML content in JSON responses

#### 4. Rate Limiting Logic Issues
**Symptoms**: 500 error in rate limiting check
**Possible causes**:
- SecurityLog model issues (we already fixed timestamp → created_at)
- Database session management problems

## Debugging Strategy

### Step 1: Enable Detailed Error Logging
Add explicit exception logging to see the actual error:

```python
# In get_public_prayers_api function, replace the generic except block:
except Exception as e:
    import traceback
    print(f"DEBUG: Full error details: {str(e)}")
    print(f"DEBUG: Traceback: {traceback.format_exc()}")
    # ... rest of error handling
```

### Step 2: Test Database Connectivity
Check if basic database operations work:
```bash
./thywill status  # Check database status
sqlite3 thywill.db "SELECT COUNT(*) FROM prayer LIMIT 1;"  # Test basic query
```

### Step 3: Test Service in Isolation
Create a minimal test to isolate the issue:
```python
# Test PublicPrayerService directly
from app_helpers.services.public_prayer_service import PublicPrayerService
result = PublicPrayerService.get_public_prayers(page=1, page_size=10)
print(result)
```

### Step 4: Check Rate Limiting
The rate limiting code we added might be causing issues:
- SecurityLog table might not exist
- Database session conflicts

### Step 5: Verify Route Registration
Ensure the public router is properly registered and no route conflicts exist.

## Quick Fixes to Try

### Fix 1: Bypass Rate Limiting Temporarily
Comment out the rate limiting check to isolate the issue:
```python
# if not check_public_rate_limit(request):
#     raise HTTPException(429, ...)
```

### Fix 2: Add Debug Logging
Add print statements at key points:
```python
print("DEBUG: Starting get_public_prayers_api")
print("DEBUG: About to call PublicPrayerService")
result = PublicPrayerService.get_public_prayers(page=page, page_size=page_size)
print(f"DEBUG: Service returned: {type(result)}")
```

### Fix 3: Simplify Response
Return a minimal response to test basic functionality:
```python
return JSONResponse({
    'success': True,
    'prayers': [],
    'pagination': {'page': 1, 'total_pages': 0}
})
```

## Expected Resolution Path
1. Add debugging logs → See actual error
2. Most likely: Database/query issue
3. Fix specific issue (missing table, bad query, etc.)
4. Remove debug logging
5. Test full functionality

## Files to Check
- `/app_helpers/routes/public_routes.py` - API endpoint
- `/app_helpers/services/public_prayer_service.py` - Business logic  
- `/models.py` - Database schema
- `/thywill.db` - Database file existence
- Server logs for startup errors

## Prevention for Future
- Add comprehensive error logging to all new endpoints
- Add unit tests for service layer
- Add integration tests for API endpoints
- Consider structured logging for better debugging