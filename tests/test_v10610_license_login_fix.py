from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot import backend


LICENSE_A = "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD"


class FakeSettings:
    def get(self, key, default=None):
        return 2 if key == "request_timeout" else default


class BaseClient:
    activate_calls: list[str] = []
    deactivate_calls: list[str] = []

    def __init__(self, *, app_version, timeout):
        self.app_version = app_version
        self.timeout = timeout

    @classmethod
    def reset(cls):
        cls.activate_calls = []
        cls.deactivate_calls = []

    def verify_access_token(self, token, *, expected_device_id=None, expected_device_fingerprint=None):
        if token == "expired":
            raise backend.LicoraV2Error("TOKEN_EXPIRED", "expired")
        return SimpleNamespace(expires_at=int(time.time()) + 3600, raw={"exp": int(time.time()) + 3600})

    def _success(self, device_id, private_key_pem):
        material = backend.load_device_key_material(private_key_pem)
        return {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "refresh_expires_at": "2026-09-08 00:00:00",
            "license": {"status": "active", "expires_at": "2026-09-08 00:00:00"},
            "verified_claims": {
                "exp": int(time.time()) + 3600,
                "device_id": device_id,
                "device_key_fingerprint": material.public_key_fingerprint,
            },
        }

    def activate(self, *, license_key, device_id, private_key_pem):
        type(self).activate_calls.append(device_id)
        return self._success(device_id, private_key_pem)

    def status(self, *, access_token, device_id, private_key_pem):
        return {"license": {"status": "active", "expires_at": "2026-09-08 00:00:00"}}

    def refresh(self, *, refresh_token, device_id, private_key_pem):
        return self._success(device_id, private_key_pem)

    def deactivate(self, *, access_token, device_id, private_key_pem):
        type(self).deactivate_calls.append(device_id)
        return {"success": True}


class MismatchThenSuccessClient(BaseClient):
    def activate(self, *, license_key, device_id, private_key_pem):
        type(self).activate_calls.append(device_id)
        if len(type(self).activate_calls) == 1:
            raise backend.LicoraV2Error(
                "DEVICE_KEY_MISMATCH",
                "Device key does not match the registered device.",
                http_status=409,
            )
        return self._success(device_id, private_key_pem)


class RevokedThenSuccessClient(BaseClient):
    def activate(self, *, license_key, device_id, private_key_pem):
        type(self).activate_calls.append(device_id)
        if len(type(self).activate_calls) == 1:
            raise backend.LicoraV2Error("DEVICE_REVOKED", "Device is revoked.", http_status=403)
        return self._success(device_id, private_key_pem)


class MismatchThenLimitClient(BaseClient):
    def activate(self, *, license_key, device_id, private_key_pem):
        type(self).activate_calls.append(device_id)
        if len(type(self).activate_calls) == 1:
            raise backend.LicoraV2Error("DEVICE_KEY_MISMATCH", "mismatch", http_status=409)
        raise backend.LicoraV2Error("DEVICE_LIMIT_REACHED", "limit", http_status=409)


class BlockingDeactivateClient(BaseClient):
    entered = threading.Event()
    release = threading.Event()
    activate_entered = threading.Event()

    def deactivate(self, *, access_token, device_id, private_key_pem):
        type(self).entered.set()
        type(self).release.wait(timeout=5)
        return super().deactivate(
            access_token=access_token,
            device_id=device_id,
            private_key_pem=private_key_pem,
        )

    def activate(self, *, license_key, device_id, private_key_pem):
        type(self).activate_entered.set()
        return super().activate(
            license_key=license_key,
            device_id=device_id,
            private_key_pem=private_key_pem,
        )


class RevokedStatusThenRecoveryClient(RevokedThenSuccessClient):
    def status(self, *, access_token, device_id, private_key_pem):
        raise backend.LicoraV2Error("DEVICE_REVOKED", "Device is revoked.", http_status=403)


