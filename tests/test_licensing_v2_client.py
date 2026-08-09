from __future__ import annotations

import sys
from pathlib import Path
import base64
import hashlib
import json
import time
import unittest

import requests
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa


# Standard-library unittest discovery does not consume pytest's ``pythonpath``
# configuration. Add the repository ``src`` layout explicitly so the documented
# direct unittest command works without shell-specific PYTHONPATH setup.
_TEST_ROOT = Path(__file__).resolve().parents[1]
_TEST_SRC = _TEST_ROOT / "src"
if str(_TEST_SRC) not in sys.path:
    sys.path.insert(0, str(_TEST_SRC))

from vibrapilot.app_config import LICENSING
from vibrapilot.licensing_v2 import LicoraV2Client, LicoraV2Error, generate_device_key_material


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class Response:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class NonJsonResponse:
    def __init__(self, status_code=500):
        self.status_code = status_code

    def json(self):
        raise ValueError("not json")


class StaticSession:
    def __init__(self, *, status_code=403, body=None, exception=None, non_json=False):
        self.status_code = status_code
        self.body = body
        self.exception = exception
        self.non_json = non_json

    def post(self, url, data, headers, timeout, allow_redirects):
        if self.exception is not None:
            raise self.exception
        if self.non_json:
            return NonJsonResponse(self.status_code)
        return Response(self.status_code, self.body or {})


def error_body(code: str, message: str = "Rejected") -> dict:
    return {
        "success": False,
        "protocol": "licora-api-v2",
        "api_version": 2,
        "server_version": "5.2.1",
        "request_id": "feedfacefeedface",
        "code": code,
        "message": message,
        "server_time": int(time.time()),
    }


class FakeLicoraSession:
    def __init__(self):
        self.server_private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        self.device_public = None
        self.device_id = ""
        self.fingerprint = ""
        self.current_refresh = "refresh-token-initial-000000000000000000000001"
        self.revoked = False
        self.counter = 0

    def _access(self) -> str:
        self.counter += 1
        now = int(time.time())
        header = {"typ": "LICORA-V2", "alg": "RS256", "kid": LICENSING.signing_key_id}
        payload = {
            "iss": "licora",
            "aud": "vibrapilot",
            "app_id": "vibrapilot",
            "license_id": 7,
            "device_id": self.device_id,
            "device_credential_id": 9,
            "device_key_fingerprint": self.fingerprint,
            "iat": now,
            "nbf": now - 5,
            "exp": now + 3600,
            "jti": f"{self.counter:032x}",
            "token_version": 2,
        }
        eh = b64url(json.dumps(header, separators=(",", ":")).encode())
        ep = b64url(json.dumps(payload, separators=(",", ":")).encode())
        sig = self.server_private.sign((eh + "." + ep).encode(), padding.PKCS1v15(), hashes.SHA256())
        return eh + "." + ep + "." + b64url(sig)

    @staticmethod
    def _canonical(path, timestamp, nonce, raw, context):
        return (
            "POST\n"
            + path
            + "\n"
            + timestamp
            + "\n"
            + nonce
            + "\n"
            + hashlib.sha256(raw).hexdigest()
            + "\n"
            + context
        ).encode()

    def _verify_proof(self, url, raw, headers, context):
        canonical = self._canonical(
            urlparse(url).path,
            headers["X-Licora-Timestamp"],
            headers["X-Licora-Nonce"],
            raw,
            context,
        )
        sig_text = headers["X-Licora-Device-Signature"]
        pad = "=" * ((4 - len(sig_text) % 4) % 4)
        signature = base64.urlsafe_b64decode(sig_text + pad)
        self.device_public.verify(signature, canonical, ec.ECDSA(hashes.SHA256()))

    @staticmethod
    def _ok(**extra):
        base = {
            "success": True,
            "protocol": "licora-api-v2",
            "api_version": 2,
            "server_version": "5.2.1",
            "request_id": "abcd1234abcd1234",
            "code": "OK",
            "message": "OK",
            "server_time": int(time.time()),
        }
        base.update(extra)
        return base

    def post(self, url, data, headers, timeout, allow_redirects):
        self.assertions = (timeout, allow_redirects)
        raw = bytes(data)
        body = json.loads(raw.decode())
        path = urlparse(url).path
        if path.endswith("/activate.php"):
            self.device_public = serialization.load_pem_public_key(body["device_public_key"].encode())
            self.device_id = body["device_id"]
            normalized = self.device_public.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            self.fingerprint = hashlib.sha256(normalized).hexdigest()
            self._verify_proof(url, raw, headers, "activate:vibrapilot")
            return Response(200, self._ok(
                access_token=self._access(),
                token_type="Bearer",
                expires_in=3600,
                refresh_token=self.current_refresh,
                refresh_expires_at="2026-09-08 00:00:00",
                license={"status": "active", "expires_at": "2026-09-08 00:00:00", "device_limit": 1},
                device={"device_id": self.device_id, "public_key_fingerprint": self.fingerprint},
            ))
        if path.endswith("/refresh.php"):
            self._verify_proof(
                url,
                raw,
                headers,
                "refresh:" + hashlib.sha256(body["refresh_token"].encode()).hexdigest(),
            )
            self.current_refresh = "refresh-token-rotated-000000000000000000000002"
            return Response(200, self._ok(
                access_token=self._access(),
                token_type="Bearer",
                expires_in=3600,
                refresh_token=self.current_refresh,
                refresh_expires_at="2026-09-08 00:00:01",
            ))
        auth = headers["Authorization"].split(" ", 1)[1]
        # Decode the access-token JTI only for this fake server's proof context.
        payload_segment = auth.split(".")[1]
        payload_segment += "=" * ((4 - len(payload_segment) % 4) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_segment).decode())
        self._verify_proof(url, raw, headers, claims["jti"])
        if path.endswith("/deactivate.php"):
            self.revoked = True
            return Response(200, self._ok(message="Device deactivated."))
        if path.endswith("/status.php"):
            if self.revoked:
                return Response(403, {
                    "success": False,
                    "protocol": "licora-api-v2",
                    "api_version": 2,
                    "server_version": "5.2.1",
                    "request_id": "deadbeefdeadbeef",
                    "code": "DEVICE_REVOKED",
                    "message": "Device is revoked.",
                    "server_time": int(time.time()),
                })
            return Response(200, self._ok(
                message="License is active.",
                license={"status": "active", "expires_at": "2026-09-08 00:00:00"},
                device={"device_id": self.device_id, "status": "active"},
                app_id="vibrapilot",
            ))
        raise AssertionError(path)


