"""
framework_detect.py — automatic frontend framework detection and package.json patching.

Runs BEFORE pack build on the checked-out repo_path. If a known static-site framework
is detected AND the existing scripts.start looks like a dev server (or is missing),
this module patches the repo_path/package.json copy in place so that:

  1. serve is added as a dependency (pinned to ^14.2.6)
  2. scripts.start is set to the correct production serve command
  3. scripts.heroku-postbuild is set to the appropriate build command

IMPORTANT: only repo_path/package.json is touched — the user's bare git repo is
never modified.  repo_path is the temporary checkout that pack build reads from.

Detection priority (first match wins):
  1. Expo      — "expo" in deps/devDeps
  2. CRA       — "react-scripts" in deps/devDeps
  3. Vite      — "vite" in deps/devDeps

A scripts.start is considered "already production-ready" (and therefore left alone)
if it contains any of: "serve", "node ", "next start", "python", "gunicorn", "uvicorn".
"""

import json
import logging
import os
import re

# Pinned version floor for the injected serve dependency.
# Checked against npm registry on 2025-07-31 — latest stable is 14.2.6.
SERVE_VERSION = "^14.2.6"

# Patterns that indicate scripts.start is a known dev-server command.
# Re-checked periodically — keep conservative (only add patterns we're certain about).
_DEV_SERVER_PATTERNS = [
    r"^vite$",                      # plain "vite" with no args
    r"\bvite\b(?!.*(?:preview|serve))",  # "vite ..." but not "vite preview" / "vite serve"
    r"\breact-scripts\s+start\b",
    r"\bexpo\s+start\b",
    r"\bnext\s+dev\b",
]

# If start contains any of these, it's already a production server — don't touch.
_PRODUCTION_ALLOWLIST = [
    "serve",
    "node ",
    "next start",
    "python",
    "gunicorn",
    "uvicorn",
]

_COMPILED_DEV = [re.compile(p) for p in _DEV_SERVER_PATTERNS]


def _is_dev_server(start_cmd: str) -> bool:
    """Return True if start_cmd looks like a dev server that needs replacing."""
    lower = start_cmd.strip()
    for keyword in _PRODUCTION_ALLOWLIST:
        if keyword in lower:
            return False
    for pattern in _COMPILED_DEV:
        if pattern.search(lower):
            return True
    return False


def _get_vite_out_dir(repo_path: str) -> str:
    """
    Try to extract build.outDir from vite.config.{js,ts,mjs} using a conservative
    regex.  Only parses simple string literals — returns "dist" for anything complex.
    """
    for name in ("vite.config.ts", "vite.config.js", "vite.config.mjs"):
        cfg_path = os.path.join(repo_path, name)
        if not os.path.exists(cfg_path):
            continue
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Match: outDir: "something"  or  outDir: 'something'
            m = re.search(r'\boutDir\s*:\s*["\']([^"\']+)["\']', content)
            if m:
                out_dir = m.group(1).strip()
                if out_dir and "/" not in out_dir and "\\" not in out_dir:
                    # Only accept a simple directory name, not a path
                    return out_dir
        except Exception:
            pass
    return "dist"


def _needs_heroku_postbuild(scripts: dict) -> bool:
    """Return True if heroku-postbuild is absent or empty."""
    val = scripts.get("heroku-postbuild", "").strip()
    return not val


def detect_and_patch(repo_path: str) -> bool:
    """
    Inspect repo_path/package.json, detect the framework, and patch in place if needed.

    Returns True if a patch was applied, False if nothing was changed.
    Logs clearly what was detected and what (if anything) was modified.
    """
    pkg_path = os.path.join(repo_path, "package.json")
    if not os.path.exists(pkg_path):
        logging.debug("[framework_detect] No package.json found — skipping detection")
        return False

    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)
    except Exception as e:
        logging.warning(f"[framework_detect] Could not parse package.json: {e} — skipping")
        return False

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    scripts = pkg.setdefault("scripts", {})
    current_start = scripts.get("start", "")

    # ── Detect framework ──────────────────────────────────────────────────────

    if "expo" in deps:
        framework = "Expo"
        start_cmd   = "serve -s dist -l 8080"
        build_cmd   = "expo export -p web"

    elif "react-scripts" in deps:
        framework = "Create React App"
        start_cmd   = "serve -s build -l 8080"
        build_cmd   = "react-scripts build"

    elif "vite" in deps:
        out_dir     = _get_vite_out_dir(repo_path)
        framework   = f"Vite (outDir={out_dir})"
        start_cmd   = f"serve -s {out_dir} -l 8080"
        build_cmd   = "vite build"

    else:
        logging.debug("[framework_detect] No known frontend framework detected — skipping")
        return False

    # ── Decide whether to patch ───────────────────────────────────────────────

    start_needs_patch = (not current_start) or _is_dev_server(current_start)
    build_needs_patch = _needs_heroku_postbuild(scripts)

    if not start_needs_patch and not build_needs_patch:
        logging.info(
            f"[framework_detect] Detected {framework} — scripts.start already looks "
            f"production-ready (\"{current_start}\"), no changes needed"
        )
        return False

    # ── Apply patch ───────────────────────────────────────────────────────────

    changes = []

    if start_needs_patch:
        old = f'"{current_start}"' if current_start else "(missing)"
        scripts["start"] = start_cmd
        changes.append(f'scripts.start {old} → "{start_cmd}"')

    if build_needs_patch:
        scripts["heroku-postbuild"] = build_cmd
        changes.append(f'scripts.heroku-postbuild → "{build_cmd}"')

    # Add serve to dependencies if not already anywhere in the manifest
    serve_added = False
    if "serve" not in deps:
        pkg.setdefault("dependencies", {})["serve"] = SERVE_VERSION
        serve_added = True
        changes.append(f'dependencies.serve → "{SERVE_VERSION}"')

    # Write the patched package.json back to repo_path
    try:
        with open(pkg_path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, indent=2)
            f.write("\n")
    except Exception as e:
        logging.error(f"[framework_detect] Failed to write patched package.json: {e}")
        return False
# If we added a new dependency (serve), package-lock.json is now out of sync.
    # Buildpacks use `npm ci`, which requires an exact match — so regenerate the
    # lockfile now with npm install, scoped to just this repo_path.
    if serve_added:
        import subprocess
        try:
            result = subprocess.run(
                ["npm", "install", "--package-lock-only"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                logging.warning(
                    f"[framework_detect] Failed to update package-lock.json: {result.stderr[-500:]}"
                )
            else:
                logging.info("[framework_detect]   package-lock.json updated to match new dependency")
        except Exception as e:
            logging.warning(f"[framework_detect] Could not run npm install to update lockfile: {e}")
	
    logging.info(
        f"-----> [framework_detect] Detected {framework} project — "
        f"scripts.start looks like a dev server, auto-configuring for deployment"
    )
    for change in changes:
        logging.info(f"-----> [framework_detect]   {change}")

    return True
