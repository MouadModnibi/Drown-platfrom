# Authentication System - Implementation Summary

## ✅ What Was Implemented

### 1. Session-Based Authentication
- **Flask sessions** with signed cookies (using `flask.session`)
- **Secret key** persisted to `web/.secret_key` file (survives Flask restarts)
- Generated once on first run using `secrets.token_hex(32)`
- Added to `.gitignore` to keep it out of version control

### 2. Routes Added

**`GET/POST /login`**
- Login form with username/password
- Validates credentials against `database.get_user_by_username()`
- Uses `check_password_hash()` from werkzeug.security
- On success: Sets `session['user_id']` and redirects to home or `?next` param
- On failure: Shows error message inline (no redirect)

**`GET/POST /register`**
- Registration form with username/password/confirm_password
- Validation:
  - Username: min 3 chars, not already taken
  - Password: min 6 chars, matches confirmation
- Hashes password with `generate_password_hash()`
- Creates user via `database.create_user()`
- Redirects to `/login` with success message

**`GET /logout`**
- Clears session
- Redirects to `/login`

### 3. Protected Routes (with `@login_required` decorator)

All existing routes now require authentication:
- `/` - Homepage (shows only user's owned apps)
- `/app/<app_name>` - App detail page (checks ownership)
- `/metrics` - Platform metrics (scoped to user's apps)
- `/api/stats` - Stats API (user's data only)
- `/api/app/<app_name>/metrics` - Metrics API (checks ownership)

### 4. Ownership Scoping

**Homepage (`/`)**
- Uses `database.list_apps_by_owner(user_id)` instead of `list_apps()`
- Only shows apps where `owner_id = current_user.id`
- Apps with `owner_id = NULL` are NOT visible

**App Detail (`/app/<app_name>`)**
- Calls `database.get_app_owner(app_name)`
- Returns **404** if `owner_id is None` (unassigned app)
- Returns **403 Forbidden** if `owner_id != current_user.id` (not your app)

**Metrics Page (`/metrics`)**
- Scoped to user's owned apps only
- Shows aggregated CPU/memory for user's replicas

**API Endpoints**
- All API endpoints check ownership before returning data
- Return 403 if unauthorized

### 5. UI Updates

**Header/Nav** (`base.html`)
- Shows logged-in username: `{{ current_user.username }}`
- Added "Logout" link
- Uses `@app.context_processor` to inject `current_user` in all templates

**New Templates**
- `login.html` - Dark-themed login form (matches dashboard design)
- `register.html` - Dark-themed registration form
- Both use the same dark color palette and premium styling

### 6. Helper Functions

**`login_required` decorator**
```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
```

**`get_current_user()` helper**
- Returns `{'id': user_id, 'username': username}` if logged in
- Returns `None` if not logged in
- Used throughout the app to check current user

**`inject_user()` context processor**
- Makes `current_user` available in ALL templates automatically
- No need to pass it explicitly in every `render_template()` call

## 🔒 Security Features

1. **Password Hashing**: Uses `werkzeug.security.generate_password_hash()` and `check_password_hash()`
2. **Signed Sessions**: Flask's session cookies are cryptographically signed with the secret key
3. **Ownership Checks**: Every app access verifies ownership (403 if unauthorized, 404 if unassigned)
4. **Input Validation**: Username/password length, uniqueness checks, password confirmation
5. **Persistent Secret Key**: Stored in file, survives restarts (sessions don't break)

## ⚠️ Known Limitations

### Session Invalidation on Secret Key Change
If `web/.secret_key` is deleted or regenerated, **all existing sessions are invalidated** (users get logged out). This is expected Flask behavior.

**Current implementation**: Secret key is generated once and persisted to `web/.secret_key`, so sessions survive Flask restarts.

**Future improvement**: Move to environment variable (`FLASK_SECRET_KEY`) for production deployments.

### No CSRF Protection
Currently no CSRF tokens on forms. This is acceptable for a private/internal tool, but should be added if exposed to the internet.

**Future improvement**: Use `flask-wtf` or manually add CSRF tokens.

### No Rate Limiting
Login attempts are not rate-limited. An attacker could brute-force passwords.

**Future improvement**: Add rate limiting with `flask-limiter` or similar.

### No Email Verification
Registration is immediate with no email confirmation.

**Current status**: Acceptable for internal use where you control user registration.

### No Password Reset
No "forgot password" flow. Users cannot reset their own passwords.

**Workaround**: Manually update password_hash in database if needed.

## 📊 Database Schema (Already Existed)

```sql
-- users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- apps table (owner_id column already added)
ALTER TABLE apps ADD COLUMN owner_id INTEGER;
```

### Functions Used (from `core/database.py`)
- `create_user(username, password_hash)`
- `get_user_by_username(username)` → (id, username, password_hash)
- `get_user_by_id(user_id)` → (id, username)
- `set_app_owner(app_name, owner_id)`
- `list_apps_by_owner(owner_id)`
- `get_app_owner(app_name)` → owner_id or None

## 🚀 Testing the System

### 1. First Visit
Visit http://127.0.0.1:5000 → Redirected to `/login`

### 2. Register a New User
1. Click "Register here"
2. Fill in:
   - Username: `admin` (min 3 chars)
   - Password: `password123` (min 6 chars)
   - Confirm Password: `password123`
3. Submit → Redirected to `/login` with success message

### 3. Login
1. Enter username: `admin`
2. Enter password: `password123`
3. Submit → Redirected to `/` (homepage)

### 4. Test Ownership
- Homepage shows only apps where `owner_id = current_user.id`
- If you try to access another user's app → **403 Forbidden**
- If you try to access an app with `owner_id = NULL` → **404 Not Found**

### 5. Test Session Persistence
1. Login
2. Restart Flask server: `Ctrl+C` and `python app.py` again
3. Refresh browser → **Still logged in** (session persists)

### 6. Logout
- Click "Logout" in nav → Session cleared → Redirected to `/login`

## 📁 Files Modified/Created

### Modified
- ✅ `web/app.py` - Added auth system, decorator, protected routes
- ✅ `web/templates/base.html` - Added username display and logout link
- ✅ `web/static/css/style.css` - Added auth page styling
- ✅ `.gitignore` - Added `web/.secret_key`

### Created
- ✅ `web/.secret_key` - Persistent session secret (auto-generated)
- ✅ `web/templates/login.html` - Login page
- ✅ `web/templates/register.html` - Registration page
- ✅ `web/AUTHENTICATION.md` - This documentation

### Not Modified (as required)
- ❌ `core/database.py` - Used existing functions only
- ❌ `core/docker_ops.py` - Not touched
- ❌ `core/caddy.py` - Not touched
- ❌ `main.py` - Not touched

## 🎨 Design Consistency

All auth pages match the existing dark theme:
- Same color palette (deep slate backgrounds, blue accents)
- Same typography (Inter font, consistent sizes)
- Same button styles and form inputs
- Same shadows, borders, and hover effects
- Centered card layout with glass-morphism effect

## 🔄 Next Steps (Future Improvements)

1. **Assign Ownership to Existing Apps**
   - Currently apps with `owner_id = NULL` are hidden from everyone
   - You'll need to backfill ownership using `database.set_app_owner(app_name, user_id)`

2. **Environment Variable for Secret Key**
   - Move from `web/.secret_key` file to `os.environ['FLASK_SECRET_KEY']`

3. **CSRF Protection**
   - Add `flask-wtf` and CSRF tokens to forms

4. **Rate Limiting**
   - Add `flask-limiter` to prevent brute-force attacks

5. **Password Reset Flow**
   - Add "Forgot Password" with email/token-based reset

6. **User Management Page**
   - Admin interface to view/manage users
   - Assign app ownership via UI

7. **Remember Me**
   - Add "Remember Me" checkbox to extend session lifetime

## ✅ Authentication System Complete!

The dashboard now has a fully functional authentication system with:
- ✅ Login/Register/Logout
- ✅ Session management (persists across restarts)
- ✅ Ownership-based access control
- ✅ Protected routes
- ✅ Dark-themed auth pages
- ✅ User display in nav

Visit **http://127.0.0.1:5000** to test!
