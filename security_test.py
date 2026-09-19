"""Offline checks for Windows credential protection and legacy migration."""

import base64
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import app


def legacy_cookie(value):
    # Reproduce only the retired format, so the upgrade remains testable.
    plain, nonce, key = value.encode("utf-8"), bytes(range(16)), app._local_secret_key()
    stream = b"".join(hashlib.sha256(key + nonce + i.to_bytes(4, "big")).digest()
                      for i in range((len(plain) + 31) // 32))
    cipher = bytes(a ^ b for a, b in zip(plain, stream))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    return "v1:" + base64.urlsafe_b64encode(nonce + cipher + tag).decode("ascii")


def run():
    secret = "offline-private-value"
    protected = app.encrypt_secret(secret)
    assert protected.startswith("dpapi:") and secret not in protected
    assert app.decrypt_cookie(protected) == secret
    assert app.encrypt_secret(secret) != protected
    assert app.encrypt_secret("") == app.decrypt_cookie("") == ""
    assert app.decrypt_cookie("dpapi:invalid") == ""
    data = bytearray(base64.b64decode(protected[6:]))
    data[-1] ^= 1
    assert app.decrypt_cookie("dpapi:" + base64.b64encode(data).decode("ascii")) == ""
    with patch.object(app, "_local_secret_key", side_effect=AssertionError("legacy key used for new data")):
        assert app.decrypt_cookie(app.encrypt_secret(secret)) == secret
    with tempfile.TemporaryDirectory(prefix="streamclip-secrets-") as folder:
        root = Path(folder)
        path = root / "config.json"
        values = {name: "offline-" + name for name in app.SECRET_SETTING_FIELDS}
        legacy = dict(values, base_dir=folder, settings_version=11, publish_visibility="self",
                      unknown_future_field={"keep": True})
        path.write_text(json.dumps(legacy), encoding="utf-8")
        loaded = app.Settings.load(path)
        disk = json.loads(path.read_text(encoding="utf-8"))
        for name, value in values.items():
            assert getattr(loaded, name) == value
            assert value not in path.read_text(encoding="utf-8") and disk[name].startswith("dpapi:")
        assert disk["unknown_future_field"] == legacy["unknown_future_field"]
        assert disk["publish_visibility"] == "self"
        original = path.read_bytes()
        assert app.Settings.load(path).llm_api_key == values["llm_api_key"]
        assert path.read_bytes() == original, "already migrated files must not be rewritten on read"
        with patch.object(app, "_dpapi", side_effect=OSError("unavailable")):
            try:
                loaded.save(path)
            except OSError:
                pass
            else:
                raise AssertionError("failed encryption silently saved credentials")
            assert path.read_bytes() == original
            try:
                app.Settings.load(path)
            except RuntimeError as exc:
                assert "dashscope_api_key" in str(exc) and secret not in str(exc)
            else:
                raise AssertionError("unreadable protected key was silently erased")
            assert path.read_bytes() == original
        loaded.llm_api_key = ""
        loaded.save(path)
        assert json.loads(path.read_text(encoding="utf-8"))["llm_api_key"] == ""
        assert app.Settings.load(path).llm_api_key == ""
        loaded.bili_cookie_ciphertext = "dpapi:unreadable-legacy-login"
        loaded.save(path)
        unreadable = app.Settings.load(path)
        assert unreadable.bili_cookie == ""
        unreadable.save(path)
        assert json.loads(path.read_text(encoding="utf-8"))["bili_cookie_ciphertext"] == loaded.bili_cookie_ciphertext

        db_path = root / "accounts.db"
        db = app.Database(db_path)
        account_id = db.upsert_cookie_account("legacy", "SESSDATA=offline-cookie; bili_jct=test", "download")
        old = legacy_cookie("SESSDATA=offline-cookie; bili_jct=test")
        assert app.decrypt_cookie(old) == "SESSDATA=offline-cookie; bili_jct=test"
        broken_id = db.upsert_cookie_account("unreadable", "test")
        with db._connect() as connection:
            connection.execute("UPDATE cookie_accounts SET cookie_ciphertext=? WHERE id=?", (old, account_id))
            connection.execute("UPDATE cookie_accounts SET cookie_ciphertext='v1:broken' WHERE id=?", (broken_id,))
            before = dict(connection.execute("SELECT * FROM cookie_accounts WHERE id=?", (account_id,)).fetchone())
        with patch.object(app, "_dpapi", side_effect=OSError("unavailable")):
            try:
                app.Database(db_path)
            except OSError:
                pass
            else:
                raise AssertionError("account migration ignored encryption failure")
        with db._connect() as connection:
            assert connection.execute("SELECT cookie_ciphertext FROM cookie_accounts WHERE id=?", (account_id,)).fetchone()[0] == old
        migrated = app.Database(db_path)
        assert migrated.cookie_for_account(account_id, "download") == "SESSDATA=offline-cookie; bili_jct=test"
        with migrated._connect() as connection:
            after = dict(connection.execute("SELECT * FROM cookie_accounts WHERE id=?", (account_id,)).fetchone())
            assert connection.execute("SELECT cookie_ciphertext FROM cookie_accounts WHERE id=?", (broken_id,)).fetchone()[0] == "v1:broken"
        assert after.pop("cookie_ciphertext").startswith("dpapi:")
        before.pop("cookie_ciphertext")
        assert after == before, "credential migration changed account identity or state"
        # Force page relocation: UPDATE alone can leave v1 blobs in free cells.
        pages = app.Database(root / "legacy-pages.db")
        for i in range(30):
            pages.upsert_cookie_account("legacy-" + str(i), "offline")
        with pages._connect() as connection:
            connection.execute("PRAGMA secure_delete=OFF")
            connection.execute("UPDATE cookie_accounts SET cookie_ciphertext=?", (old,))
        app.Database(pages.path)
        assert old.encode("ascii") not in pages.path.read_bytes(), "legacy ciphertext survived in SQLite free pages"
        import quick_ui
        with patch.object(app.sys, "argv", ["app.py"]), patch.object(app.sys, "frozen", False, create=True), \
                patch.object(app, "runtime_root", return_value=root), \
                patch.object(quick_ui, "run", side_effect=RuntimeError("offline startup failure")):
            try:
                app.main()
            except RuntimeError:
                pass
            else:
                raise AssertionError("startup failure was swallowed")
            assert "offline startup failure" in (root / "data/logs/startup-error.log").read_text(encoding="utf-8")
    print("Credential protection checks passed: DPAPI, API keys, migration, tampering and failure preservation")


if __name__ == "__main__":
    run()
