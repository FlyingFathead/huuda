from huuda_tts.cli import main


def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "0.1.1" in capsys.readouterr().out


def test_dry_run_without_external_tts(capsys):
    assert main(["--dry-run", "hello", "world"]) == 0
    assert "hello world" in capsys.readouterr().out
