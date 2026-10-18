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


def fetch_env(environ=None, config_value=""):
    """Run main() with git faked out; return the env handed to the fetch call."""
    seen = {}

    def fake_run(cmd, *a, **kw):
        if "config" in cmd:                      # the core.sshCommand lookup
            return subprocess.CompletedProcess(cmd, 0 if config_value else 1, config_value + "\n" if config_value else "", "")
        seen["env"] = kw.get("env")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    hook.resolver = lambda: FakeResolver()
    hook.due = lambda root: True
    real_run, real_environ = hook.subprocess.run, hook.os.environ
    hook.subprocess.run = fake_run
    hook.os.environ = dict(environ or {})
    try:
        hook.main()
    finally:
        hook.subprocess.run = real_run
        hook.os.environ = real_environ
    return seen.get("env") or {}


env = fetch_env()
check("git env: GIT_TERMINAL_PROMPT=0", env.get("GIT_TERMINAL_PROMPT") == "0", repr(env.get("GIT_TERMINAL_PROMPT")))
check("git env: ssh BatchMode=yes", env.get("GIT_SSH_COMMAND") == "ssh -o BatchMode=yes", repr(env.get("GIT_SSH_COMMAND")))
env = fetch_env({"GIT_SSH_COMMAND": "ssh -i /k"})
check("existing GIT_SSH_COMMAND is extended", env.get("GIT_SSH_COMMAND") == "ssh -i /k -o BatchMode=yes", repr(env.get("GIT_SSH_COMMAND")))
env = fetch_env(config_value="ssh -i /c")
check("core.sshCommand is extended", env.get("GIT_SSH_COMMAND") == "ssh -i /c -o BatchMode=yes", repr(env.get("GIT_SSH_COMMAND")))
env = fetch_env({"GIT_SSH": "my-ssh"})
check("GIT_SSH alone: GIT_SSH_COMMAND is left unset", "GIT_SSH_COMMAND" not in env, repr(env.get("GIT_SSH_COMMAND")))
check("GIT_SSH alone: still never prompts", env.get("GIT_TERMINAL_PROMPT") == "0" and env.get("GIT_SSH") == "my-ssh", repr(env.get("GIT_TERMINAL_PROMPT")))
env = fetch_env({"GIT_SSH": "my-ssh", "GIT_SSH_COMMAND": "ssh -i /k"})
check("GIT_SSH with GIT_SSH_COMMAND: the command is extended as before", env.get("GIT_SSH_COMMAND") == "ssh -i /k -o BatchMode=yes", repr(env.get("GIT_SSH_COMMAND")))
env = fetch_env({"GIT_SSH": "my-ssh"}, config_value="ssh -i /c")
check("GIT_SSH with core.sshCommand: the config value is extended as before", env.get("GIT_SSH_COMMAND") == "ssh -i /c -o BatchMode=yes", repr(env.get("GIT_SSH_COMMAND")))

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("shared-config fixtures · PASS")
