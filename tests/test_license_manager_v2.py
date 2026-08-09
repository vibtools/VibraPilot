from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibrapilot import backend


class FakeClient:
    deactivate_calls = 0

    def __init__(self, *, app_version, timeout):
        self.app_version = app_version
        self.timeout = timeout

    def verify_access_token(self, token, *, expected_device_id=None, expected_device_fingerprint=None):
        if token == "expired":
            raise backend.LicoraV2Error("TOKEN_EXPIRED", "expired")
        return SimpleNamespace(expires_at=int(time.time()) + 3600, raw={"exp": int(time.time()) + 3600})

    def activate(self, *, license_key, device_id, private_key_pem):
        material = backend.load_device_key_material(private_key_pem)
        return {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "refresh_expires_at": "2026-09-08 00:00:00",
            "license": {"status": "active", "expires_at": "2026-09-08 00:00:00"},
            "verified_claims": {"exp": int(time.time()) + 3600, "device_key_fingerprint": material.public_key_fingerprint},
        }

    def status(self, *, access_token, device_id, private_key_pem):
        return {"license": {"status": "active", "expires_at": "2026-09-08 00:00:00"}}

    def refresh(self, *, refresh_token, device_id, private_key_pem):
        return {
            "access_token": "access-2",
            "refresh_token": "refresh-2",
            "refresh_expires_at": "2026-09-08 00:00:01",
            "verified_claims": {"exp": int(time.time()) + 3600},
        }

    def deactivate(self, *, access_token, device_id, private_key_pem):
        type(self).deactivate_calls += 1
        return {"success": True}


class FailingActivateClient(FakeClient):
    def activate(self, *, license_key, device_id, private_key_pem):
        raise backend.LicoraV2Error(
            "NETWORK_ERROR", "activation response was lost after request transmission"
        )


class FailingRefreshRecoveryClient(FakeClient):
    def refresh(self, *, refresh_token, device_id, private_key_pem):
        raise backend.LicoraV2Error(
            "NETWORK_ERROR", "refresh response was lost after request transmission"
        )

    def activate(self, *, license_key, device_id, private_key_pem):
        raise backend.LicoraV2Error(
            "NETWORK_ERROR", "activation recovery is unavailable"
        )


class BlockingStatusClient(FakeClient):
    entered = threading.Event()
    release = threading.Event()

    def status(self, *, access_token, device_id, private_key_pem):
        type(self).entered.set()
        type(self).release.wait(timeout=5)
        return {"license": {"status": "active", "expires_at": "2026-09-08 00:00:00"}}


class FakeSettings:
    def get(self, key, default=None):
        return 10 if key == "request_timeout" else default


