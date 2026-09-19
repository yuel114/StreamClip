"""Offline release, download and real Windows atomic replacement regression checks."""

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from unittest.mock import patch
import zipfile

import app_updates as updates


def release(version="2099.01.01", **changes):
    tag = "v" + version
    result = {"tag_name": tag, "published_at": "2026-09-19T05:06:54Z", "draft": False, "prerelease": False,
              "body": "## 离线测试版本\n\n- 修复离线测试问题。\n- 保留所有测试数据。",
              "assets": [{"name": f"StreamClip-{tag}-windows-x64.zip", "size": 512,
                          "digest": "sha256:" + "a" * 64,
                          "browser_download_url": f"{updates.RELEASES_URL}/download/{tag}/StreamClip-{tag}-windows-x64.zip"}]}
    return result | changes


def package_bytes(names=("StreamClip.exe",), executable=None):
    if executable is None:
        header = bytearray(128)
        header[:2] = b"MZ"
        struct.pack_into("<I", header, 60, 80)
        header[80:86] = b"PE\0\0\x64\x86"
        executable = bytes(header)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.writestr(name, executable)
        bundle.writestr("data/config.json", "must never be extracted")
    return buffer.getvalue()


def rejected(work, text=""):
    try:
        work()
    except (ValueError, updates.DownloadCancelled, zipfile.BadZipFile) as exc:
        assert not text or text in str(exc), str(exc)
    else:
        raise AssertionError("Unsafe update operation was accepted")


def check_windows_installer(folder):
    if os.name != "nt":
        return
    helper = Path(updates.__file__).with_name("install-update.ps1")
    root = folder / "安装 [test] ' 空格"
    root.mkdir()
    target = root / "StreamClip.exe"
    stage = root / "data/updates/download-test"
    stage.mkdir(parents=True)
    staged = stage / target.name
    plan = stage / "plan.json"
    plan_data = {"target": str(target), "staged": str(staged), "sha256": hashlib.sha256(b"new exe").hexdigest(),
                 "pid": 2147483600, "version": "2099.01.01"}
    source = str(helper).replace("'", "''")
    job_path = str(plan).replace("'", "''")
    # Only launching is intercepted; validation, hashing, backup, replacement and rollback are real.
    command = f"""
    $ErrorActionPreference='Stop'
    . '{source}'
    $script:launchCount=0
    function Start-Process {{
        param($FilePath,$WorkingDirectory,$WindowStyle)
        $script:launchCount++
        if ($env:UPDATE_TEST_RESTART_FAIL -eq '1' -and $script:launchCount -eq 1) {{ throw 'synthetic restart failure' }}
    }}
    try {{ Install-StreamClipUpdate '{job_path}' }} catch {{ Write-Output $_.Exception.Message }}
    """
    powershell = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
    for mode in ("success", "hash", "restart", "outside"):
        target.write_bytes(b"old exe")
        staged.write_bytes(b"new exe" if mode != "hash" else b"corrupted exe")
        backup = stage / "StreamClip.before.exe"
        backup.unlink(missing_ok=True)
        job = dict(plan_data)
        if mode == "outside":
            job["staged"] = str(root / "outside.exe")
        plan.write_text(json.dumps(job), encoding="utf-8")
        env = dict(os.environ, UPDATE_TEST_RESTART_FAIL="1" if mode == "restart" else "0")
        completed = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                                   env=env, capture_output=True, timeout=20)
        assert completed.returncode == 0, completed.stderr
        if mode == "success":
            assert target.read_bytes() == b"new exe" and backup.read_bytes() == b"old exe", completed.stdout.decode("utf-8", errors="replace")
        else:
            assert target.read_bytes() == b"old exe", mode
        if mode != "outside":
            result = json.loads((root / "data/updates/last-result.json").read_text(encoding="utf-8-sig"))
            assert result["success"] is (mode == "success")


