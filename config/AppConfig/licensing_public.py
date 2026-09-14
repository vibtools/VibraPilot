"""Public Licora Secure API v2 configuration for VibraPilot.

This module intentionally contains only non-secret client configuration.  The
server RSA *public* signing key is pinned so VibraPilot can verify Licora access
tokens locally.  No API v1 shared key, server private signing key, license key,
device private key, access token, or refresh token belongs in source control.
"""

LICORA_API_BASE_URL = "https://license.vib.tools"
LICORA_API_VERSION = 2
LICORA_PROTOCOL = "licora-api-v2"
LICORA_APP_ID = "vibrapilot"

LICORA_ACTIVATE_PATH = "/api/v2/activate.php"
LICORA_STATUS_PATH = "/api/v2/status.php"
LICORA_REFRESH_PATH = "/api/v2/refresh.php"
LICORA_DEACTIVATE_PATH = "/api/v2/deactivate.php"

# Licora v5.2.1 default signing key identifier for this deployment.
LICORA_SIGNING_KEY_ID = "primary-v1"

# Public material only.  The corresponding private key remains exclusively on
# the Licora server and must never be packaged with VibraPilot.
LICORA_SIGNING_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAutnTEEYmknkLbkVMUoIM
w4idtNUCRzM/kiHfwuyzNfTwO8THNmf9444BktFxVRP92FLUCRc9mMnR/RKrle4Z
jYKn712hzBN+Ixr5qIJCKLI6jMsfk4oRQxixP0zhRiRoK6y/UZMZn4GUhYvN7Ibo
FzWgJyQPgrcmyUz3LGqhiTjCnERAeOb8Uwpy/bpCA1W+6TML+TQEGabUJ4/R+zH4
xacIvJCMF6AocJTtX/3GslrJUzjWPh3bKxo47O7/JaPoUqRQgONNPklVwvvRsGkB
a8PGitFB5K3Peit7+jnM+vxjQsuijD5xaICukbcvrDhWQEMEAcSfXrnmvikZcaVP
klSwznsx9/xlRNJNPR6hj/FfUEQ3PLTsaMREfJJIZ8tjqp5meAupdc8VDDpKuOfs
F4tZaFvd4l2JAfuoB8kz3JoRD3BkEa+HHb+CErUNvUmYZRWzAHaNc3RDoLOXWcdk
btwgN8eITUGiWRiD7XwQsaMw8P6ooZWY9gJJHv0symznAgMBAAE=
-----END PUBLIC KEY-----
"""
LICORA_SIGNING_PUBLIC_KEY_SHA256 = "a10f52d70a8a5813495e3b5904639d65b8530d8cfde228657ff19e49ca5790a4"

# Request proof and token validation use the production server clock-skew policy.
LICORA_CLOCK_SKEW_SECONDS = 300
