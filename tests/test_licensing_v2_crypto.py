from __future__ import annotations

import base64
import hashlib
import json
import time
import unittest

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from vibrapilot.app_config import LICENSING
from vibrapilot.licensing_v2 import (
    LicoraV2Client,
    LicoraV2Error,
    generate_device_key_material,
    load_device_key_material,
)


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def token(private_key, payload: dict, *, header: dict | None = None) -> str:
    head = header or {"typ": "LICORA-V2", "alg": "RS256", "kid": LICENSING.signing_key_id}
    eh = b64url(json.dumps(head, separators=(",", ":")).encode())
    ep = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signature = private_key.sign((eh + "." + ep).encode(), padding.PKCS1v15(), hashes.SHA256())
    return eh + "." + ep + "." + b64url(signature)


class LicensingV2CryptoTest(unittest.TestCase):
    def test_pinned_public_key_hash_and_public_only_contract(self):
        self.assertEqual(
            hashlib.sha256(LICENSING.signing_public_key_pem.encode("ascii")).hexdigest(),
            LICENSING.signing_public_key_sha256,
        )
        self.assertIn("BEGIN PUBLIC KEY", LICENSING.signing_public_key_pem)
        self.assertNotIn("PRIVATE KEY", LICENSING.signing_public_key_pem)

    def test_device_key_is_p256_and_fingerprint_is_stable(self):
        material = generate_device_key_material()
        loaded = load_device_key_material(material.private_key_pem)
        self.assertEqual(material.public_key_pem, loaded.public_key_pem)
        self.assertEqual(material.public_key_fingerprint, loaded.public_key_fingerprint)
        key = serialization.load_pem_public_key(material.public_key_pem.encode())
        self.assertIsInstance(key, ec.EllipticCurvePublicKey)
        self.assertIsInstance(key.curve, ec.SECP256R1)

    def test_request_proof_is_ecdsa_sha256_over_exact_canonical_body(self):
        material = generate_device_key_material()
        client = LicoraV2Client(app_version="1.0.6.4")
        url = "https://mxflow.shop/api/v2/status.php"
        raw = "{}"
        headers = client._proof_headers(
            url=url,
            raw_body=raw,
            context="0123456789abcdef",
            private_key_pem=material.private_key_pem,
        )
        canonical = client._canonical(
            "POST",
            url,
            int(headers["X-Licora-Timestamp"]),
            headers["X-Licora-Nonce"],
            raw,
            "0123456789abcdef",
        )
        signature = base64.urlsafe_b64decode(
            headers["X-Licora-Device-Signature"] + "=="
        )
        public = serialization.load_pem_public_key(material.public_key_pem.encode())
        public.verify(signature, canonical, ec.ECDSA(hashes.SHA256()))
        with self.assertRaises(InvalidSignature):
            public.verify(signature, canonical + b"x", ec.ECDSA(hashes.SHA256()))

    def test_rs256_token_verification_checks_app_device_and_expiry(self):
        server_private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        material = generate_device_key_material()
        client = LicoraV2Client(app_version="1.0.6.4")
        client.server_public_key = server_private.public_key()
        now = int(time.time())
        payload = {
            "iss": "licora",
            "aud": "vibrapilot",
            "app_id": "vibrapilot",
            "license_id": 1,
            "device_id": "device-1234567890",
            "device_credential_id": 2,
            "device_key_fingerprint": material.public_key_fingerprint,
            "iat": now,
            "nbf": now - 5,
            "exp": now + 3600,
            "jti": "0123456789abcdef0123456789abcdef",
            "token_version": 2,
        }
        good = token(server_private, payload)
        claims = client.verify_access_token(
            good,
            expected_device_id=payload["device_id"],
            expected_device_fingerprint=material.public_key_fingerprint,
        )
        self.assertEqual(claims.raw["app_id"], "vibrapilot")

        wrong_aud = dict(payload, aud="other")
        with self.assertRaises(LicoraV2Error):
            client.verify_access_token(token(server_private, wrong_aud))
        expired = dict(payload, exp=now - 1)
        with self.assertRaisesRegex(LicoraV2Error, "expired"):
            client.verify_access_token(token(server_private, expired))
        invalid_headers = [
            {"typ": "WRONG", "alg": "RS256", "kid": LICENSING.signing_key_id},
            {"typ": "LICORA-V2", "alg": "RS512", "kid": LICENSING.signing_key_id},
            {"typ": "LICORA-V2", "alg": "RS256", "kid": "wrong"},
        ]
        for header in invalid_headers:
            with self.subTest(header=header):
                with self.assertRaises(LicoraV2Error):
                    client.verify_access_token(token(server_private, payload, header=header))

        wrong_app = dict(payload, app_id="other")
        with self.assertRaises(LicoraV2Error):
            client.verify_access_token(token(server_private, wrong_app))
        future = dict(payload, iat=now + 1000, nbf=now + 1000)
        with self.assertRaisesRegex(LicoraV2Error, "not yet valid"):
            client.verify_access_token(token(server_private, future))
        wrong_version = dict(payload, token_version=1)
        with self.assertRaises(LicoraV2Error):
            client.verify_access_token(token(server_private, wrong_version))
        with self.assertRaises(LicoraV2Error):
            client.verify_access_token(
                good, expected_device_id="different-device"
            )
        with self.assertRaises(LicoraV2Error):
            client.verify_access_token(
                good, expected_device_fingerprint="0" * 64
            )

        other_private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        signed_by_other = token(other_private, payload)
        with self.assertRaisesRegex(LicoraV2Error, "signature"):
            client.verify_access_token(signed_by_other)


if __name__ == "__main__":
    unittest.main()
