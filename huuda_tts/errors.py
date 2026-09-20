from __future__ import annotations


class HuudaError(RuntimeError):
    """Base class for user-facing Huuda failures."""


class DependencyError(HuudaError):
    """A required external program or Python module is unavailable."""


class CommandFailed(HuudaError):
    def __init__(self, stage: str, command: list[str], returncode: int, stderr: str = "") -> None:
        self.stage = stage
        self.command = command
        self.returncode = returncode
        self.stderr = stderr.strip()
        detail = f"{stage} failed with exit code {returncode}"
        if self.stderr:
            detail += f": {self.stderr}"
        super().__init__(detail)


class CommandTimedOut(HuudaError):
    def __init__(self, stage: str, timeout: float) -> None:
        self.stage = stage
        self.timeout = timeout
        super().__init__(f"{stage} exceeded {timeout:g} seconds and was terminated")
