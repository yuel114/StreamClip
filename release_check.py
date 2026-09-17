"""Offline checks for files included in the public Git snapshot."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


ROOT = Path(__file__).resolve().parent
PRIVATE_PARTS = {
    "data", "references", ".learnings", ".impeccable", ".claude", ".codex",
    ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist",
}
PRIVATE_NAMES = {
    "config.json", "appearance.json", "当前会话工作报告.md", "高光选题与文案复核.md",
}
PRIVATE_SUFFIXES = {
    ".exe", ".dll", ".db", ".sqlite", ".sqlite3", ".log", ".pem", ".key",
    ".mp4", ".mkv", ".flv", ".ts", ".mp3", ".wav", ".srt", ".ass", ".zip",
}
PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "service-token": re.compile(
        rb"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{25,}"
        rb"|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})\b"
    ),
    "personal-home-path": re.compile(rb"(?i)[A-Z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+"),
    "personal-email": re.compile(rb"\b[0-9]{5,}@qq\.com\b"),
}


def problems(name: str, content: bytes) -> list[str]:
    path = PurePosixPath(name.lower())
    result = []
    if (
        any(part in PRIVATE_PARTS for part in path.parts)
        or path.name in PRIVATE_NAMES
        or path.suffix in PRIVATE_SUFFIXES
        or (path.name.startswith(".env") and path.name != ".env.example")
        or re.search(r"\.(?:db|sqlite3?)-(?:wal|shm|journal)$", path.name)
        or ("cookie" in path.name and path.suffix == ".txt")
    ):
        result.append("private-or-generated-file")
    if len(content) >= 50 * 1024 * 1024:
        result.append("large-git-blob")
    if b"\0" not in content[:8192]:
        result.extend(label for label, pattern in PATTERNS.items() if pattern.search(content))
    return result


def check_rules() -> None:
    for name in (
        "data/config.json", "backup/app.db-wal", ".env", ".env.local",
        ".learnings/ERRORS.md", "tools/ffmpeg.exe", "session-cookies.txt",
        "当前会话工作报告.md",
    ):
        assert problems(name, b"") == ["private-or-generated-file"], name
    for name in ("app.py", ".env.example", "assets/ui/art-provenance.json", "LICENSE"):
        assert not problems(name, b"")
    assert problems("app.py", ("ghp_" + "a" * 30).encode()) == ["service-token"]
    assert problems("notes.md", ("E:" + "/Users/private/file").encode()) == ["personal-home-path"]
    assert problems("notes.md", ("123456789" + "@qq.com").encode()) == ["personal-email"]
    assert problems("key.txt", ("-----BEGIN " + "PRIVATE KEY-----").encode()) == ["private-key"]
    assert not problems("test.py", b"api_key='offline-test-key'")


def check_release() -> None:
    check_rules()
    assert subprocess.run(["git", "diff", "--quiet", "--"], cwd=ROOT).returncode == 0, (
        "Tracked working files differ from the index; stage the reviewed version before publishing."
    )
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
    ).decode("utf-8").split("\0")
    names = sorted(set(filter(None, names)))
    assert names, "No release files"
    failures = []
    for name in names:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            failures.append(f"{name}: not a regular file")
            continue
        failures.extend(f"{name}: {label}" for label in problems(name, path.read_bytes()))
    assert not failures, "\n".join(failures)

    assert (ROOT / "LICENSE").read_bytes() == (ROOT / "licenses/hikami-go-LICENSE").read_bytes()
    rights = (ROOT / "assets/ui/ASSET_RIGHTS.md").read_text(encoding="utf-8")
    assert "尚未取得" in rights and "不因进入本仓库而获得 GPL" in rights
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/ui/ASSET_RIGHTS.md" in readme and "GPL" in readme
    generation = json.loads((ROOT / "assets/ui/generation-provenance.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "assets/ui/art-provenance.json").read_text(encoding="utf-8"))
    for entry in generation["sources"] + manifest["assets"]:
        file = ROOT / "assets/ui" / entry["file"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"], file.name
    for name in ("wallpaper-studio.png", "wallpaper-ice-studio.png", "character.png"):
        assert f"assets/ui/{name}" in names and name in rights, name
    print(f"Release checks passed: {len(names)} files; private-file rules, license and artwork hashes.")
    print("Artwork redistribution permission remains unresolved; this check does not grant permission.")


if __name__ == "__main__":
    check_release()
