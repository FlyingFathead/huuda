from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import BinaryIO

from .errors import CommandFailed, CommandTimedOut


@dataclass(slots=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: bytes
    stderr: bytes
    elapsed: float

    @property
    def stderr_text(self) -> str:
        return self.stderr.decode("utf-8", errors="replace")


class ProcessRunner:
    """Run external commands with bounded waits and reliable cancellation."""

    def __init__(self, *, terminate_grace: float = 1.0) -> None:
        self.terminate_grace = terminate_grace

    def run(
        self,
        args: list[str],
        *,
        stage: str,
        input_data: bytes | None = None,
        timeout: float | None = None,
        stdout: int | BinaryIO | None = subprocess.PIPE,
        check: bool = True,
    ) -> CommandResult:
        start = time.monotonic()
        popen_kwargs: dict[str, object] = {
            "stdin": subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
            "stdout": stdout,
            "stderr": subprocess.PIPE,
        }

        # Isolate children from terminal SIGINT. Huuda receives Ctrl-C and then
        # explicitly terminates the complete child process group. This prevents
        # a wedged audio/TTS backend from trapping the parent in a wait.
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(args, **popen_kwargs)  # type: ignore[arg-type]
        try:
            out, err = proc.communicate(input=input_data, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            self._terminate(proc)
            # Never follow a failed termination with an unbounded communicate().
            # A backend stuck in uninterruptible kernel I/O must not be able to
            # turn Huuda's own timeout path into another infinite wait.
            try:
                proc.communicate(timeout=self.terminate_grace)
            except subprocess.TimeoutExpired:
                pass
            raise CommandTimedOut(stage, timeout or 0) from exc
        except KeyboardInterrupt:
            self._terminate(proc)
            raise

        result = CommandResult(
            args=list(args),
            returncode=proc.returncode,
            stdout=out or b"",
            stderr=err or b"",
            elapsed=time.monotonic() - start,
        )
        if check and result.returncode != 0:
            raise CommandFailed(stage, list(args), result.returncode, result.stderr_text)
        return result

    def _terminate(self, proc: subprocess.Popen[bytes]) -> None:
        if proc.poll() is not None:
            return

        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGTERM)
            else:
                proc.terminate()
        except ProcessLookupError:
            return

        try:
            proc.wait(timeout=self.terminate_grace)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            return

        try:
            proc.wait(timeout=self.terminate_grace)
        except subprocess.TimeoutExpired:
            # Nothing useful remains to do here. The caller must not be held
            # hostage by a backend which cannot be reaped promptly.
            pass
