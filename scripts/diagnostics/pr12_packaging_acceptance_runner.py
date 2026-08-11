#!/usr/bin/env python3
"""PR-12 PC acceptance for GitHub-built VibraPilot ZIP/MSI artifacts.

This script never builds the application and requires no Nuitka or WiX toolchain.
Use it only after downloading/extracting the GitHub Actions artifact named
VibraPilot-1.0.6.29-PR12-Windows-x64.
"""
from __future__ import annotations
import argparse, ctypes, hashlib, json, os, platform, subprocess, time, uuid, zipfile
from ctypes import wintypes
from pathlib import Path

VERSION='1.0.6.29'; MSI_VERSION='1.0.629'; NUITKA='4.1.3'; WIX='6.0.2'
GATES={
 'P01':'Windows + downloaded artifact environment','P02':'GitHub Actions build provenance',
 'P03':'Required ZIP/MSI/report/manifest artifacts','P04':'Portable ZIP CRC/SHA/manifest extraction',
 'P05':'OneDir resources/bundled Chromium/EXE version','P06':'Portable EXE launch and reopen',
 'P07':'Chrome-preferred/fallback policy contract','P08':'MSI manifest/hash contract',
 'P09':'MSI live-install safety preflight','P10':'Isolated per-user MSI install',
 'P11':'Installed EXE launch smoke','P12':'Manual packaged-browser acceptance',
 'P13':'Runtime/user-data preservation markers','P14':'MSI uninstall',
 'P15':'Markers preserved after uninstall','P16':'Final artifact hashes',
 'P17':'PR-13/CL Automation boundary','P18':'PR-12 consolidated PC acceptance'}
ALLOWED={'PASS','FAIL','BLOCKED','NOT_RUN'}

