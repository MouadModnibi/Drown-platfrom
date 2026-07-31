"""
Quick self-contained tests for framework_detect.detect_and_patch().
Run from repo root: python test_framework_detect.py
"""
import json
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "control-plane"))

from core.framework_detect import detect_and_patch, SERVE_VERSION

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []

def check(label, condition):
    status = PASS if condition else FAIL
    print(f"  [{status}] {label}")
    results.append(condition)

def make_repo(pkg: dict, vite_config: str = None) -> str:
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "package.json"), "w") as f:
        json.dump(pkg, f)
    if vite_config:
        with open(os.path.join(d, "vite.config.ts"), "w") as f:
            f.write(vite_config)
    return d

def read_pkg(repo):
    with open(os.path.join(repo, "package.json")) as f:
        return json.load(f)

# ── Test 1: vanilla Vite (npm create vite@latest default) ────────────────────
print("\n[1] Vanilla Vite project (zero manual config)")
repo = make_repo({
    "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
    "dependencies": {},
    "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-react": "^4.0.0"}
})
patched = detect_and_patch(repo)
pkg = read_pkg(repo)
check("detect_and_patch returns True", patched)
check("scripts.start set to serve -s dist", pkg["scripts"].get("start") == "serve -s dist -l 8080")
check("scripts.heroku-postbuild set to vite build", pkg["scripts"].get("heroku-postbuild") == "vite build")
check(f"serve pinned to {SERVE_VERSION}", pkg.get("dependencies", {}).get("serve") == SERVE_VERSION)
shutil.rmtree(repo)

# ── Test 2: Vite with custom outDir in vite.config ───────────────────────────
print("\n[2] Vite with custom outDir='public' in vite.config.ts")
repo = make_repo(
    {"scripts": {"dev": "vite"}, "devDependencies": {"vite": "^5.0.0"}},
    vite_config="export default defineConfig({ build: { outDir: 'public' } })"
)
detect_and_patch(repo)
pkg = read_pkg(repo)
check("scripts.start uses custom outDir 'public'", pkg["scripts"].get("start") == "serve -s public -l 8080")
shutil.rmtree(repo)

# ── Test 3: Vite with complex dynamic outDir (fallback to dist) ───────────────
print("\n[3] Vite with dynamic outDir (should fall back to dist)")
repo = make_repo(
    {"scripts": {"dev": "vite"}, "devDependencies": {"vite": "^5.0.0"}},
    vite_config="const dir = process.env.OUT_DIR || 'dist'; export default { build: { outDir: dir } }"
)
detect_and_patch(repo)
pkg = read_pkg(repo)
check("scripts.start falls back to 'dist'", pkg["scripts"].get("start") == "serve -s dist -l 8080")
shutil.rmtree(repo)

# ── Test 4: Create React App ──────────────────────────────────────────────────
print("\n[4] Create React App")
repo = make_repo({
    "scripts": {"start": "react-scripts start", "build": "react-scripts build"},
    "dependencies": {"react": "^18.0.0", "react-scripts": "5.0.1"}
})
patched = detect_and_patch(repo)
pkg = read_pkg(repo)
check("detect_and_patch returns True", patched)
check("scripts.start → serve -s build", pkg["scripts"].get("start") == "serve -s build -l 8080")
check("scripts.heroku-postbuild → react-scripts build", pkg["scripts"].get("heroku-postbuild") == "react-scripts build")
check("serve dependency added", pkg.get("dependencies", {}).get("serve") == SERVE_VERSION)
shutil.rmtree(repo)

# ── Test 5: Expo ──────────────────────────────────────────────────────────────
print("\n[5] Expo project")
repo = make_repo({
    "scripts": {"start": "expo start"},
    "dependencies": {"expo": "~51.0.0", "react": "18.2.0"}
})
patched = detect_and_patch(repo)
pkg = read_pkg(repo)
check("detect_and_patch returns True", patched)
check("scripts.start → serve -s dist", pkg["scripts"].get("start") == "serve -s dist -l 8080")
check("scripts.heroku-postbuild → expo export -p web", pkg["scripts"].get("heroku-postbuild") == "expo export -p web")
shutil.rmtree(repo)

# ── Test 6: already-configured Vite (user set start correctly) ───────────────
print("\n[6] Vite project with start already correctly configured")
repo = make_repo({
    "scripts": {
        "dev": "vite",
        "start": "serve -s dist -l 8080",
        "heroku-postbuild": "vite build"
    },
    "devDependencies": {"vite": "^5.0.0"},
    "dependencies": {"serve": "^14.0.0"}
})
patched = detect_and_patch(repo)
pkg = read_pkg(repo)
check("detect_and_patch returns False (nothing to do)", not patched)
check("scripts.start unchanged", pkg["scripts"]["start"] == "serve -s dist -l 8080")
check("serve version unchanged", pkg["dependencies"]["serve"] == "^14.0.0")
shutil.rmtree(repo)

# ── Test 7: non-Node project (no package.json) ────────────────────────────────
print("\n[7] No package.json (Python/other project)")
repo = tempfile.mkdtemp()
open(os.path.join(repo, "requirements.txt"), "w").close()
patched = detect_and_patch(repo)
check("detect_and_patch returns False", not patched)
shutil.rmtree(repo)

# ── Test 8: Node backend (Express) — should not be touched ───────────────────
print("\n[8] Express backend — start is 'node server.js', leave alone")
repo = make_repo({
    "scripts": {"start": "node server.js"},
    "dependencies": {"express": "^4.18.0"}
})
patched = detect_and_patch(repo)
check("detect_and_patch returns False", not patched)
shutil.rmtree(repo)

# ── Test 9: Vite project with start='vite preview' (not a dev server) ────────
print("\n[9] Vite project — start='vite preview --port 8080', leave start alone but add postbuild")
repo = make_repo({
    "scripts": {"start": "vite preview --port 8080"},
    "devDependencies": {"vite": "^5.0.0"}
})
patched = detect_and_patch(repo)
pkg = read_pkg(repo)
check("detect_and_patch returns True (needs heroku-postbuild)", patched)
check("scripts.start NOT changed", pkg["scripts"].get("start") == "vite preview --port 8080")
check("scripts.heroku-postbuild added", pkg["scripts"].get("heroku-postbuild") == "vite build")
shutil.rmtree(repo)

# ── Test 10: fully configured Vite with vite preview — nothing to do ─────────
print("\n[10] Vite — start='vite preview', heroku-postbuild already set → nothing to do")
repo = make_repo({
    "scripts": {
        "start": "vite preview --port 8080",
        "heroku-postbuild": "vite build"
    },
    "devDependencies": {"vite": "^5.0.0"},
    "dependencies": {"serve": "^14.0.0"}
})
patched = detect_and_patch(repo)
check("detect_and_patch returns False", not patched)
shutil.rmtree(repo)

# ── Summary ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
print(f"\n{'='*50}")
print(f"Results: {passed}/{total} checks passed")
if passed == total:
    print("All tests passed.")
    sys.exit(0)
else:
    print(f"{total - passed} test(s) FAILED.")
    sys.exit(1)
