# Feature: Delete App + Admin Dashboard

## Overview

Added app deletion capability with GitHub-style confirmation, plus an admin dashboard for managing all apps across all users. Admins can access any app and delete any app regardless of ownership.

## Implementation Summary

### 1. Database Changes (control-plane/core/database.py)

**Migration:**
- Added `is_admin` column to `users` table (INTEGER DEFAULT 0)
- Safe migration using PRAGMA table_info() check (same pattern as existing migrations)

**New Functions:**
- `is_user_admin(user_id)` - Check if user has admin privileges
- `get_all_apps_with_owners()` - Get all apps with owner information (admin dashboard)

### 2. Shared Delete Logic (control-plane/core/scaler.py)

**New Function:**
```python
delete_app(app_name)
```
- Stops and removes all containers using `docker rm -f`
- Removes database records via `remove_all_replicas()`
- Regenerates Caddy configuration
- Returns: (success: bool, replica_count: int, message: str)

### 3. CLI Update (cli.py)

**Updated:**
- `delete_app()` now calls `core.scaler.delete_app()` instead of duplicating logic
- Both CLI and web UI use the same implementation

### 4. Web App Changes (web/app.py)

**New Helper Function:**
```python
can_access_app(user, app_name)
```
- Unified ownership check for both session and token auth
- Returns: (can_access: bool, owner_id: int|None, reason: str)
- Checks: owns it OR is admin

**Updated Context Processor:**
- `inject_user()` now also injects `is_admin` for templates

**Routes Updated with Unified Helper:**
1. `/app/<app_name>` - App detail
2. `/api/app/<app_name>/metrics` - Metrics (session)
3. `/onboarding/<app_name>` - Onboarding
4. `/api/apps/<app_name>/metrics` - Metrics API v2
5. `/api/apps/<app_name>/scale` - Scale API
6. `/api/apps/<app_name>/logs` - Logs API
7. `/api/apps/<app_name>/link` - Link API

**New Routes:**
- `POST /app/<app_name>/delete` - Delete app (web UI, requires confirmation)
- `GET /admin` - Admin dashboard (admin only)
- `POST /admin/delete/<app_name>` - Admin delete (admin only, requires confirmation)

### 5. Frontend Changes

**base.html:**
- Added "Admin" link in navigation (visible only if `is_admin` is true)

**app_detail.html:**
- Added "Delete App" button in header
- Added GitHub-style delete confirmation modal:
  - Warning about permanence
  - Shows replica count
  - Requires typing exact app name
  - Delete button disabled until name matches
  - Real-time validation
  - Error handling

**admin.html (NEW):**
- Summary stats: Total apps, total replicas, running apps
- Full table of all apps across all users:
  - App name (links to detail)
  - Owner username
  - Domain (with external link)
  - Status (with animated indicator)
  - Replica count
  - Delete action button
- Same GitHub-style delete confirmation modal
- Uses admin-specific delete endpoint

## Security Features

### Ownership Checks
- **Before**: Each route manually checked `owner_id == user['id']`
- **After**: Unified `can_access_app()` helper checks ownership OR admin status
- All 7 routes now consistently allow access to owners OR admins

### Admin Access
- Admin users can:
  - View any app's details
  - Delete any app
  - Access admin dashboard
  - See all apps and owners
- Non-admin users:
  - Cannot access `/admin`
  - Cannot see admin nav link
  - Cannot delete others' apps

### Delete Confirmation
- GitHub-style safety pattern
- Must type exact app name
- Button disabled until match
- Shows consequences (replica count)
- Cannot be bypassed client-side (server validates name)

## Making a User Admin

No UI for granting admin status (intentional security decision). Set manually via database:

```sql
UPDATE users SET is_admin = 1 WHERE username = 'your_username';
```

Or via Python:

```python
import sqlite3
conn = sqlite3.connect('/home/ubuntu/mini-heroku/apps.db')
c = conn.cursor()
c.execute('UPDATE users SET is_admin = 1 WHERE username = ?', ('your_username',))
conn.commit()
conn.close()
```

## User Flow

### Delete Your Own App:
1. Navigate to app detail page
2. Click "Delete App" button
3. Modal appears with warning
4. Type exact app name to confirm
5. Click "Delete this app" (enabled only when name matches)
6. App deleted, redirected to homepage

### Admin View/Delete Any App:
1. Click "Admin" link in nav (only visible to admins)
2. See all apps across all users
3. Click app name to view details (owner OR admin can access)
4. Click "Delete" button in table
5. Same confirmation modal
6. App deleted, page reloads

## Files Changed

### Backend:
- ✅ `control-plane/core/database.py` - Migration + admin functions
- ✅ `control-plane/core/scaler.py` - Shared delete_app() function
- ✅ `cli.py` - Uses shared delete function
- ✅ `web/app.py` - Helper function + 3 new routes + updated 7 routes

### Templates:
- ✅ `web/templates/base.html` - Added admin nav link
- ✅ `web/templates/app_detail.html` - Added delete button + modal
- ✅ `web/templates/admin.html` - NEW admin dashboard

## Testing Checklist

- [ ] Non-admin user cannot access `/admin` (redirects to homepage)
- [ ] Non-admin user cannot see "Admin" nav link
- [ ] Non-admin user cannot delete others' apps
- [ ] Admin user can see "Admin" nav link
- [ ] Admin user can access `/admin` dashboard
- [ ] Admin user can see all apps (their own + others')
- [ ] Admin user can access any app's detail page
- [ ] Admin user can delete any app
- [ ] Delete confirmation requires exact app name
- [ ] Delete button disabled until name matches
- [ ] Delete actually removes containers and database records
- [ ] Caddy config regenerated after delete
- [ ] CLI delete command still works
- [ ] Token-based API routes respect admin access
- [ ] Session-based routes respect admin access

## Database Schema Changes

```sql
-- users table now has:
ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0;

-- Existing columns:
-- id, username, password_hash, created_at, api_token, is_admin
```

## API Consistency

All ownership-checked routes now use the same logic:

```python
can_access, owner_id, reason = can_access_app(user, app_name)
if not can_access:
    if reason == "not_found":
        return error_404
    return error_403
```

This ensures:
- Owners can access their apps
- Admins can access any app
- Non-owners/non-admins get 403
- Non-existent apps get 404
- Works identically for session auth and token auth

## Known Limitations

1. **Delete doesn't remove git repository** - Only unregisters app, git repo remains on disk
2. **No admin audit log** - No tracking of which admin deleted which app
3. **No undo** - Deletion is permanent
4. **Single admin role** - No granular permissions (admin has all permissions)

## Future Enhancements (Not Implemented)

- Audit log for admin actions
- Soft delete with trash/restore
- Granular permissions (read-only admin, etc.)
- Bulk operations (delete multiple apps)
- Git repository cleanup on delete
- Email notification to owner when admin deletes their app

## Deployment Notes

1. Deploy backend changes (database migration runs automatically on init)
2. Make first user admin manually via database
3. Deploy web changes (templates)
4. Test admin access works
5. Test delete functionality works

The migration is safe - adds column with default value, doesn't affect existing data.
