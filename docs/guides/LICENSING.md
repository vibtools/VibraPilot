# Licora Secure API v2 Integration

VibraPilot v1.0.6.10 uses Licora Secure API v2 for desktop licensing. The client does **not** embed or send a Licora API v1 shared/master API key.

## Public client configuration

`config/AppConfig/licensing_public.py` contains only non-secret deployment metadata:

- HTTPS Licora base URL
- App ID `vibrapilot`
- `/api/v2/activate.php`, `/status.php`, `/refresh.php`, `/deactivate.php`
- pinned Licora RSA public signing key and SHA-256 fingerprint
- expected signing key ID and clock-skew policy

The matching Licora RSA private signing key remains server-side and must never be packaged with VibraPilot.

## Persistent device-bound activation

VibraPilot uses one persistent P-256 (`secp256r1`) device key identity for the local installation. The key is generated if absent and is DPAPI-protected and atomically persisted **before** any first activation request is sent. This prevents a response-loss/restart from leaving Licora bound to a device public key that the client did not save.

The same protected device key is retained across logout and license switching. If production Licora reports `DEVICE_KEY_MISMATCH` or `DEVICE_REVOKED`, VibraPilot persists one new device ID and retries activation once with the existing P-256 key. A stale active device that already fills the server device limit is not bypassed; Licora administrator cleanup is required before the recovered ID can consume a slot. The public key is sent to Licora during activation; the private key never leaves the client.

Signed requests use the exact Licora canonical form:

```text
METHOD
PATH
TIMESTAMP
NONCE
SHA256(raw JSON body)
CONTEXT
```

Activation uses `activate:vibrapilot`; refresh uses `refresh:<sha256(refresh_token)>`; status and deactivate use the current access-token JTI.

## Tokens and local persistence

Licora returns a short-lived RS256 access token and a rotating refresh token. VibraPilot validates the access token locally before using it, including `typ`, `alg`, `kid`, signature, issuer, audience/App ID, device ID, device-key fingerprint, timestamps, JTI and token version. Successfully verified access-token state is cached in memory until its verified expiry so dashboard polling does not repeatedly perform identical RSA verification.

`%LOCALAPPDATA%\Vib Tools\VibraPilot\license.json` is the default Windows session cache for v1.0.6.10 (an explicit `VIB_TOOLS_DATA_DIR` remains authoritative). A one-time migration copies the historical install-relative `AppData/license.json` when needed. `device_identity.json` separately preserves the DPAPI-protected P-256 device key and stable client device ID so clean upgrades or a corrupt session cache do not recreate the same server device with a different key. Windows DPAPI protects:

- license key
- P-256 device private key
- access token
- refresh token

Writes use a temporary file, flush/fsync and atomic `os.replace()`. The persistent device key may remain in a device-only schema-v2 cache after logout; protected license and session tokens are cleared.

Existing pre-v2 license caches are detected at startup. The existing activation shell displays the restore attempt while the protected license is revalidated against API v2. The migration is considered complete only after a server-authorized v2 session has been verified and persisted.

## Refresh and recovery

Refresh tokens rotate on every successful refresh. A refresh call is one-shot and is never blindly retried with the same token. If a refresh outcome is ambiguous, VibraPilot clears the old access/refresh state **and atomically persists that invalidation before** attempting fresh activation with the protected license key and persistent device key. A restart therefore cannot replay the old refresh credential.

Periodic license recheck runs whenever a protected/current license exists, even if the short-lived access token has expired; `validate()` can then refresh or safely re-activate the session.

## Concurrency and UI behavior

Long-running Licora HTTP validation uses a dedicated validation lock rather than holding the short UI-facing state lock. Dashboard `is_activated()` reads therefore do not wait behind remote network I/O. A state-generation guard prevents a late background validation result from restoring a session after local logout or another session-changing action. Validation checks the pending-logout event again while holding both validation/state locks, closing the narrow race where a login could otherwise pass the initial wait and acquire the validation lock just ahead of the queued deactivation request.

## Logout

Logout immediately removes the protected license key, access token and refresh token from local session state while retaining the persistent DPAPI-protected P-256 key. Server deactivation remains best-effort and serialized against any new activation. When deactivation is confirmed, VibraPilot persists a new client device ID because the current Licora server permanently revokes the old ID; if the deactivation outcome is unavailable, the old ID is retained and the next activation resolves the actual server state safely.

## Release-package boundary

`AppData/`, `Logs/`, `Reports/`, `FailedData/`, `project/`, `__pycache__/` and `.pytest_cache/` are private/runtime/development paths and are not valid release-source inputs. The current production scope verifier and packaging audit enforce this boundary for the official clean baseline.