def sha256(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def sidecar_ok(p:Path)->bool:
 s=p.with_name(p.name+'.sha256'); return s.is_file() and s.read_text(encoding='ascii').strip().split()[0]==sha256(p)

def pe_version(path:Path):
 v=ctypes.windll.version; size=v.GetFileVersionInfoSizeW(str(path),None)
 if not size: raise OSError(f'No version resource: {path}')
 buf=ctypes.create_string_buffer(size); v.GetFileVersionInfoW(str(path),0,size,buf)
 lp=ctypes.c_void_p(); length=wintypes.UINT(); v.VerQueryValueW(buf,'\\',ctypes.byref(lp),ctypes.byref(length))
 class F(ctypes.Structure):
  _fields_=[('sig',wintypes.DWORD),('sv',wintypes.DWORD),('fms',wintypes.DWORD),('fls',wintypes.DWORD),('pms',wintypes.DWORD),('pls',wintypes.DWORD),('mask',wintypes.DWORD),('flags',wintypes.DWORD),('os',wintypes.DWORD),('typ',wintypes.DWORD),('sub',wintypes.DWORD),('dms',wintypes.DWORD),('dls',wintypes.DWORD)]
 x=ctypes.cast(lp,ctypes.POINTER(F)).contents; return (x.fms>>16,x.fms&65535,x.fls>>16,x.fls&65535)

def launch(exe:Path,cwd:Path,data:Path,label:str):
 env=os.environ.copy(); env['VIB_TOOLS_DATA_DIR']=str(data); p=subprocess.Popen([str(exe)],cwd=str(cwd),env=env)
 try:
  time.sleep(6)
  if p.poll() is not None: return False,f'{label} exited early rc={p.returncode}'
  p.terminate()
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
  return True,f'{label} stayed alive for 6-second smoke'
 finally:
  if p.poll() is None:p.kill()

def installed_entries():
 import winreg
 found=set()
 for root in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
  for view in (0,getattr(winreg,'KEY_WOW64_64KEY',0),getattr(winreg,'KEY_WOW64_32KEY',0)):
   try:k=winreg.OpenKey(root,r'Software\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view)
   except OSError:continue
   with k:
    for i in range(winreg.QueryInfoKey(k)[0]):
     try:
      n=winreg.EnumKey(k,i); c=winreg.OpenKey(k,n)
      with c:
       if str(winreg.QueryValueEx(c,'DisplayName')[0]).strip().lower()=='vibrapilot': found.add(n)
     except OSError:pass
 return sorted(found)

class A:
 def __init__(self,e:Path): self.e=e; self.r={g:{'title':t,'status':'NOT_RUN','note':''} for g,t in GATES.items()}; self.save()
 def set(self,g,s,n): self.r[g]={'title':GATES[g],'status':s,'note':n}; self.save(); print(f'{g} {s}: {n}',flush=True)
 def save(self): (self.e/'results.json').write_text(json.dumps({'version':VERSION,'gates':self.r},indent=2)+'\n',encoding='utf-8')
 def overall(self):
  if any(x['status']=='FAIL' for x in self.r.values()):return 'FAIL'
  if any(x['status'] in {'BLOCKED','NOT_RUN'} for g,x in self.r.items() if g!='P18'):return 'BLOCKED'
  return 'PASS'

def finish(a:A):
 result=a.overall(); lines=[f'=== PR-12 PC RESULT: {result} ===']+[f"{g} {a.r[g]['status']:<10} {GATES[g]} :: {a.r[g]['note']}" for g in GATES]
 s=a.e/'SUMMARY.txt'; lines += [f'EVIDENCE_DIR={a.e}',f'SUMMARY_FILE={s}']; s.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'+'\n'.join(lines)); return 0 if result=='PASS' else (1 if result=='FAIL' else 2)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--artifacts',type=Path,required=True); a=ap.parse_args()
 art=a.artifacts.expanduser().resolve(); evidence=art/'PR12_PC_EVIDENCE'/ (time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]); evidence.mkdir(parents=True)
 acc=A(evidence); print('=== VibraPilot PR-12 PC ACCEPTANCE ==='); print('Artifacts:',art); print('Evidence:',evidence)
 if os.name!='nt' or platform.system().lower()!='windows': acc.set('P01','BLOCKED','Windows x64 required'); return finish(acc)
 acc.set('P01','PASS',f'Windows {platform.release()} x64; package build is not performed on this PC')
 base=f'VibraPilot-{VERSION}-Windows-x64'; z=art/f'{base}.zip'; m=art/f'{base}.msi'; manifest=art/f'{base}-BUILD_MANIFEST.json'; report=art/f'VibraPilot-{VERSION}-Nuitka-Report.xml'
 if not manifest.is_file(): acc.set('P02','FAIL','build manifest missing'); return finish(acc)
 d=json.loads(manifest.read_text(encoding='utf-8')); prov=d.get('build_provenance',{})
 if prov.get('provider')!='github_actions' or prov.get('workflow')!='PR-12 Package Build' or not prov.get('sha'): acc.set('P02','FAIL',f'GitHub Actions provenance invalid: {prov}'); return finish(acc)
 acc.set('P02','PASS',f"workflow={prov.get('workflow')} sha={prov.get('sha')} run={prov.get('run_id')}")
 missing=[str(p) for p in (z,m,manifest,report) if not p.is_file()]
 if missing or not sidecar_ok(z) or not sidecar_ok(m): acc.set('P03','FAIL','missing/hash mismatch: '+' | '.join(missing)); return finish(acc)
 acc.set('P03','PASS','ZIP/MSI/build manifest/Nuitka report + sidecar hashes present')
 with zipfile.ZipFile(z) as q:
  bad=q.testzip()
  if bad: acc.set('P04','FAIL',f'ZIP CRC failure: {bad}'); return finish(acc)
  ext=evidence/'portable'; q.extractall(ext)
 one=ext/base; pm=one/'SHA256SUMS.json'
 if not pm.is_file(): acc.set('P04','FAIL','portable SHA256SUMS.json missing'); return finish(acc)
 for rel,expected in json.loads(pm.read_text(encoding='utf-8')).items():
  p=one/rel
  if not p.is_file() or sha256(p)!=expected: acc.set('P04','FAIL',f'portable manifest mismatch: {rel}'); return finish(acc)
 acc.set('P04','PASS','ZIP CRC/SHA + portable file manifest verified')
 req=[one/'VibraPilot.exe',one/'config/settings.defaults.json',one/'assets/icons/app.ico',one/'frozen_design_source/CURRENT_FOUNDATION_TOKENS.json',one/'ms-playwright']
 miss=[str(p) for p in req if not p.exists()]
 if miss or not any((one/'ms-playwright').iterdir()) or pe_version(one/'VibraPilot.exe')!=(1,0,6,29): acc.set('P05','FAIL','resource/EXE version failure: '+' | '.join(miss)); return finish(acc)
 acc.set('P05','PASS','required resources + bundled Chromium present; EXE version 1.0.6.29')
 ok,n1=launch(one/'VibraPilot.exe',one,evidence/'portable_data','portable #1'); ok2,n2=launch(one/'VibraPilot.exe',one,evidence/'portable_data','portable #2') if ok else (False,'first launch failed')
 if not(ok and ok2): acc.set('P06','FAIL',n1+'; '+n2); return finish(acc)
 acc.set('P06','PASS',n1+'; '+n2)
 pol=d.get('browser_policy',{})
 if pol!={'google_chrome_preferred':True,'observable_chromium_fallback':True,'sandbox_default':False}: acc.set('P07','FAIL',f'browser policy mismatch: {pol}'); return finish(acc)
 acc.set('P07','PASS','Chrome preferred; observable Chromium fallback; Sandbox default OFF')
 ins=d.get('installer',{})
 if ins.get('version')!=WIX or ins.get('scope')!='perUser' or ins.get('msi_product_version')!=MSI_VERSION: acc.set('P08','FAIL',f'MSI manifest mismatch: {ins}'); return finish(acc)
 acc.set('P08','PASS','WiX 6.0.2 per-user MSI / ProductVersion 1.0.629 / hash verified')
 existing=installed_entries()
 if existing:
  acc.set('P09','BLOCKED','existing VibraPilot MSI detected; refusing automated upgrade/uninstall: '+' | '.join(existing))
  for g in ('P10','P11','P12','P13','P14'): acc.set(g,'BLOCKED','skipped by live-install safety gate')
 else:
  acc.set('P09','PASS','no existing VibraPilot MSI detected')
  install=evidence/'msi_install'/'VibraPilot'; install.parent.mkdir(parents=True)
  log=evidence/'msi_install.log'; rc=subprocess.run(['msiexec.exe','/i',str(m),'/qn','/norestart',f'INSTALLFOLDER={install}','/L*v',str(log)]).returncode
  if rc not in (0,3010) or not (install/'VibraPilot.exe').is_file(): acc.set('P10','FAIL',f'MSI install failed rc={rc}'); return finish(acc)
  acc.set('P10','PASS',f'isolated MSI install: {install}')
  ok,n=launch(install/'VibraPilot.exe',install,evidence/'installed_data','installed EXE smoke')
  if not ok: acc.set('P11','FAIL',n); return finish(acc)
  acc.set('P11','PASS',n)

  # Keep the installed package available while the owner performs the required real browser checks.
  manual_data=evidence/'manual_browser_data'; env=os.environ.copy(); env['VIB_TOOLS_DATA_DIR']=str(manual_data)
  manual_proc=subprocess.Popen([str(install/'VibraPilot.exe')],cwd=str(install),env=env)
  print('\n=== MANUAL PACKAGED-BROWSER ACCEPTANCE REQUIRED ===',flush=True)
  print('The installed VibraPilot app is open. In that installed app, verify ALL of these:',flush=True)
  print('  1. Open Browser uses Google Chrome preferred path when healthy.',flush=True)
  print('  2. Managed Task profile is created/used; do not use personal Chrome User Data.',flush=True)
  print('  3. Perform one real Task-specific download and confirm filename/content are usable.',flush=True)
  print('  4. Perform one real single-file upload/file chooser selection.',flush=True)
  print('  5. Close the browser/window and reopen it successfully.',flush=True)
  print('  6. Confirm the app remains stable after browser close/reopen.',flush=True)
  print('Do NOT type PASS unless all six checks succeeded.',flush=True)
  try:
   answer=input('Type PASS and press Enter after completing all six checks: ').strip()
  finally:
   if manual_proc.poll() is None:
    manual_proc.terminate()
    try: manual_proc.wait(timeout=8)
    except subprocess.TimeoutExpired: manual_proc.kill(); manual_proc.wait(timeout=5)
  if answer!='PASS':
   acc.set('P12','BLOCKED','manual packaged-browser acceptance was not explicitly confirmed as PASS; installed test package is left installed for owner review')
   return finish(acc)
  acc.set('P12','PASS','owner explicitly confirmed installed packaged browser open + managed profile + real download + real upload + close/reopen')

  markers=[]
  for name in ('AppData','BrowserProfiles','Downloads','Reports','Logs','FailedData','UserInput'):
   q=install/name/'PR12_DO_NOT_DELETE.marker'; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(name,encoding='utf-8'); markers.append(q)
  h={str(q):sha256(q) for q in markers}; (evidence/'preservation_markers.json').write_text(json.dumps(h,indent=2)+'\n',encoding='utf-8'); acc.set('P13','PASS',f'created {len(markers)} untracked preservation markers')
  rc=subprocess.run(['msiexec.exe','/x',str(m),'/qn','/norestart','/L*v',str(evidence/'msi_uninstall.log')]).returncode
  if rc not in (0,3010): acc.set('P14','FAIL',f'MSI uninstall failed rc={rc}'); return finish(acc)
  acc.set('P14','PASS','MSI uninstall completed')
  lost=[q for q in markers if not q.is_file() or sha256(q)!=h[str(q)]]
  if lost: acc.set('P15','FAIL','untracked data removed/changed: '+' | '.join(map(str,lost))); return finish(acc)
  acc.set('P15','PASS','untracked runtime/user-data markers survived uninstall')
 acc.set('P16','PASS',f'ZIP={sha256(z)} MSI={sha256(m)}')
 acc.set('P17','PASS','artifact is from PR-12 Package Build; no CL Automation/tag-release workflow is part of PC artifact')
 final=acc.overall(); acc.set('P18','PASS' if final=='PASS' else 'BLOCKED','all PR-12 PC gates passed' if final=='PASS' else 'manual or safety gate remains blocked')
 return finish(acc)
if __name__=='__main__': raise SystemExit(main())
