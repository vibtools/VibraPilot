#!/usr/bin/env python3
"""Verify PR-12 GitHub Actions package outputs before artifact upload."""
from __future__ import annotations
import argparse, hashlib, json, os, zipfile
from pathlib import Path

VERSION="1.0.6.29"; MSI_VERSION="1.0.629"; NUITKA="4.1.3"; WIX="6.0.2"

def sha256(p: Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def sidecar_ok(p: Path)->bool:
    s=p.with_name(p.name+'.sha256')
    return s.is_file() and s.read_text(encoding='ascii').strip().split()[0]==sha256(p)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--release',type=Path,required=True); a=ap.parse_args()
    r=a.release.resolve(); base=f'VibraPilot-{VERSION}-Windows-x64'
    z=r/f'{base}.zip'; m=r/f'{base}.msi'; manifest=r/f'{base}-BUILD_MANIFEST.json'; report=r/f'VibraPilot-{VERSION}-Nuitka-Report.xml'
    for p in (z,m,manifest,report):
        if not p.is_file(): raise SystemExit(f'PR12 CI ARTIFACT VERIFY: FAIL missing {p}')
    if not sidecar_ok(z) or not sidecar_ok(m): raise SystemExit('PR12 CI ARTIFACT VERIFY: FAIL sidecar hash mismatch')
    with zipfile.ZipFile(z) as q:
        bad=q.testzip()
        if bad: raise SystemExit(f'PR12 CI ARTIFACT VERIFY: FAIL ZIP CRC {bad}')
        names=q.namelist()
        required=[f'{base}/VibraPilot.exe',f'{base}/config/settings.defaults.json',f'{base}/SHA256SUMS.json']
        for name in required:
            if name not in names: raise SystemExit(f'PR12 CI ARTIFACT VERIFY: FAIL ZIP missing {name}')
        if not any(name.startswith(f'{base}/ms-playwright/') for name in names): raise SystemExit('PR12 CI ARTIFACT VERIFY: FAIL bundled Chromium missing')
    d=json.loads(manifest.read_text(encoding='utf-8'))
    if d.get('version')!=VERSION: raise SystemExit('PR12 CI ARTIFACT VERIFY: FAIL version')
    if d.get('compiler')!={'name':'Nuitka','version':NUITKA,'mode':'standalone'}: raise SystemExit('PR12 CI ARTIFACT VERIFY: FAIL Nuitka contract')
    ins=d.get('installer',{})
    if ins.get('version')!=WIX or ins.get('scope')!='perUser' or ins.get('msi_product_version')!=MSI_VERSION: raise SystemExit('PR12 CI ARTIFACT VERIFY: FAIL MSI contract')
    prov=d.get('build_provenance',{})
    if prov.get('provider')!='github_actions' or not prov.get('sha') or prov.get('workflow')!='PR-12 Package Build': raise SystemExit(f'PR12 CI ARTIFACT VERIFY: FAIL provenance {prov}')
    pol=d.get('browser_policy',{})
    if pol!={'google_chrome_preferred':True,'observable_chromium_fallback':True,'sandbox_default':False}: raise SystemExit(f'PR12 CI ARTIFACT VERIFY: FAIL browser policy {pol}')
    print('PR12 CI ARTIFACT VERIFY: PASS')
    print('GitHub SHA:',prov.get('sha')); print('ZIP SHA-256:',sha256(z)); print('MSI SHA-256:',sha256(m))
    return 0
if __name__=='__main__': raise SystemExit(main())
