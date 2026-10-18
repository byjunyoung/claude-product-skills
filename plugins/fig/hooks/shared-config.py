#!/usr/bin/env python3
"""SessionStart — keeps a config that is shared through a repository from going quietly stale.

This file lives as a copy in each plugin. Change one and not the other and verify catches it.

A team that runs these skills against one tracker shares one config, and every machine holds
a copy of it. A copy says nothing about its own age: the run succeeds either way, and the
first sign that a machine was working from an old one is the thing it wrote. Anything that
asks the file to declare its own version fails here twice over — a file written before a key
existed cannot say anything about that key, and a person who reads the warning can silence
it by editing the stamp rather than the file.

So nothing is declared. Where the config resolves into a git work tree, that is the team
saying so structurally, and this asks git.

    CLAUDE_SHARED_CONFIG=off     do nothing
                         fetch   look, report, change no file        (default)
                         pull    fast-forward the work tree as well

The default touches no file. Pulling is somebody's decision and is turned on deliberately —
one line in settings.json, which /<plugin>:setup offers to write.

It says nothing when the copy is current. A hook that prints on every session start is
wallpaper by the third day, and the run it needed to be read on is the one it is skipped on.
Two plugins sharing one work tree do not fetch it twice: the stamp is keyed by that tree.
"""
import hashlib, importlib.util, json, os, subprocess, sys, tempfile, time

def plugin_name(here):
    """The plugin these scripts ship in, read from the nearest .claude-plugin/plugin.json above
    `here`. A checkout that happens to sit under a directory called pm/ is still the fig plugin.
    Falls back to the path rule when no manifest is found; never raises."""
    try:
        d = os.path.abspath(here)
        while True:
            manifest = os.path.join(d, ".claude-plugin", "plugin.json")
            if os.path.isfile(manifest):
                with open(manifest, encoding="utf-8") as f:
                    name = json.load(f).get("name")
                if isinstance(name, str) and name:
                    return name
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    except (OSError, ValueError, AttributeError):
        pass
    return "pm" if f"{os.sep}pm{os.sep}" in here else "fig"


HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = plugin_name(HERE)
NAME = "pm-conventions.yaml" if PLUGIN == "pm" else "figma-conventions.yaml"
TTL = 6 * 3600            # a work tree looked at this recently is not looked at again


def resolver():
    path = os.path.join(HERE, "..", "_common", "scripts", "lib", "resolve-config.py")
    spec = importlib.util.spec_from_file_location("resolve_config", os.path.normpath(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def due(root):
    """True where this work tree has not been looked at inside the ttl. The stamp is written
    before the network call, so a machine with no route out is not retried every session."""
    stamp = os.path.join(tempfile.gettempdir(),
                         "claude-shared-config-" + hashlib.sha1(root.encode()).hexdigest()[:16])
    try:
        if time.time() - os.path.getmtime(stamp) < TTL:
            return False
    except OSError:
        pass
    try:
        open(stamp, "w").close()
    except OSError:
        pass
    return True


def main():
    mode = os.environ.get("CLAUDE_SHARED_CONFIG", "fetch").strip().lower()
    if mode == "off":
        return
    mod = resolver()
    st = mod.origin_state(NAME)
    root = st.get("root")
    if not root:
        return                                   # not shared through a repository — nothing to say

    if due(root):
        cmd = ["fetch", "--quiet"] if mode != "pull" or st["dirty"] else ["pull", "--ff-only", "--quiet"]
        try:
            # A hook has no terminal: a credential or host-key prompt would sit there until the
            # timeout, on every session start. Make git fail fast instead of asking.
            env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}
            subprocess.run(["git", "-C", root, *cmd], capture_output=True, timeout=20, env=env)
        except (OSError, subprocess.SubprocessError):
            pass                                 # offline is not an error worth a session's attention
        st = mod.origin_state(NAME)

    if not st.get("behind") and not st.get("dirty"):
        return                                   # current — say nothing

    print(f"Shared config ({NAME}):")
    for line in mod.origin(NAME):
        print(f"  {line}")


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass        # a session must not fail to start over this — including the resolver's
                    # sys.exit() when PyYAML is missing, which Exception does not catch