class LicenseManagerV2Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "license.json"
        self.patches = [
            patch.object(backend, "LICENSE_FILE", self.path),
            patch.object(backend, "LicoraV2Client", FakeClient),
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
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_activation_persists_v2_secrets_protected_and_loads_again(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, message = manager.validate("AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", "user@example.com")
        self.assertTrue(ok, message)
        self.assertTrue(manager.is_activated())
        data = json.loads(self.path.read_text())
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["protocol"], "licora-api-v2")
        self.assertEqual(data["app_id"], "vibrapilot")
        self.assertNotIn("license_key", data)
        self.assertNotIn("device_private_key", data)
        self.assertNotIn("access_token", data)
        self.assertNotIn("refresh_token", data)
        self.assertTrue(data["license_key_protected"])
        self.assertTrue(data["device_private_key_protected"])
        self.assertTrue(data["access_token_protected"])
        self.assertTrue(data["refresh_token_protected"])

        restored = backend.LicenseManager(FakeSettings())
        self.assertEqual(restored.license_key, "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD")
        self.assertTrue(restored.is_activated())
        ok, message = restored.validate(restored.license_key, restored.user_email)
        self.assertTrue(ok, message)
        self.assertIn("verified", message.lower())

    def test_legacy_plaintext_cache_migrates_without_writing_plaintext(self):
        key = "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD"
        self.path.write_text(json.dumps({
            "license_key": key,
            "license_hash": hashlib.sha256(key.encode()).hexdigest(),
            "user_email": "legacy@example.com",
            "activated_until": "2026-09-08",
            "device_id": backend.LicenseManager(FakeSettings()).device_id(),
        }))
        manager = backend.LicenseManager(FakeSettings())
        self.assertEqual(manager.license_key, key)
        self.assertFalse(manager.is_activated())
        ok, message = manager.validate(key, manager.user_email)
        self.assertTrue(ok, message)
        migrated = json.loads(self.path.read_text())
        self.assertEqual(migrated["schema_version"], 2)
        self.assertNotIn("license_key", migrated)
        self.assertTrue(migrated["device_private_key_protected"])

    def test_expired_access_refreshes_and_rotates(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate("AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", "")
        self.assertTrue(ok)
        manager.access_token = "expired"
        manager.save()
        ok, message = manager.validate(manager.license_key, "")
        self.assertTrue(ok, message)
        self.assertEqual(manager.access_token, "access-2")
        self.assertEqual(manager.refresh_token, "refresh-2")



    def test_corrupt_cache_fails_closed(self):
        self.path.write_text("{not-json", encoding="utf-8")
        manager = backend.LicenseManager(FakeSettings())
        self.assertFalse(manager.license_key)
        self.assertFalse(manager.access_token)
        self.assertFalse(manager.refresh_token)
        self.assertFalse(manager.is_activated())

    def test_atomic_save_leaves_no_temporary_license_files(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, message = manager.validate(
            "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", ""
        )
        self.assertTrue(ok, message)
        leftovers = list(self.path.parent.glob(self.path.name + ".tmp.*"))
        self.assertEqual(leftovers, [])

    def test_device_key_is_persisted_before_ambiguous_initial_activation(self):
        with patch.object(backend, "LicoraV2Client", FailingActivateClient):
            manager = backend.LicenseManager(FakeSettings())
            ok, _ = manager.validate(
                "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", ""
            )
        self.assertFalse(ok)
        self.assertTrue(self.path.is_file())
        data = json.loads(self.path.read_text())
        self.assertFalse(data["license_key_protected"])
        self.assertTrue(data["device_private_key_protected"])
        first_key = manager.device_private_key_pem

        restored = backend.LicenseManager(FakeSettings())
        self.assertEqual(restored.device_private_key_pem, first_key)
        self.assertFalse(restored.license_key)

    def test_logout_preserves_persistent_device_key_but_clears_session(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, message = manager.validate(
            "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", ""
        )
        self.assertTrue(ok, message)
        device_key = manager.device_private_key_pem
        fingerprint = manager.device_public_key_fingerprint

        manager.logout()
        data = json.loads(self.path.read_text())
        self.assertFalse(data["license_key_protected"])
        self.assertFalse(data["access_token_protected"])
        self.assertFalse(data["refresh_token_protected"])
        self.assertTrue(data["device_private_key_protected"])
        self.assertEqual(data["device_public_key_fingerprint"], fingerprint)

        restored = backend.LicenseManager(FakeSettings())
        self.assertFalse(restored.is_activated())
        self.assertFalse(restored.license_key)
        self.assertEqual(restored.device_private_key_pem, device_key)

        ok, message = restored.validate(
            "AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", ""
        )
        self.assertTrue(ok, message)
        self.assertEqual(restored.device_private_key_pem, device_key)

    def test_license_switch_reuses_persistent_device_key(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate("AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", "")
        self.assertTrue(ok)
        device_key = manager.device_private_key_pem

        ok, message = manager.validate("EEEEEEEE-FFFFFFFF-11111111-22222222", "")
        self.assertTrue(ok, message)
        self.assertEqual(manager.device_private_key_pem, device_key)

    def test_ambiguous_refresh_is_cleared_on_disk_before_reactivation(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate("AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", "")
        self.assertTrue(ok)
        manager.access_token = "expired"
        manager.save()

        with patch.object(backend, "LicoraV2Client", FailingRefreshRecoveryClient):
            ok, _ = manager.validate(manager.license_key, "")
        self.assertFalse(ok)
        data = json.loads(self.path.read_text())
        self.assertFalse(data["access_token_protected"])
        self.assertFalse(data["refresh_token_protected"])
        self.assertTrue(data["license_key_protected"])
        self.assertTrue(data["device_private_key_protected"])

    def test_logout_during_remote_validation_cannot_report_success_or_restore_session(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate("AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", "")
        self.assertTrue(ok)

        BlockingStatusClient.entered = threading.Event()
        BlockingStatusClient.release = threading.Event()
        result = {}

        with patch.object(backend, "LicoraV2Client", BlockingStatusClient):
            worker = threading.Thread(
                target=lambda: result.setdefault(
                    "validate", manager.validate(manager.license_key, manager.user_email)
                )
            )
            worker.start()
            self.assertTrue(BlockingStatusClient.entered.wait(timeout=1.5))
            manager.logout()
            BlockingStatusClient.release.set()
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertFalse(result["validate"][0])
        self.assertIn("changed locally", result["validate"][1].lower())
        self.assertFalse(manager.license_key)
        self.assertFalse(manager.access_token)
        self.assertFalse(manager.refresh_token)
        self.assertFalse(manager.is_activated())

    def test_remote_validation_does_not_hold_ui_state_lock(self):
        manager = backend.LicenseManager(FakeSettings())
        ok, _ = manager.validate("AAAAAAAA-BBBBBBBB-CCCCCCCC-DDDDDDDD", "")
        self.assertTrue(ok)

        BlockingStatusClient.entered = threading.Event()
        BlockingStatusClient.release = threading.Event()
        result = {}

        with patch.object(backend, "LicoraV2Client", BlockingStatusClient):
            worker = threading.Thread(
                target=lambda: result.setdefault(
                    "validate", manager.validate(manager.license_key, manager.user_email)
                )
            )
            worker.start()
            self.assertTrue(BlockingStatusClient.entered.wait(timeout=1.5))

            probe_done = threading.Event()

            def probe():
                result["active"] = manager.is_activated()
                probe_done.set()

            probe_thread = threading.Thread(target=probe)
            probe_thread.start()
            self.assertTrue(
                probe_done.wait(timeout=0.5),
                "is_activated blocked behind remote validation network I/O",
            )
            self.assertTrue(result["active"])
            BlockingStatusClient.release.set()
            worker.join(timeout=2)
            probe_thread.join(timeout=2)
            self.assertFalse(worker.is_alive())
            self.assertTrue(result["validate"][0])


if __name__ == "__main__":
    unittest.main()
