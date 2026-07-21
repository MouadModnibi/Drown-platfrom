# PyPI Publishing Instructions for drown CLI v0.2.0

## Important: Package Name

- **PyPI package name**: `drown` 
- **Installation command**: `pip install drown`
- **Repository folder**: `drown-cli` (just for organization)

Users install with `pip install drown`, NOT `pip install drown-cli`.

## Quick Publish Steps

### 1. Update Version Numbers

Edit these 2 files:

**File: `drown-cli/drown/__init__.py`**
```python
__version__ = "0.2.0"  # Change from "0.1.0"
```

**File: `drown-cli/setup.py`**
```python
setup(
    name="drown",  # This is correct - users install with: pip install drown
    version="0.2.0",  # Change from "0.1.0" or "0.2.1"
    # ... rest stays same
)
```

### 2. Build Package

```bash
cd c:\Users\Microsoft\Desktop\mini-heroku\drown-cli

# Clean old builds
rmdir /s /q build dist drown.egg-info 2>nul

# Build distributions
python -m build
```

### 3. Verify Build

```bash
twine check dist/*
```

Expected: `PASSED` for both files

### 4. Publish to PyPI

```bash
twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: [Your PyPI API token from https://pypi.org/manage/account/token/]

### 5. Test Installation

```bash
# Install/upgrade
pip install --upgrade drown

# Verify version
drown --version

# Should show: drown, version 0.2.0
```

### 6. Test New Feature

Create an app via web UI, then:

```bash
cd your-project/
drown create test-app

# Should show:
# App 'test-app' already exists, linking to it...
# ✓ App 'test-app' ready!
```

## What Changed in v0.2.0

- Added app linking: `drown create` now works with apps created via web UI
- Automatic fallback when app exists
- Better user experience for web → CLI workflow

## Files Changed in CLI Package

1. `drown-cli/drown/api.py` - Added `link_app()` function
2. `drown-cli/drown/cli.py` - Updated `create()` with fallback logic  
3. `drown-cli/drown/__init__.py` - Version bump to 0.2.0
4. `drown-cli/setup.py` - Version bump to 0.2.0

## Rollback

If issues occur, publish v0.2.1 with fixes (can't delete/replace on PyPI).

## Post-Publishing

- Verify on PyPI: https://pypi.org/project/drown/
- Test installation from fresh environment
- Monitor for user feedback/issues

---

**Ready to publish!** The web backend is already deployed and working. Publishing the CLI update is optional but recommended for the best user experience.
