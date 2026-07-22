# Bug Fixes: Delete Feature Issues

## Bug 1: Delete confirmation button never enables on app detail page

**Symptom:** On `/app/<app_name>`, typing the exact app name in the delete confirmation modal doesn't enable the "Delete this app" button.

**Root Cause:** The delete modal HTML was placed inside `{% block scripts %}` **after** the JavaScript code that attaches the `addEventListener('input', ...)` to the input field. When the script executed at page load, `document.getElementById('confirm-name-input')` returned `null` because the DOM element hadn't been rendered yet (it was defined below in the same script block). The event listener was never attached, so typing in the input never triggered the comparison logic.

**Fix:** Moved the modal HTML div from `{% block scripts %}` to `{% block content %}`, ensuring the DOM elements exist **before** the JavaScript tries to attach listeners.

**Additional Issue Found:** A JavaScript comment `// Modal HTML is in {% block content %} above` was incorrectly parsed by Jinja2 as a real block tag, creating an unclosed block. Changed to `// Modal HTML is in the content block above` to avoid Jinja2 interpreting it.

**Files Changed:**
- `web/templates/app_detail.html` - Moved modal HTML, fixed comment

---

## Bug 2: Admin panel delete appears to succeed but doesn't actually delete

**Symptom:** On `/admin`, clicking delete on an app shows success but the app remains in the database after refresh.

**Root Cause:** The `delete_app()` function in `core/scaler.py` called `remove_all_replicas(app_name)`, which only deletes rows from the `replicas` table. It never deleted the actual **app row** from the `apps` table, nor the related `app_configs` and `deployments` rows. The app record persisted in the database, so `get_all_apps_with_owners()` continued returning it on the admin dashboard.

**Fix:** 
1. Created new function `remove_app(app_name)` in `core/database.py` that deletes **all** related records:
   - Replicas (`DELETE FROM replicas WHERE app_name=?`)
   - Configs (`DELETE FROM app_configs WHERE app_name=?`)
   - Deployments (`DELETE FROM deployments WHERE app_name=?`)
   - App row (`DELETE FROM apps WHERE app_name=?`)

2. Updated `delete_app()` in `core/scaler.py` to call `remove_app()` instead of just `remove_all_replicas()`

**Files Changed:**
- `control-plane/core/database.py` - Added `remove_app()` function
- `control-plane/core/scaler.py` - Updated `delete_app()` to use `remove_app()`

---

## Testing Performed

Both bugs are now fixed:

✅ **Bug 1 Fix Verified:**
- Modal HTML renders in content block before scripts block
- JavaScript finds the input element when attaching listener
- Typing app name enables delete button in real-time
- Jinja2 template syntax validates successfully

✅ **Bug 2 Fix Verified:**
- `remove_app()` deletes all DB records (apps, replicas, configs, deployments)
- Admin delete removes app from database completely
- CLI delete (which uses same function) also works correctly
- App no longer appears after page refresh

---

## Technical Details

### Bug 1 - DOM Timing Issue

**Before (broken):**
```html
{% block scripts %}
<script>
    document.getElementById('confirm-name-input').addEventListener(...) // FAILS - element doesn't exist yet
</script>

<div id="delete-modal">
    <input id="confirm-name-input" ...>  <!-- Defined AFTER JS runs -->
</div>
{% endblock %}
```

**After (fixed):**
```html
{% block content %}
    <!-- App content -->
    <div id="delete-modal">
        <input id="confirm-name-input" ...>  <!-- Defined FIRST -->
    </div>
{% endblock %}

{% block scripts %}
<script>
    document.getElementById('confirm-name-input').addEventListener(...) // WORKS - element exists
</script>
{% endblock %}
```

### Bug 2 - Incomplete Database Deletion

**Before (broken):**
```python
def delete_app(app_name):
    # ...stop containers...
    remove_all_replicas(app_name)  # Only deletes replicas table
    # App row stays in database! ❌
```

**After (fixed):**
```python
def delete_app(app_name):
    # ...stop containers...
    remove_app(app_name)  # Deletes: apps, replicas, configs, deployments ✅
```

---

## Impact

- ✅ Users can now delete their own apps from app detail page
- ✅ Admins can now delete any app from admin dashboard
- ✅ Both deletion methods fully remove the app from database
- ✅ Containers stopped, database cleaned, Caddy config regenerated
- ✅ No orphaned records left behind

---

## Files Modified

1. `web/templates/app_detail.html` - Fixed modal DOM ordering, fixed Jinja comment
2. `control-plane/core/database.py` - Added `remove_app()` for complete deletion
3. `control-plane/core/scaler.py` - Updated to use `remove_app()`

All changes are backward-compatible and don't affect any other functionality.
