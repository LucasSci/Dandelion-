from __future__ import annotations

import json
import os
import resource
import subprocess
import textwrap
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class SandboxPolicy:
    cpu_time_seconds: int = 2
    memory_mb: int = 128
    max_open_files: int = 64
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allow_subprocess: bool = False


class SandboxExecutionError(RuntimeError):
    pass


def _apply_limits(policy: SandboxPolicy) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_time_seconds, policy.cpu_time_seconds))
    memory_bytes = policy.memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (policy.max_open_files, policy.max_open_files))


def _build_guard(policy: SandboxPolicy) -> str:
    guards = []
    if not policy.allow_network:
        guards.append(
            textwrap.dedent(
                """
                import socket
                class _BlockedSocket(socket.socket):
                    def __init__(self, *args, **kwargs):
                        raise RuntimeError("Network access is disabled in sandbox")
                socket.socket = _BlockedSocket
                """
            )
        )
    if not policy.allow_subprocess:
        guards.append(
            textwrap.dedent(
                """
                import subprocess
                def _blocked(*_args, **_kwargs):
                    raise RuntimeError("Subprocess execution is disabled in sandbox")
                subprocess.Popen = _blocked
                subprocess.run = _blocked
                """
            )
        )
    if not policy.allow_filesystem_write:
        guards.append(
            textwrap.dedent(
                """
                import builtins
                _orig_open = builtins.open
                def _guarded_open(file, mode='r', *args, **kwargs):
                    if any(flag in mode for flag in ('w', 'a', 'x', '+')):
                        raise RuntimeError("Filesystem writes are disabled in sandbox")
                    return _orig_open(file, mode, *args, **kwargs)
                builtins.open = _guarded_open
                """
            )
        )
    return "\n".join(guards)


def run_hook_in_sandbox(
    module: str,
    func: str,
    payload: Mapping[str, Any],
    policy: Optional[SandboxPolicy] = None,
    working_dir: Optional[str] = None,
    extra_env: Optional[Mapping[str, str]] = None,
) -> Any:
    policy = policy or SandboxPolicy()
    guard = _build_guard(policy)
    runner = textwrap.dedent(
        f"""
        import json
        {guard}
        from {module} import {func}

        payload = json.loads(input())
        result = {func}(payload)
        print(json.dumps(result))
        """
    )

    env = {
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
    }
    if extra_env:
        env.update(extra_env)

    try:
        completed = subprocess.run(
            [os.environ.get("PYTHON_EXECUTABLE", "python"), "-I", "-c", runner],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=working_dir,
            env=env,
            check=False,
            preexec_fn=lambda: _apply_limits(policy),
            timeout=policy.cpu_time_seconds + 1,
        )
    except subprocess.TimeoutExpired as exc:
        raise SandboxExecutionError("Sandbox execution timed out") from exc

    if completed.returncode != 0:
        raise SandboxExecutionError(
            f"Sandboxed hook failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SandboxExecutionError("Sandboxed hook returned invalid JSON") from exc
