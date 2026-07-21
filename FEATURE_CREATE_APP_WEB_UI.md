# Feature: Create New App via Web UI + Help Documentation

## Overview

Added a complete "Create New App" feature to the web dashboard with onboarding guide and troubleshooting documentation. This allows users to create apps via the web UI and get step-by-step deployment instructions, plus resolve common deployment issues.

## Implementation Summary

### 1. Backend Changes (web/app.py)

#### New Endpoints Added:

**`POST /api/apps/create`** (Modified)
- Added support for both token auth (CLI) and session auth (web UI)
- Changed: `user = get_user_from_token() or get_current_user()`
- Allows the same endpoint to work for both CLI and browser sessions

**`POST /api/apps/<app_name>/link`** (New)
- Returns git remote info for existing apps
- Used by CLI when app already exists (created via web UI)
- Supports both token and session auth
- Response format matches `/create` for CLI compatibility

**`GET/POST /create-app`** (New)
- Web UI form to create a new app
- Client-side validation for app name format
- Creates app and redirects to onboarding guide

**`GET /onboarding/<app_name>`** (New)
- Step-by-step deployment guide after app creation
- Shows personalized commands with actual app name
- Copy-to-clipboard buttons for each command
- Explains the web UI → CLI workflow

**`GET /help`** (New)
- Comprehensive troubleshooting guide
- Covers common deployment errors with solutions
- Framework-specific guidance (Node.js, React, Vite, Flask, Python)

### 2. Frontend Changes

#### New Templates Created:

**`web/templates/create_app.html`**
- Simple form with app name input
- Client-side validation (lowercase, numbers, hyphens only)
- Dark theme matching existing design
- Error handling display

**`web/templates/onboarding.html`**
- 5-step deployment guide
- Numbered steps with copy buttons
- Personalized with user's app name and domain
- Explains that `drown create` will link (not recreate) the app
- Links to app details and help pages

**`web/templates/help.html`**
- Comprehensive troubleshooting documentation
- Sections for each common error:
  - Application failed health check
  - Permission denied (publickey)
  - Branch name mismatch (main vs master)
  - Corrupted files (Windows)
  - Build failures
- Framework-specific solutions
- Code examples for fixes

#### Updated Templates:

**`web/templates/base.html`**
- Added "Help" link to navigation

**`web/templates/index.html`**
- Added "Create New App" button in header
- Added "Create Your First App" button in empty state

### 3. CLI Changes (drown-cli package)

#### Modified Files:

**`drown-cli/drown/api.py`**
- Added `link_app(token, app_name)` function
- Calls `POST /api/apps/<app_name>/link` endpoint

**`drown-cli/drown/cli.py`**
- Updated `create()` command with fallback logic
- If app already exists (409), automatically tries linking
- Changes success message from "created successfully" to "ready"
- Gracefully handles both create and link scenarios

### 4. User Flow

#### Web UI → CLI Workflow:

1. User creates app via web UI (`/create-app`)
2. App is created in database
3. User sees onboarding guide with commands
4. User runs `drown create my-app` locally
5. CLI detects app exists, falls back to `/link` endpoint
6. Git remote is added automatically
7. User can deploy with `git push platform main`

#### CLI-Only Workflow (unchanged):

1. User runs `drown create my-app`
2. App is created via API
3. Git remote added
4. Ready to deploy

## Files Changed

### Backend (web/)
- ✅ `web/app.py` - Added 4 new routes, modified 1 route

### Frontend (web/templates/)
- ✅ `web/templates/base.html` - Added Help nav link
- ✅ `web/templates/index.html` - Added Create button
- ✅ `web/templates/create_app.html` - New file
- ✅ `web/templates/onboarding.html` - New file
- ✅ `web/templates/help.html` - New file

### CLI (drown-cli/)
- ✅ `drown-cli/drown/api.py` - Added link_app() function
- ✅ `drown-cli/drown/cli.py` - Updated create() with fallback logic

## Testing Checklist

- [x] Web UI create app form validates app names correctly
- [x] Creating app redirects to onboarding guide
- [x] Onboarding guide shows personalized commands
- [x] Copy buttons work on onboarding guide
- [x] Help page displays all troubleshooting sections
- [x] Navigation includes Help link
- [x] Empty state shows "Create Your First App" button
- [x] CLI fallback logic works (create → link on 409)
- [x] `/api/apps/create` accepts both token and session auth
- [x] `/api/apps/<name>/link` returns correct git remote info

## API Changes Summary

### Modified Endpoints:

**POST /api/apps/create**
- Before: Token auth only
- After: Token OR session auth
- Breaking change: No (backward compatible)

### New Endpoints:

**POST /api/apps/<app_name>/link**
- Auth: Token OR session
- Returns: Same structure as `/create` (git_remote, domain, etc.)
- Use case: Get git remote for existing app

## Documentation Updates Needed

### README.md (drown-cli package)
- No changes needed - CLI behavior is backward compatible
- Users can still use `drown create` normally
- Fallback to link is transparent

### Web Dashboard
- "Help" page is self-documenting
- Onboarding guide explains the workflow

## Known Limitations

1. **CLI version requirement**: Users need to update to v0.2.0+ for the link fallback to work
2. **Partial compatibility**: Old CLI versions will get 409 error if app exists, but can still use other commands

## Security Considerations

- ✅ Ownership checks on all endpoints (can't link to other users' apps)
- ✅ Input validation matches API validation rules
- ✅ Session auth uses existing `@login_required` pattern
- ✅ No new authentication mechanisms introduced

## Performance Impact

- Minimal: New endpoints are simple database lookups
- No additional database queries on existing pages
- Copy-to-clipboard is client-side only

## Deployment Notes

1. Deploy web changes first (backward compatible)
2. Publish new CLI version (v0.2.0)
3. Existing CLI users continue to work normally
4. New users get full web UI experience

## Success Metrics

Once deployed, track:
- Number of apps created via web UI vs CLI
- Onboarding guide page views
- Help page views (indicates user confusion/issues)
- 409 errors that trigger CLI fallback (indicates web→CLI workflow usage)
