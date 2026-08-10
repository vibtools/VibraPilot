# Google CAPTCHA / Unusual Traffic Forensic Audit — v1.0.6.18

Root Cause Status: **NOT VERIFIED / RUNTIME EVIDENCE REQUIRED**.

Confirmed environment differences include managed profile, Playwright launch, optional Chrome→Chromium fallback, Sandbox-OFF, fixed 1280×720 viewport, DPR 1.0 and HTTP-cache-disabled routing. None is proven causal.

v1.0.6.18 records the app-side identity/environment evidence needed for a same-machine, same-network comparison: product/version, executable/command line when available, fallback, profile, UA/Client Hints, observed `navigator.webdriver`, screen/viewport/DPR, languages/timezone, WebGL and representative fonts.

No stealth, CAPTCHA bypass, fingerprint spoofing or webdriver falsification is introduced. A factor is confirmed only if changing it reproducibly changes the CAPTCHA outcome under equivalent conditions.
