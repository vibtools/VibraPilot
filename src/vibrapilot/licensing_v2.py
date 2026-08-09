"""Licora Secure API v2 client primitives for VibraPilot.

This module owns the wire protocol and cryptographic contract only.  Local
Windows DPAPI persistence remains the responsibility of ``backend.LicenseManager``.
No API v1 shared/master credential is used by this client.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from .app_config import LICENSING


class LicoraV2Error(RuntimeError):
    """Stable client-side representation of a Licora API v2 failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        request_id: str = "",
    ) -> None:
        super().__init__(message)
        self.code = str(code or "LICORA_V2_ERROR")
        self.message = str(message or "Licora API v2 request failed.")
        self.http_status = http_status
        self.request_id = str(request_id or "")

    @property
    def is_network_error(self) -> bool:
        return self.code in {"NETWORK_ERROR", "INVALID_SERVER_RESPONSE"}


@dataclass(frozen=True)
class DeviceKeyMaterial:
    private_key_pem: str
    public_key_pem: str
    public_key_fingerprint: str


@dataclass(frozen=True)
class AccessTokenClaims:
    raw: dict[str, Any]

    @property
    def jti(self) -> str:
        return str(self.raw["jti"])

    @property
    def expires_at(self) -> int:
        return int(self.raw["exp"])

    @property
    def device_id(self) -> str:
        return str(self.raw["device_id"])

    @property
    def device_key_fingerprint(self) -> str:
        return str(self.raw["device_key_fingerprint"])


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    if not value or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for ch in value):
        raise LicoraV2Error("INVALID_TOKEN", "Access token encoding is invalid.")
    padding_len = (4 - len(value) % 4) % 4
    try:
        return base64.b64decode(
            value.replace("-", "+").replace("_", "/") + "=" * padding_len,
            validate=True,
        )
    except Exception as exc:
        raise LicoraV2Error("INVALID_TOKEN", "Access token encoding is invalid.") from exc


