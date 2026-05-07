from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from auth_backend import Database, make_handler  # noqa: E402


class AuthBackendApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        db = Database(Path(cls.tmpdir.name) / "auth-test.sqlite3")
        db.initialize()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db))
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.tmpdir.cleanup()

    def request(self, method: str, path: str, body: dict | None = None, token: str | None = None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read()
            exc.close()
            return exc.code, json.loads(body.decode("utf-8"))

    def test_registered_user_flow(self) -> None:
        status, payload = self.request(
            "POST",
            "/api/auth/register",
            {"username": "student01", "password": "secret123"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(payload["success"])
        token = payload["data"]["token"]
        self.assertFalse(payload["data"]["user"]["anonymous"])
        self.assertTrue(payload["data"]["permissions"]["canSaveLongTermHistory"])

        status, payload = self.request("GET", "/api/auth/me", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["user"]["username"], "student01")

        status, payload = self.request(
            "POST",
            "/api/auth/login",
            {"username": "student01", "password": "secret123"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["data"]["token"])

        status, payload = self.request(
            "POST",
            "/api/auth/register",
            {"username": "student01", "password": "another123"},
        )
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "USERNAME_EXISTS")

    def test_anonymous_user_permissions(self) -> None:
        status, payload = self.request("POST", "/api/auth/anonymous", {})
        self.assertEqual(status, 201)
        token = payload["data"]["token"]
        self.assertTrue(payload["data"]["user"]["anonymous"])
        self.assertFalse(payload["data"]["privacy"]["allowHistorySave"])
        self.assertFalse(payload["data"]["permissions"]["canSaveLongTermHistory"])

        status, payload = self.request(
            "PATCH",
            "/api/user/privacy",
            {"allowHistorySave": True},
            token=token,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["code"], "ANONYMOUS_HISTORY_FORBIDDEN")

        status, payload = self.request("POST", "/api/auth/logout", token=token)
        self.assertEqual(status, 200)
        self.assertTrue(payload["data"]["loggedOut"])

        status, payload = self.request("GET", "/api/auth/me", token=token)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