class V10610LicenseLoginFixTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.session = root / "durable" / "license.json"
        self.identity = root / "durable" / "device_identity.json"
        self.legacy = root / "legacy" / "license.json"
        self.patches = [
            patch.object(backend, "LICENSE_FILE", self.session),
            patch.object(backend, "DEVICE_IDENTITY_FILE", self.identity),
            patch.object(backend, "LEGACY_LICENSE_FILE", self.legacy),
            patch.object(backend, "_current_machine_anchor", lambda: "machine-anchor"),
            patch.object(
                backend,
                "_protect_local_secret",
                lambda value: base64.b64encode(value.encode()).decode() if value else "",
            ),
            patch.object(
                backend,
                "_unprotect_local_secret",
                lambda value: base64.b64decode(value.encode()).decode() if value else "",
            ),
            patch.object(backend, "LicoraV2Client", BaseClient),
        ]
        for item in self.patches:
            item.start()
        BaseClient.reset()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_legacy_install_relative_cache_migrates_to_durable_state_and_identity(self):
        material = backend.generate_device_key_material()
        self.legacy.parent.mkdir(parents=True, exist_ok=True)
        self.legacy.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "protocol": "licora-api-v2",
                    "app_id": "vibrapilot",
                    "license_key_protected": base64.b64encode(LICENSE_A.encode()).decode(),
                    "license_hash": hashlib.sha256(LICENSE_A.encode()).hexdigest(),
                    "user_email": "user@example.com",
                    "device_id": backend._legacy_device_id(),
                    "device_private_key_protected": base64.b64encode(
                        material.private_key_pem.encode()
                    ).decode(),
                    "device_public_key_fingerprint": material.public_key_fingerprint,
                    "access_token_protected": "",
                    "refresh_token_protected": "",
                    "access_expires_at": 0,
                }
            ),
            encoding="utf-8",
        )

        manager = backend.LicenseManager(FakeSettings())
        self.assertTrue(self.session.is_file())
        self.assertTrue(self.identity.is_file())
        self.assertEqual(manager.license_key, LICENSE_A)
        self.assertEqual(manager.device_private_key_pem, material.private_key_pem)
        identity = json.loads(self.identity.read_text(encoding="utf-8"))
        self.assertEqual(identity["device_id"], backend._legacy_device_id())
        self.assertTrue(identity["device_private_key_protected"])

    def test_corrupt_session_cache_does_not_destroy_durable_device_identity(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, message = manager.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        device_id = manager.device_id()
        private_key = manager.device_private_key_pem
        self.session.write_text("{broken", encoding="utf-8")

        restored = backend.LicenseManager(FakeSettings())
        self.assertEqual(restored.device_id(), device_id)
        self.assertEqual(restored.device_private_key_pem, private_key)
        self.assertFalse(restored.license_key)
        ok, message = restored.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        self.assertEqual(restored.device_id(), device_id)

    def test_device_key_mismatch_rotates_persisted_device_id_and_recovers_once(self):
        MismatchThenSuccessClient.reset()
        with patch.object(backend, "LicoraV2Client", MismatchThenSuccessClient):
            manager = backend.LicenseManager(FakeSettings())
            original = manager.device_id()
            ok, message = manager.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        self.assertEqual(len(MismatchThenSuccessClient.activate_calls), 2)
        self.assertEqual(MismatchThenSuccessClient.activate_calls[0], original)
        self.assertNotEqual(MismatchThenSuccessClient.activate_calls[1], original)
        self.assertEqual(manager.device_id(), MismatchThenSuccessClient.activate_calls[1])
        identity = json.loads(self.identity.read_text(encoding="utf-8"))
        self.assertEqual(identity["device_id"], manager.device_id())

    def test_revoked_device_id_rotates_and_recovers_for_same_license(self):
        RevokedThenSuccessClient.reset()
        with patch.object(backend, "LicoraV2Client", RevokedThenSuccessClient):
            manager = backend.LicenseManager(FakeSettings())
            original = manager.device_id()
            ok, message = manager.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        self.assertEqual(len(RevokedThenSuccessClient.activate_calls), 2)
        self.assertNotEqual(manager.device_id(), original)

    def test_revoked_status_drops_stale_tokens_and_reaches_activation_recovery(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate(LICENSE_A, "")
        self.assertTrue(ok)
        old_id = manager.device_id()

        RevokedStatusThenRecoveryClient.reset()
        with patch.object(backend, "LicoraV2Client", RevokedStatusThenRecoveryClient):
            ok, message = manager.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        self.assertNotEqual(manager.device_id(), old_id)
        self.assertEqual(len(RevokedStatusThenRecoveryClient.activate_calls), 2)

    def test_mismatch_recovery_reports_stale_device_when_license_limit_blocks_new_id(self):
        MismatchThenLimitClient.reset()
        with patch.object(backend, "LicoraV2Client", MismatchThenLimitClient):
            manager = backend.LicenseManager(FakeSettings())
            original = manager.device_id()
            ok, message = manager.validate(LICENSE_A, "")
        self.assertFalse(ok)
        self.assertEqual(len(MismatchThenLimitClient.activate_calls), 2)
        self.assertNotEqual(manager.device_id(), original)
        self.assertIn("stale registered device", message.lower())
        self.assertIn("DEVICE_LIMIT_REACHED", message)

    def test_confirmed_logout_rotates_revoked_device_id_before_same_license_relogin(self):
        BaseClient.reset()
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate(LICENSE_A, "")
        self.assertTrue(ok)
        old_id = manager.device_id()
        manager.logout()
        self.assertTrue(manager._remote_logout_done.wait(timeout=2))
        self.assertNotEqual(manager.device_id(), old_id)
        self.assertIn(old_id, BaseClient.deactivate_calls)

        ok, message = manager.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        self.assertEqual(BaseClient.activate_calls[-1], manager.device_id())

    def test_relogin_cannot_overtake_background_logout_deactivation(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate(LICENSE_A, "")
        self.assertTrue(ok)

        BlockingDeactivateClient.entered = threading.Event()
        BlockingDeactivateClient.release = threading.Event()
        BlockingDeactivateClient.activate_entered = threading.Event()
        BlockingDeactivateClient.reset()
        with patch.object(backend, "LicoraV2Client", BlockingDeactivateClient):
            manager.logout()
            self.assertTrue(BlockingDeactivateClient.entered.wait(timeout=1))
            result = {}
            worker = threading.Thread(
                target=lambda: result.setdefault("value", manager.validate(LICENSE_A, ""))
            )
            worker.start()
            time.sleep(0.15)
            self.assertFalse(
                BlockingDeactivateClient.activate_entered.is_set(),
                "new activation overtook the pending remote logout",
            )
            BlockingDeactivateClient.release.set()
            worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertTrue(result["value"][0], result["value"][1])

    def test_validate_rechecks_pending_logout_after_validation_lock_acquisition(self):
        source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        validate_source = source[source.index("    def validate(self, license_key:"):source.index("    def is_activated(self)")]
        validation_lock = validate_source.index("with self._validation_lock:")
        second_check = validate_source.index("if not self._remote_logout_done.is_set():", validation_lock)
        generation_snapshot = validate_source.index("generation = self._state_generation", validation_lock)
        self.assertLess(validation_lock, second_check)
        self.assertLess(second_check, generation_snapshot)

    def test_transient_status_failure_keeps_current_verified_access_state(self):
        class NetworkStatusClient(BaseClient):
            def status(self, *, access_token, device_id, private_key_pem):
                raise backend.LicoraV2Error("NETWORK_ERROR", "offline")

        manager = backend.LicenseManager(FakeSettings())
        ok, message = manager.validate(LICENSE_A, "")
        self.assertTrue(ok, message)
        original_access = manager.access_token
        with patch.object(backend, "LicoraV2Client", NetworkStatusClient):
            ok, message = manager.validate(LICENSE_A, "")
        self.assertFalse(ok)
        self.assertEqual(manager._last_validation_code, "NETWORK_ERROR")
        self.assertEqual(manager.access_token, original_access)
        self.assertTrue(manager.is_activated())

    def test_transient_recheck_codes_preserve_only_still_valid_local_session(self):
        for code in [
            "NETWORK_ERROR",
            "INVALID_SERVER_RESPONSE",
            "RATE_LIMITED",
            "API_V2_NOT_READY",
            "INTERNAL_ERROR",
        ]:
            self.assertTrue(backend.license_validation_failure_is_transient(code), code)
        for code in ["DEVICE_REVOKED", "INVALID_LICENSE", "APP_VERSION_UNSUPPORTED"]:
            self.assertFalse(backend.license_validation_failure_is_transient(code), code)

        ui = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.assertIn("transient_with_valid_token", ui)
        self.assertIn("still_locally_valid = self.license_manager.is_activated()", ui)
        self.assertIn("license_validation_failure_is_transient(validation_code)", ui)


if __name__ == "__main__":
    unittest.main()
