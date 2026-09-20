import sys
import time

import pytest

from huuda_tts.errors import CommandTimedOut
from huuda_tts.process import ProcessRunner


def test_process_timeout_is_bounded():
    runner = ProcessRunner(terminate_grace=0.2)
    started = time.monotonic()
    with pytest.raises(CommandTimedOut):
        runner.run(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stage="test sleeper",
            timeout=0.2,
        )
    assert time.monotonic() - started < 3


def test_process_captures_stderr():
    runner = ProcessRunner()
    result = runner.run(
        [sys.executable, "-c", "import sys; print('hello', file=sys.stderr)"],
        stage="test stderr",
        timeout=2,
    )
    assert "hello" in result.stderr_text
