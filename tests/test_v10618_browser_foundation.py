from __future__ import annotations
import json, re, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from vibrapilot.browser_diagnostics import browser_diagnostics_summary, build_browser_diagnostics, persist_browser_diagnostics, sanitize_command_argument, sanitize_launch_kwargs

ROOT=Path(__file__).resolve().parents[1]
class BrowserFoundationTest(unittest.TestCase):
 def test_scope_and_conditional_sandbox_boundary(self):
  s=json.loads((ROOT/'config/verification/v1.0.6.18_browser_foundation_scope.json').read_text())
  self.assertEqual(s['plan_id'],'VP-BROWSER-FOUNDATION-STABILIZATION-001'); self.assertEqual(s['target_version'],'1.0.6.18')
  self.assertFalse(s['sandbox_default_change_applied']); self.assertEqual(s['windows_sandbox_on_acceptance'],'RUNTIME_TEST_BLOCKED_NON_WINDOWS_ENVIRONMENT')
  defaults=json.loads((ROOT/'config/settings.defaults.json').read_text()); current=(ROOT/'config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json').is_file(); self.assertIs(defaults['sandbox_enabled'], True if current else False); self.assertIs(defaults['use_chrome_channel'],True); self.assertIs(defaults['allow_chromium_fallback'], False if current else True)
 def test_sanitization(self):
  x=sanitize_launch_kwargs({'channel':'chrome','env':{'PRIVATE_TOKEN':'secret'},'args':['--api-key=secret']})
  self.assertNotIn('secret',json.dumps(x)); self.assertEqual(sanitize_command_argument('--api-key=secret'),'--api-key=<redacted>')
 def test_google_chrome_process_identity(self):
  settings={'sandbox_enabled':False,'allow_chromium_fallback':True,'persistent_profile_directory':'','http_cache_enabled':False,'viewport_width':1280,'viewport_height':720,'device_scale_factor':1.0,'proxy':'','dns_host_resolver_rules':'','user_agent':''}
  from vibrapilot.chrome_runtime import ChromeRuntimeInfo
  trusted=ChromeRuntimeInfo(True,'available',Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),'140','Google Chrome','programfiles',publisher='Google LLC',signature_trusted=True)
  with patch('vibrapilot.browser_diagnostics.collect_windows_browser_process',return_value={'status':'found','profile_path':r'C:\Profiles\slot_1','pid':1,'executable_path':r'C:\Program Files\Google\Chrome\Application\chrome.exe','command_line':'chrome'}), patch('vibrapilot.browser_diagnostics.discover_google_chrome',return_value=trusted), patch('vibrapilot.browser_diagnostics.collect_cdp_browser_metadata',return_value={'product':'Chrome/140.0'}), patch('vibrapilot.browser_diagnostics.collect_page_environment',return_value={'webdriver':True}):
   r=build_browser_diagnostics(slot_id=1,settings=settings,requested_launch_kwargs={'channel':'chrome'},effective_launch_kwargs={'channel':'chrome'},context=object(),page=object(),user_data_dir=Path('x'),fallback_used=False,fallback_reason='',persistent_context=True)
  self.assertEqual(r['actual']['engine'],'google_chrome'); self.assertEqual(r['actual']['engine_evidence'],'confirmed_by_trusted_windows_process_path')
 def test_fallback_is_not_claimed_as_google_chrome(self):
  settings={'sandbox_enabled':False,'allow_chromium_fallback':True,'persistent_profile_directory':'','http_cache_enabled':False,'viewport_width':1280,'viewport_height':720,'device_scale_factor':1.0,'proxy':'','dns_host_resolver_rules':'','user_agent':''}
  with patch('vibrapilot.browser_diagnostics.collect_windows_browser_process',return_value={'status':'not_found'}), patch('vibrapilot.browser_diagnostics.collect_cdp_browser_metadata',return_value={'product':'Chrome/140'}), patch('vibrapilot.browser_diagnostics.collect_page_environment',return_value={}):
   r=build_browser_diagnostics(slot_id=2,settings=settings,requested_launch_kwargs={'channel':'chrome'},effective_launch_kwargs={},context=object(),page=object(),user_data_dir=Path('/tmp/x'),fallback_used=True,fallback_reason='missing chrome',persistent_context=True)
  self.assertEqual(r['actual']['engine'],'playwright_chromium_fallback'); self.assertTrue(r['launch']['fallback_used'])
 def test_persist_and_summary(self):
  r={'schema_version':1,'slot_id':1,'actual':{'engine':'google_chrome','product':'Chrome/140','executable_path':'chrome.exe','profile_path':'p'},'requested':{'sandbox_enabled':True},'launch':{'fallback_used':False}}
  with tempfile.TemporaryDirectory() as td:
   ts,latest=persist_browser_diagnostics(td,1,r); self.assertTrue(ts.is_file()); self.assertEqual(json.loads(latest.read_text()),r)
  self.assertIn('engine=google_chrome',browser_diagnostics_summary(r)); self.assertIn('sandbox=on',browser_diagnostics_summary(r))
 def test_no_detection_evasion(self):
  s=(ROOT/'src/vibrapilot/browser_diagnostics.py').read_text(); low=s.lower(); self.assertNotIn('stealth',low); self.assertIsNone(re.search(r'navigator\.webdriver\s*=(?!=)',s)); self.assertNotIn('object.defineproperty(navigator',low)
 def test_backend_connection(self):
  s=(ROOT/'src/vibrapilot/backend.py').read_text(); self.assertIn('def _capture_browser_foundation_diagnostics',s); self.assertIn('Browser diagnostics evidence saved:',s); self.assertNotIn('falling back to bundled Chromium',s); self.assertIn('does not fall back to Chromium',s)
if __name__=='__main__': unittest.main()
