# Publishing drown-cli to PyPI

## Prerequisites

1. **Create a PyPI account** at https://pypi.org/account/register/
2. **Install build tools**:
   ```bash
   pip install --upgrade build twine
   ```

## Publishing Steps

### 1. Verify Package is Ready

```bash
cd c:\Users\Microsoft\Desktop\mini-heroku\drown-cli

# Test installation locally
pip install -e .

# Test the CLI
drown --version
drown --help
```

### 2. Build the Distribution

```bash
# Clean old builds
rm -rf build dist *.egg-info

# Build source and wheel distributions
python -m build
```

This creates:
- `dist/drown-cli-0.1.0.tar.gz` (source distribution)
- `dist/drown_cli-0.1.0-py3-none-any.whl` (wheel)

### 3. Check the Build

```bash
# Verify the package with twine
twine check dist/*
```

Should output: `Checking dist/... PASSED`

### 4. Test Upload to TestPyPI (Optional but Recommended)

```bash
# Upload to test.pypi.org first
twine upload --repository testpypi dist/*
```

You'll be prompted for:
- Username: `__token__`
- Password: Your TestPyPI API token (get from https://test.pypi.org/manage/account/token/)

Test install:
```bash
pip install --index-url https://test.pypi.org/simple/ drown-cli
```

### 5. Upload to Real PyPI

```bash
# Upload to pypi.org
twine upload dist/*
```

You'll be prompted for:
- Username: `__token__`
- Password: Your PyPI API token (get from https://pypi.org/manage/account/token/)

**Important**: Use an API token, not your password. Create one at:
https://pypi.org/manage/account/token/

### 6. Verify Installation

```bash
# Install from PyPI
pip install drown

# Test it works
drown --version
drown login
```

## Versioning

To release a new version:

1. Update version in `setup.py` and `drown/__init__.py`
2. Update `CHANGELOG.md` (create one if needed)
3. Commit and tag:
   ```bash
   git add .
   git commit -m "Release v0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```
4. Rebuild and re-upload:
   ```bash
   rm -rf dist build *.egg-info
   python -m build
   twine upload dist/*
   ```

## Troubleshooting

### "Package already exists"
- You can't re-upload the same version. Increment the version number in `setup.py`.

### "Invalid credentials"
- Make sure you're using an API token (starts with `pypi-`), not your password
- Username should be `__token__` (literal string)

### "README rendering failed"
- Test with: `twine check dist/*`
- Ensure README.md uses standard Markdown (no custom extensions)

### Import errors after install
- Verify package structure with: `python -m zipfile -l dist/*.whl`
- Ensure `__init__.py` exists in the `drown/` directory

## Post-Publication

1. **Update README badges** (optional):
   ```markdown
   ![PyPI](https://img.shields.io/pypi/v/drown-cli)
   ![Python](https://img.shields.io/pypi/pyversions/drown-cli)
   ![Downloads](https://img.shields.io/pypi/dm/drown-cli)
   ```

2. **Announce** on GitHub, social media, etc.

3. **Monitor** https://pypi.org/project/drown-cli/ for download stats

## Quick Reference Commands

```bash
# Install build tools
pip install --upgrade build twine

# Build package
python -m build

# Check package
twine check dist/*

# Upload to TestPyPI (optional)
twine upload --repository testpypi dist/*

# Upload to PyPI (production)
twine upload dist/*
```

## Package URL

After publishing, your package will be available at:
- **PyPI**: https://pypi.org/project/drown-cli/
- **Install**: `pip install drown`