def compact_json(value: dict[str, Any]) -> str:
    """Return deterministic JSON bytes compatible with Licora request signing."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _normalize_public_pem(public_key: ec.EllipticCurvePublicKey) -> str:
    return public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def generate_device_key_material() -> DeviceKeyMaterial:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = _normalize_public_pem(private_key.public_key())
    return DeviceKeyMaterial(
        private_key_pem=private_pem,
        public_key_pem=public_pem,
        public_key_fingerprint=hashlib.sha256(public_pem.encode("ascii")).hexdigest(),
    )


def load_device_key_material(private_key_pem: str) -> DeviceKeyMaterial:
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("ascii"), password=None
        )
    except Exception as exc:
        raise LicoraV2Error("INVALID_DEVICE_KEY", "Stored device key is invalid.") from exc
    if not isinstance(private_key, ec.EllipticCurvePrivateKey) or not isinstance(
        private_key.curve, ec.SECP256R1
    ):
        raise LicoraV2Error("INVALID_DEVICE_KEY", "Stored device key is not P-256.")
    normalized_private = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = _normalize_public_pem(private_key.public_key())
    return DeviceKeyMaterial(
        private_key_pem=normalized_private,
        public_key_pem=public_pem,
        public_key_fingerprint=hashlib.sha256(public_pem.encode("ascii")).hexdigest(),
    )


class LicoraV2Client:
    """Protocol-exact Licora v2 HTTP client with local token verification."""

    def __init__(
        self,
        *,
        app_version: str,
        timeout: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = LICENSING.api_base_url.rstrip("/")
        self.app_id = LICENSING.app_id
        self.app_version = str(app_version)
        self.timeout = min(300.0, max(1.0, float(timeout)))
        self.session = session or requests.Session()
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise LicoraV2Error(
                "INVALID_CONFIGURATION", "Licora API v2 base URL must use HTTPS."
            )

        public_pem_bytes = LICENSING.signing_public_key_pem.encode("ascii")
        digest = hashlib.sha256(public_pem_bytes).hexdigest()
        if digest != LICENSING.signing_public_key_sha256:
            raise LicoraV2Error(
                "INVALID_CONFIGURATION", "Pinned Licora public-key fingerprint mismatch."
            )
        try:
            public_key = serialization.load_pem_public_key(public_pem_bytes)
        except Exception as exc:
            raise LicoraV2Error(
                "INVALID_CONFIGURATION", "Pinned Licora public key is invalid."
            ) from exc
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 3072:
            raise LicoraV2Error(
                "INVALID_CONFIGURATION", "Pinned Licora signing key must be RSA-3072 or stronger."
            )
        self.server_public_key = public_key

    def _url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    @staticmethod
    def _canonical(
        method: str,
        url: str,
        timestamp: int,
        nonce: str,
        raw_body: str,
        context: str,
    ) -> bytes:
        path = urlparse(url).path or "/"
        body_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()
        return (
            method.upper()
            + "\n"
            + path
            + "\n"
            + str(timestamp)
            + "\n"
            + nonce
            + "\n"
            + body_hash
            + "\n"
            + context
        ).encode("utf-8")

    @staticmethod
    def _private_key(private_key_pem: str) -> ec.EllipticCurvePrivateKey:
        material = load_device_key_material(private_key_pem)
        key = serialization.load_pem_private_key(
            material.private_key_pem.encode("ascii"), password=None
        )
        assert isinstance(key, ec.EllipticCurvePrivateKey)
        return key

    def _proof_headers(
        self,
        *,
        url: str,
        raw_body: str,
        context: str,
        private_key_pem: str,
        access_token: str = "",
    ) -> dict[str, str]:
        timestamp = int(time.time())
        nonce = secrets.token_urlsafe(24)
        canonical = self._canonical(
            "POST", url, timestamp, nonce, raw_body, context
        )
        signature = self._private_key(private_key_pem).sign(
            canonical, ec.ECDSA(hashes.SHA256())
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"VibraPilot/{self.app_version}",
            "X-Licora-Timestamp": str(timestamp),
            "X-Licora-Nonce": nonce,
            "X-Licora-Device-Signature": _b64url_encode(signature),
        }
        if access_token:
            headers["Authorization"] = "Bearer " + access_token
        return headers

    def _post(
        self,
        *,
        path: str,
        payload: dict[str, Any],
        context: str,
        private_key_pem: str,
        access_token: str = "",
    ) -> dict[str, Any]:
        url = self._url(path)
        raw_body = compact_json(payload)
        headers = self._proof_headers(
            url=url,
            raw_body=raw_body,
            context=context,
            private_key_pem=private_key_pem,
            access_token=access_token,
        )
        try:
            response = self.session.post(
                url,
                data=raw_body.encode("utf-8"),
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise LicoraV2Error(
                "NETWORK_ERROR", f"Licora API v2 network request failed: {exc}"
            ) from exc
        if 300 <= response.status_code < 400:
            raise LicoraV2Error(
                "INVALID_SERVER_RESPONSE",
                "Licora API v2 unexpectedly redirected the request.",
                http_status=response.status_code,
            )
        try:
            body = response.json()
        except Exception as exc:
            raise LicoraV2Error(
                "INVALID_SERVER_RESPONSE",
                "Licora API v2 returned a non-JSON response.",
                http_status=response.status_code,
            ) from exc
        if not isinstance(body, dict):
            raise LicoraV2Error(
                "INVALID_SERVER_RESPONSE",
                "Licora API v2 returned an invalid response object.",
                http_status=response.status_code,
            )
        request_id = str(body.get("request_id", ""))
        if body.get("protocol") != LICENSING.protocol or int(body.get("api_version", 0)) != 2:
            raise LicoraV2Error(
                "INVALID_SERVER_RESPONSE",
                "Licora API v2 protocol marker is invalid.",
                http_status=response.status_code,
                request_id=request_id,
            )
        if response.status_code != 200 or body.get("success") is not True or body.get("code") != "OK":
            raise LicoraV2Error(
                str(body.get("code") or "LICORA_V2_ERROR"),
                str(body.get("message") or "Licora API v2 request was rejected."),
                http_status=response.status_code,
                request_id=request_id,
            )
        return body

    def verify_access_token(
        self,
        token: str,
        *,
        expected_device_id: str | None = None,
        expected_device_fingerprint: str | None = None,
    ) -> AccessTokenClaims:
        parts = token.split(".")
        if len(parts) != 3:
            raise LicoraV2Error("INVALID_TOKEN", "Access token structure is invalid.")
        try:
            header = json.loads(_b64url_decode(parts[0]).decode("utf-8"))
            payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
            signature = _b64url_decode(parts[2])
        except LicoraV2Error:
            raise
        except Exception as exc:
            raise LicoraV2Error("INVALID_TOKEN", "Access token JSON is invalid.") from exc
        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise LicoraV2Error("INVALID_TOKEN", "Access token payload is invalid.")
        if (
            header.get("typ") != "LICORA-V2"
            or header.get("alg") != "RS256"
            or header.get("kid") != LICENSING.signing_key_id
        ):
            raise LicoraV2Error("INVALID_TOKEN", "Access token header is invalid.")
        try:
            self.server_public_key.verify(
                signature,
                (parts[0] + "." + parts[1]).encode("ascii"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except InvalidSignature as exc:
            raise LicoraV2Error("INVALID_TOKEN", "Access token signature is invalid.") from exc
        except Exception as exc:
            raise LicoraV2Error("INVALID_TOKEN", "Access token verification failed.") from exc

        required = {
            "iss", "aud", "app_id", "license_id", "device_id",
            "device_credential_id", "device_key_fingerprint", "iat", "nbf",
            "exp", "jti", "token_version",
        }
        if not required.issubset(payload):
            raise LicoraV2Error("INVALID_TOKEN", "Access token claims are incomplete.")
        if payload.get("iss") != "licora" or int(payload.get("token_version", 0)) != 2:
            raise LicoraV2Error("INVALID_TOKEN", "Access token issuer/version is invalid.")
        if payload.get("aud") != self.app_id or payload.get("app_id") != self.app_id:
            raise LicoraV2Error("INVALID_TOKEN", "Access token audience is invalid.")
        if expected_device_id is not None and payload.get("device_id") != expected_device_id:
            raise LicoraV2Error("INVALID_TOKEN", "Access token device does not match this PC.")
        if (
            expected_device_fingerprint is not None
            and payload.get("device_key_fingerprint") != expected_device_fingerprint
        ):
            raise LicoraV2Error("INVALID_TOKEN", "Access token device key does not match this PC.")

        now = int(time.time())
        skew = int(LICENSING.clock_skew_seconds)
        try:
            iat = int(payload["iat"])
            nbf = int(payload["nbf"])
            exp = int(payload["exp"])
        except Exception as exc:
            raise LicoraV2Error("INVALID_TOKEN", "Access token timestamps are invalid.") from exc
        if nbf > now + skew or iat > now + skew:
            raise LicoraV2Error("TOKEN_NOT_YET_VALID", "Access token is not yet valid.")
        # Client-side authorization is strict at the actual expiration boundary.
        # The server may tolerate skew for transport, but VibraPilot proactively
        # refreshes instead of opening the workspace with an expired token.
        if exp <= now:
            raise LicoraV2Error("TOKEN_EXPIRED", "Access token has expired.")
        if not isinstance(payload.get("jti"), str) or not payload["jti"]:
            raise LicoraV2Error("INVALID_TOKEN", "Access token JTI is invalid.")
        return AccessTokenClaims(dict(payload))

    def activate(
        self,
        *,
        license_key: str,
        device_id: str,
        private_key_pem: str,
    ) -> dict[str, Any]:
        material = load_device_key_material(private_key_pem)
        result = self._post(
            path=LICENSING.activate_path,
            payload={
                "license_key": license_key.strip().upper(),
                "app_id": self.app_id,
                "app_version": self.app_version,
                "device_id": device_id,
                "device_public_key": material.public_key_pem,
            },
            context="activate:" + self.app_id,
            private_key_pem=material.private_key_pem,
        )
        access_token = str(result.get("access_token", ""))
        refresh_token = str(result.get("refresh_token", ""))
        if not access_token or not refresh_token:
            raise LicoraV2Error(
                "INVALID_SERVER_RESPONSE", "Activation response did not include both tokens."
            )
        claims = self.verify_access_token(
            access_token,
            expected_device_id=device_id,
            expected_device_fingerprint=material.public_key_fingerprint,
        )
        result["verified_claims"] = claims.raw
        return result

    def status(
        self,
        *,
        access_token: str,
        device_id: str,
        private_key_pem: str,
    ) -> dict[str, Any]:
        material = load_device_key_material(private_key_pem)
        claims = self.verify_access_token(
            access_token,
            expected_device_id=device_id,
            expected_device_fingerprint=material.public_key_fingerprint,
        )
        return self._post(
            path=LICENSING.status_path,
            payload={},
            context=claims.jti,
            private_key_pem=material.private_key_pem,
            access_token=access_token,
        )

    def refresh(
        self,
        *,
        refresh_token: str,
        device_id: str,
        private_key_pem: str,
    ) -> dict[str, Any]:
        material = load_device_key_material(private_key_pem)
        result = self._post(
            path=LICENSING.refresh_path,
            payload={"refresh_token": refresh_token, "app_version": self.app_version},
            context="refresh:" + hashlib.sha256(refresh_token.encode("utf-8")).hexdigest(),
            private_key_pem=material.private_key_pem,
        )
        new_access = str(result.get("access_token", ""))
        new_refresh = str(result.get("refresh_token", ""))
        if not new_access or not new_refresh or new_refresh == refresh_token:
            raise LicoraV2Error(
                "INVALID_SERVER_RESPONSE", "Refresh response did not rotate credentials."
            )
        claims = self.verify_access_token(
            new_access,
            expected_device_id=device_id,
            expected_device_fingerprint=material.public_key_fingerprint,
        )
        result["verified_claims"] = claims.raw
        return result

    def deactivate(
        self,
        *,
        access_token: str,
        device_id: str,
        private_key_pem: str,
    ) -> dict[str, Any]:
        material = load_device_key_material(private_key_pem)
        claims = self.verify_access_token(
            access_token,
            expected_device_id=device_id,
            expected_device_fingerprint=material.public_key_fingerprint,
        )
        return self._post(
            path=LICENSING.deactivate_path,
            payload={},
            context=claims.jti,
            private_key_pem=material.private_key_pem,
            access_token=access_token,
        )