class LicensingV2ClientTest(unittest.TestCase):
    def test_complete_protocol_lifecycle(self):
        fake = FakeLicoraSession()
        client = LicoraV2Client(app_version="1.0.6.5", timeout=12, session=fake)
        client.server_public_key = fake.server_private.public_key()
        material = generate_device_key_material()
        device_id = "device-0123456789abcdef"

        activated = client.activate(
            license_key="AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD",
            device_id=device_id,
            private_key_pem=material.private_key_pem,
        )
        self.assertEqual(activated["license"]["status"], "active")
        access = activated["access_token"]
        refresh = activated["refresh_token"]

        status = client.status(
            access_token=access,
            device_id=device_id,
            private_key_pem=material.private_key_pem,
        )
        self.assertEqual(status["app_id"], "vibrapilot")

        refreshed = client.refresh(
            refresh_token=refresh,
            device_id=device_id,
            private_key_pem=material.private_key_pem,
        )
        self.assertNotEqual(refreshed["refresh_token"], refresh)
        new_access = refreshed["access_token"]
        client.status(
            access_token=new_access,
            device_id=device_id,
            private_key_pem=material.private_key_pem,
        )
        client.deactivate(
            access_token=new_access,
            device_id=device_id,
            private_key_pem=material.private_key_pem,
        )
        self.assertTrue(fake.revoked)
        with self.assertRaises(LicoraV2Error) as revoked:
            client.status(
                access_token=new_access,
                device_id=device_id,
                private_key_pem=material.private_key_pem,
            )
        self.assertEqual(revoked.exception.code, "DEVICE_REVOKED")
        self.assertEqual(fake.assertions, (12.0, False))

    def test_stable_server_error_codes_are_preserved(self):
        material = generate_device_key_material()
        cases = [
            ("INVALID_LICENSE", 403),
            ("APP_NOT_ALLOWED", 403),
            ("APP_VERSION_UNSUPPORTED", 426),
            ("DEVICE_LIMIT_REACHED", 409),
            ("REFRESH_TOKEN_REUSED", 401),
            ("RATE_LIMITED", 429),
        ]
        for code, http_status in cases:
            with self.subTest(code=code):
                client = LicoraV2Client(
                    app_version="1.0.6.5",
                    session=StaticSession(
                        status_code=http_status, body=error_body(code)
                    ),
                )
                with self.assertRaises(LicoraV2Error) as raised:
                    client.activate(
                        license_key="AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD",
                        device_id="device-0123456789abcdef",
                        private_key_pem=material.private_key_pem,
                    )
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(raised.exception.http_status, http_status)
                self.assertEqual(raised.exception.request_id, "feedfacefeedface")

    def test_network_redirect_non_json_and_protocol_fail_closed(self):
        material = generate_device_key_material()
        device_id = "device-0123456789abcdef"
        license_key = "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD"

        scenarios = [
            (
                "network",
                StaticSession(exception=requests.ConnectionError("offline")),
                "NETWORK_ERROR",
            ),
            ("redirect", StaticSession(status_code=302, body={}), "INVALID_SERVER_RESPONSE"),
            (
                "non-json",
                StaticSession(status_code=500, non_json=True),
                "INVALID_SERVER_RESPONSE",
            ),
            (
                "protocol",
                StaticSession(
                    status_code=200,
                    body={
                        "success": True,
                        "protocol": "wrong",
                        "api_version": 2,
                        "code": "OK",
                    },
                ),
                "INVALID_SERVER_RESPONSE",
            ),
        ]
        for name, session, expected in scenarios:
            with self.subTest(name=name):
                client = LicoraV2Client(app_version="1.0.6.5", session=session)
                with self.assertRaises(LicoraV2Error) as raised:
                    client.activate(
                        license_key=license_key,
                        device_id=device_id,
                        private_key_pem=material.private_key_pem,
                    )
                self.assertEqual(raised.exception.code, expected)


if __name__ == "__main__":
    unittest.main()
