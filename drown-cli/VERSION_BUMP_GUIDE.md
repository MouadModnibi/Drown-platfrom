# Version Bump Guide: drown-cli v0.1.0 → v0.2.0

## Changes in This Version

### New Features
- **App linking fallback**: `drown create` now automatically links to existing apps if they were created via the web UI
- Graceful handling of 409 Conflict responses
- Better user experience for web UI → CLI workflow

### Modified Behavior
- Success message changed from "created successfully" to "ready" (works for both create and link)
- Automatic fallback to `/api/apps/<name>/link` when app exists

### Files Changed in drown-cli Package

1. **`drown/api.py`** - Added `link_app()` function
2. **`drown/cli.py`** - Updated `create()` command with fallback logic
3. **`drown/__init__.py`** - Version bump needed
4. **`setup.py`** - Version bump needed

## Step-by-Step Version Bump Instructions

### 1. Update Version in `__init__.py`

File: `drown-cli/drown/__init__.py`

```python
# Change this line:
__version__ = "0.1.0"

# To:
__version__ = "0.2.0"
```

### 2. Update Version in `setup.py`

File: `drown-cli/setup.py`

```python
setup(
    name="drown-cli",
    version="0.2.0",  # Change from "0.1.0"
    # ... rest of setup.py stays the same
)
```

### 3. Create a CHANGELOG Entry (Optional but Recommended)

Create or update `drown-cli/CHANGELOG.md`:

```markdown
# Changelog

## [0.2.0] - 2026-07-21

### Added
- App linking feature: `drown create` now works seamlessly with apps created via web UI
- New `link_app()` API function for connecting to existing apps
- Automatic fallback when attempting to create an app that already exists

### Changed
- Success message for `drown create` is now "✓ App 'name' ready!" instead of "created successfully"
- Better error handling for app name conflicts

### Technical
- Added POST /api/apps/<name>/link endpoint support
- Improved web UI → CLI workflow compatibility

## [0.1.0] - 2026-07-20

### Added
- Initial release
- Commands: login, logout, apps, create, scale, logs, metrics
- Automatic SSH key setup during login
- Git remote auto-configuration
```

### 4. Update README.md (If Needed)

No changes needed - the CLI behavior is backward compatible and transparent to users.

### 5. Git Commit and Tag

```bash
cd c:\Users\Microsoft\Desktop\mini-heroku\drown-cli

git add .
git commit -m "Release v0.2.0 - Add app linking fallback for web UI workflow"
git tag v0.2.0
git push origin main --tags
```

### 6. Build the Package

```bash
cd c:\Users\Microsoft\Desktop\mini-heroku\drown-cli

# Clean old builds
rmdir /s /q build dist drown_cli.egg-info 2>nul

# Build new distributions
python -m build
```

Expected output:
```
Successfully built drown_cli-0.2.0.tar.gz and drown_cli-0.2.0-py3-none-any.whl
```

### 7. Check the Build

```bash
twine check dist/*
```

Expected output:
```
Checking dist/drown_cli-0.2.0-py3-none-any.whl: PASSED
Checking dist/drown_cli-0.2.0.tar.gz: PASSED
```

### 8. (Optional) Test on TestPyPI

```bash
twine upload --repository testpypi dist/*
```

Then test install:
```bash
pip install --index-url https://test.pypi.org/simple/ drown-cli
drown --version  # Should show 0.2.0
```

### 9. Publish to PyPI

```bash
twine upload dist/*
```

You'll be prompted for:
- **Username**: `__token__`
- **Password**: Your PyPI API token

### 10. Verify Installation

```bash
pip install --upgrade drown-cli
drown --version
```

Should output:
```
drown, version 0.2.0
```

### 11. Test the New Feature

```bash
# Assuming you have an app created via web UI called "test-web-app"
cd your-project/
drown create test-web-app

# Expected output:
# App 'test-web-app' already exists, linking to it...
# ✓ App 'test-web-app' ready!
# Domain: test-web-app.dr0wn.duckdns.org
# ✓ Git remote 'platform' added
# To deploy, push your code:
#   git push platform main
```

## Rollback Plan

If issues are discovered after publishing:

1. **Immediate**: Publish v0.2.1 with fixes (PyPI doesn't allow re-uploading same version)
2. **Document**: Update README with known issues
3. **Communicate**: Update GitHub/documentation with workaround

Note: You cannot delete or replace a published version on PyPI.

## Pre-Publication Checklist

- [ ] Version updated in `drown/__init__.py`
- [ ] Version updated in `setup.py`
- [ ] CHANGELOG.md created/updated
- [ ] Git changes committed
- [ ] Git tag created (v0.2.0)
- [ ] Package built successfully
- [ ] `twine check` passes
- [ ] (Optional) Tested on TestPyPI
- [ ] Ready to upload to PyPI

## Post-Publication Checklist

- [ ] Verified installation works: `pip install --upgrade drown-cli`
- [ ] Version check passes: `drown --version` shows 0.2.0
- [ ] Tested app linking feature works
- [ ] Updated any external documentation (if applicable)
- [ ] Announced release (if applicable)

## Quick Commands Reference

```bash
# Navigate to package
cd c:\Users\Microsoft\Desktop\mini-heroku\drown-cli

# Update versions (manual edit)
# - drown/__init__.py
# - setup.py

# Build
rmdir /s /q build dist drown_cli.egg-info 2>nul
python -m build

# Check
twine check dist/*

# Publish
twine upload dist/*

# Verify
pip install --upgrade drown-cli
drown --version
```

## Support

After publishing, monitor:
- GitHub issues for bug reports
- PyPI download statistics
- User feedback on the web UI → CLI workflow

The new feature is designed to be transparent and backward-compatible, so existing users should not experience any breaking changes.
