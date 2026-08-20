"""memfd-script-exec — Execute a script from anonymous memfd."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_script
from fenix.interpreters.registry import get_interpreter, resolve_binary
from fenix.techniques import register

VALID_METHODS = ("shebang", "interpreter-procfs", "fexecve-interpreter")

# Shell payloads (hello_shebang.sh) only match sh/bash for interpreter-procfs / fexecve-interpreter.
_SHELL_INTERPRETERS = frozenset({"sh", "bash", "dash"})
_INTERPRETER_SCRIPTS: dict[str, str] = {
    "python3": "payloads/scripts/hello.py",
    "python": "payloads/scripts/hello.py",
    "perl": "payloads/scripts/hello.pl",
    "php": "payloads/scripts/hello.php",
    "ruby": "payloads/scripts/hello.rb",
    "node": "payloads/scripts/hello.js",
    "nodejs": "payloads/scripts/hello.js",
    "awk": "payloads/scripts/hello.awk",
    "gawk": "payloads/scripts/hello.awk",
    "mawk": "payloads/scripts/hello.awk",
    "lua": "payloads/scripts/hello.lua",
    "lua5.4": "payloads/scripts/hello.lua",
    "lua5.3": "payloads/scripts/hello.lua",
}
# Node resolves /proc/self/fd memfd paths via realpath — often fails; shebang method works.
_NODE_NAMES = frozenset({"node", "nodejs"})


def _shebang_interpreter_path(script_path: str) -> str | None:
    """First absolute binary from #! line, or None if env-based / missing shebang."""
    try:
        head = Path(script_path).read_bytes()[:512]
    except OSError:
        return None
    first = head.split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
    if not first.startswith("#!"):
        return None
    rest = first[2:].strip()
    if not rest or rest.startswith("/usr/bin/env ") or rest.startswith("/bin/env "):
        return None
    token = rest.split()[0]
    return token if token.startswith("/") else None


def _validate_shebang_interpreter(script_path: str | None, method: str) -> None:
    if method != "shebang" or not script_path:
        return
    interp = _shebang_interpreter_path(script_path)
    if not interp or Path(interp).exists():
        return
    base = Path(interp).name.lower()
    hint = ""
    if base in ("gawk", "awk", "mawk", "nawk"):
        hint = (
            " Install gawk or awk (e.g. apt install gawk), or use "
            "--method interpreter-procfs --interpreter awk (FENIX resolves awk/gawk/mawk)."
        )
    raise ValueError(
        f"Shebang interpreter {interp!r} not found on this host (execve errno ENOENT).{hint}"
    )


def _looks_like_shell_script(path: str) -> bool:
    try:
        head = Path(path).read_bytes()[:256].decode("utf-8", errors="replace")
    except OSError:
        return path.endswith(".sh")
    first = head.split("\n", 1)[0].strip().lower()
    if first.startswith("#!") and any(x in first for x in ("sh", "bash", "dash")):
        return True
    return path.endswith(".sh")


def _validate_script_for_interpreter(
    script_path: str | None, interpreter: str | None, method: str
) -> None:
    if not interpreter or not script_path or method == "shebang":
        return
    key = interpreter.lower().split("/")[-1]
    if key in _NODE_NAMES and method in ("interpreter-procfs", "fexecve-interpreter"):
        raise ValueError(
            "Node.js often cannot execute /proc/self/fd/<memfd> (realpath on memfd fails). "
            "Use --method shebang with payloads/scripts/hello.js, or interpreter-exec."
        )
    if _looks_like_shell_script(script_path) and key not in _SHELL_INTERPRETERS:
        hint = _INTERPRETER_SCRIPTS.get(key, "a script written for that interpreter")
        raise ValueError(
            f"{script_path} is a shell script but --interpreter {interpreter!r} was set. "
            f"Use --method shebang for the shell script, --interpreter sh, or e.g. "
            f"--script {hint}"
        )


@register("memfd-script-exec", "Execute script from anonymous memfd")
def run_memfd_script_exec(options: dict[str, Any]) -> int:
    script_file = options.get("script") or options.get("script_file")
    code = options.get("code") or options.get("content")
    name = options.get("name") or "fenix_script"
    method = options.get("method") or "shebang"

    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    if not script_file and not code:
        raise ValueError("memfd-script-exec requires --script or --code")

    resolved_script = str(resolve_script(script_file)) if script_file else None
    interpreter = options.get("interpreter")
    _validate_shebang_interpreter(resolved_script, method)
    _validate_script_for_interpreter(resolved_script, str(interpreter) if interpreter else None, method)

    args = ["--name", str(name), "--method", str(method)]

    if script_file:
        args.extend(["--script-file", resolved_script])
    else:
        args.extend(["--content", str(code)])

    if interpreter:
        spec = get_interpreter(str(interpreter))
        binary = resolve_binary(spec)
        args.extend(["--interpreter", binary])

    return run_helper("memfd-script-exec", args)
