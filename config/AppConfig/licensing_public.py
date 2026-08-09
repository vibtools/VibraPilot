"""Public Licora Secure API v2 configuration for VibraPilot.

This module intentionally contains only non-secret client configuration.  The
server RSA *public* signing key is pinned so VibraPilot can verify Licora access
tokens locally.  No API v1 shared key, server private signing key, license key,
device private key, access token, or refresh token belongs in source control.
"""

LICORA_API_BASE_URL = "https://mxflow.shop"
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
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAtyagxZBg0ZyKPdWvc+KW
jHIjjMHi34yHFh9hOWB/ciMRvDDquyCsIaFEVwE+70w8bwqoUy/aXv0DQUNgBZhU
Y2snjSiRm4V0S/YvDYR+1zFXmVVx9jHT1E29OTSzlz0GFUV+wDx5ErKMZtt+Gns/
r3CF0iADf5FlPnBey7+5jl7gvn5yQYZNztDcAL6WU9QSO0lo2GqCjClGE17yrIdz
0ybr20YiL9rNKaI4PVwFCQuJGhh5bjcmOjZmyt9+8OjxoywOyzWxRSeT669QZBgw
nHJ8vwQftFt4dPhtHih11FOzOmjSqW7+u8R3WkDuKSTA4uyiiLVb/go0bka3g3kO
NfU0NL9gWoN/cy8OBqdWxfA1ZgoX5IeOjVTung/GYNgKALCK98xGA+1wr2wwAItY
coCMzQ9zTDs42l0/Pew9fUyhEgc6jdkCyhRnLUaPq+4HYlQZexUX5TCtbgw4va9o
sbhQ3Mzsy8RlD5noNI10tw85RgjQO9HKK62u4jeaImY/AgMBAAE=
-----END PUBLIC KEY-----
"""
LICORA_SIGNING_PUBLIC_KEY_SHA256 = "e4c15e883f17f89482f3423245d2bf71da64190dba4ea01d39da0a1d88942783"

# Request proof and token validation use the production server clock-skew policy.
LICORA_CLOCK_SKEW_SECONDS = 300
