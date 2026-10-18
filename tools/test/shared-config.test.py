#!/usr/bin/env python3
"""Fixtures for hooks/shared-config.py — the SessionStart hook must never fail, hang or prompt.

    python3 tools/test/shared-config.test.py
"""
import importlib.util, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "plugins" / "fig" / "hooks" / "shared-config.py"
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


# 1. No PyYAML: `-S` drops site-packages, so the resolver cannot import it. The session
#    must still start — silently, with exit 0.
r = subprocess.run([sys.executable, "-S", "-c", "import yaml"], capture_output=True, text=True)
check("precondition: python3 -S cannot import yaml", r.returncode != 0, "PyYAML still importable")
with tempfile.TemporaryDirectory() as home:
    (Path(home) / ".claude").mkdir()
    (Path(home) / ".claude" / "figma-conventions.yaml").write_text("meta: {profile: x}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["HOME"] = home
    r = subprocess.run([sys.executable, "-S", str(HOOK)], cwd=home, env=env, capture_output=True, text=True, timeout=60)
    check("no PyYAML → exit 0", r.returncode == 0, f"rc={r.returncode}")
    check("no PyYAML → silent", r.stderr == "" and r.stdout == "", f"stderr={r.stderr[-200:]!r} stdout={r.stdout[-200:]!r}")

# 2. git must never prompt for credentials or a host-key answer.
spec = importlib.util.spec_from_file_location("shared_config_hook", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class FakeResolver:
    def origin_state(self, name):
        return {"root": "/x", "dirty": False}

    def origin(self, name):
        return []


seen = {}


def fake_run(*a, **kw):
    seen["env"] = kw.get("env")
    return subprocess.CompletedProcess(a, 0, b"", b"")


hook.resolver = lambda: FakeResolver()
hook.due = lambda root: True
real_run = hook.subprocess.run
hook.subprocess.run = fake_run
try:
    hook.main()
finally:
    hook.subprocess.run = real_run
env = seen.get("env") or {}
check("git env: GIT_TERMINAL_PROMPT=0", env.get("GIT_TERMINAL_PROMPT") == "0", repr(env.get("GIT_TERMINAL_PROMPT")))
check("git env: ssh BatchMode=yes", "BatchMode=yes" in env.get("GIT_SSH_COMMAND", ""), repr(env.get("GIT_SSH_COMMAND")))

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("shared-config fixtures · PASS")