def run():
    assert updates.version_key("v2026.09.19.10") > updates.version_key("2026.09.19.2")
    assert updates.version_key("2026.09.19") == updates.version_key("2026.09.19.0")
    for bad in ("", "latest", "2026.9", "v2026.09.19-beta", "2026.09.19.2.1", "../../2.0.0"):
        rejected(lambda: updates.version_key(bad))
    assert len(updates.release_history()) >= 4
    rows = updates.parse_releases([release("2026.09.19"), release(), release("2100.1.1", prerelease=True),
                                   release("2101.1.1", draft=True), release("unknown")])
    assert [row["version"] for row in rows] == ["2099.01.01", "2026.09.19"]
    assert len([row for row in updates.release_history(rows) if row["current"]]) == 1
    assert "修复离线测试" in rows[0]["summary"] and rows[0]["package"]
    for invalid in (None, {}, [1]):
        rejected(lambda: updates.parse_releases(invalid))
    for field, value in (("digest", None), ("digest", "md5:bad"), ("size", True), ("size", -1),
                         ("browser_download_url", "https://example.org/payload.exe")):
        item = release()
        item["assets"][0][field] = value
        assert not updates.parse_releases([item])[0]["package"]
    for url in ("http://api.github.com/" + updates.REPOSITORY, "https://evil.test/update",
                "file:///C:/payload", "https://user:secret@api.github.com/repos/" + updates.REPOSITORY + "/releases",
                "https://github.com/other/project/releases/download/v1/file", updates.API_URL + "#bad",
                "https://github.com/" + updates.REPOSITORY + "/releases/download/../evil"):
        rejected(lambda: updates.trusted_url(url))
    redirect = updates.ReleaseRedirect()
    request = urllib.request.Request(updates.API_URL)
    rejected(lambda: redirect.redirect_request(request, None, 302, "", {}, "https://evil.test/payload"))
    response = redirect.redirect_request(request, None, 302, "", {}, "https://release-assets.githubusercontent.com/test?sig=public")
    assert response.full_url.startswith("https://release-assets.githubusercontent.com/")
    with patch.object(updates, "open_release", return_value=io.BytesIO(json.dumps([release()]).encode())):
        assert updates.fetch_releases()[0]["version"] == "2099.01.01"
    with patch.object(updates, "open_release", return_value=io.BytesIO(b"<html>offline</html>")):
        rejected(updates.fetch_releases, "无法解析")
    with patch.object(urllib.request.OpenerDirector, "open", side_effect=urllib.error.HTTPError(updates.API_URL, 403, "", {}, None)):
        rejected(lambda: updates.open_release(updates.API_URL), "请求受限")

    cache = Path(os.environ.get("LIVECLIP_UI_TEST_OUTPUT", str(Path(tempfile.gettempdir()) / "StreamClip" / "update-check")))
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as directory:
        root = Path(directory)
        (root / "data").mkdir()
        protected = root / "data/config.json"
        protected.write_bytes(b"offline user settings")
        executable = root / "StreamClip.exe"
        executable.write_bytes(b"old exe")
        cancel = threading.Event()

        def download(data, **changes):
            row = copy.deepcopy(rows[0])
            row["package"].update(size=len(data), sha256=hashlib.sha256(data).hexdigest(), **changes)
            with patch.object(updates, "open_release", return_value=io.BytesIO(data)):
                return updates.download_release(row, root, cancel, lambda *_: None)

        staged = download(package_bytes())
        assert updates.file_hash(staged["path"]) == staged["sha256"]
        assert executable.read_bytes() == b"old exe" and protected.read_bytes() == b"offline user settings"
        assert not (Path(staged["path"]).parent / "data").exists()
        good = package_bytes()
        row = copy.deepcopy(rows[0])
        row["package"].update(size=len(good), sha256="0" * 64)
        with patch.object(updates, "open_release", return_value=io.BytesIO(good)):
            rejected(lambda: updates.download_release(row, root, cancel, lambda *_: None), "校验失败")
        for data in (b"broken zip", package_bytes(("../StreamClip.exe",)), package_bytes(("/StreamClip.exe",)),
                     package_bytes(("a/StreamClip.exe", "b/StreamClip.exe")), package_bytes(executable=b"not executable")):
            rejected(lambda: download(data))
        cancel.set()
        rejected(lambda: download(good))
        cancel.clear()
        assert len(list((root / "data/updates").iterdir())) == 1, "Failed downloads left files behind"
        with patch.object(updates, "VERSION", "2099.01.01"):
            rejected(lambda: download(good), "只能安装")
        with patch.object(updates.sys, "frozen", False, create=True):
            rejected(lambda: updates.launch_installer(staged), "源码版")
        check_windows_installer(root)
    print("Update checks passed: release sorting, trust boundaries, cancellation, hash verification, EXE staging, real atomic replacement and rollback")


if __name__ == "__main__":
    run()
