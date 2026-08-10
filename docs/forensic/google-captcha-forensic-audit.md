# v1.0.6.19 Evidence Addendum

Real Windows VibraPilot evidence is now available for the app-launched side of the comparison:

- Chrome Stable `151.0.7922.76`
- real Google Chrome executable
- no Chromium fallback in the captured run
- dedicated managed `slot_1` profile
- `--no-sandbox`
- `navigator.webdriver=true`
- viewport `1280×720`
- DPR approximately `1.0`
- language `en-US`
- timezone `America/Los_Angeles`
- AMD Direct3D11 WebGL renderer
- Playwright Python `1.60.0`

However no paired same-machine normal-Chrome capture or reproducible CAPTCHA outcome is included. Therefore CAPTCHA root cause remains **NOT VERIFIED**. None of the values above is promoted to a confirmed causal factor.

# Google CAPTCHA / Unusual Traffic Forensic Audit — v1.0.6.18

Root Cause Status: **NOT VERIFIED / RUNTIME EVIDENCE REQUIRED**.

Confirmed environment differences include managed profile, Playwright launch, optional Chrome→Chromium fallback, Sandbox-OFF, fixed 1280×720 viewport, DPR 1.0 and HTTP-cache-disabled routing. None is proven causal.

v1.0.6.18 records the app-side identity/environment evidence needed for a same-machine, same-network comparison: product/version, executable/command line when available, fallback, profile, UA/Client Hints, observed `navigator.webdriver`, screen/viewport/DPR, languages/timezone, WebGL and representative fonts.

No stealth, CAPTCHA bypass, fingerprint spoofing or webdriver falsification is introduced. A factor is confirmed only if changing it reproducibly changes the CAPTCHA outcome under equivalent conditions.
