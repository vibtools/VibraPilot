from __future__ import annotations
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCOPE=ROOT/"config/verification/v1.0.6.16_workspace_persistence_verification_fix_scope.json"
class V10616WorkspacePersistenceVerificationFixTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.scope=json.loads(SCOPE.read_text(encoding="utf-8"))
 def test_scope_locks_exact_v10615_baseline_and_no_runtime_change(self):
  self.assertEqual(self.scope["official_baseline"],"VibraPilot v1.0.6.15"); self.assertEqual(self.scope["official_baseline_github_commit"],"564dc159856e2e3255a1d8c101086e291bdca110"); self.assertEqual(self.scope["failed_github_actions_job"],93315001000); self.assertTrue(self.scope["no_production_runtime_change"]); self.assertTrue(self.scope["no_database_schema_change"]); self.assertEqual(self.scope["required_taskruntime_schema_version"],1)
 def test_v10615_runtime_files_are_byte_frozen(self):
  current=ROOT/"config/verification/v1.0.6.17_browser_capabilities_scope.json"
  allowed=set()
  if current.is_file(): allowed.update(json.loads(current.read_text(encoding="utf-8")).get("allowed_runtime_source_changes",[]))
  for r,e in self.scope["runtime_byte_frozen_sha256"].items():
   if r in allowed: continue
   self.assertEqual(hashlib.sha256((ROOT/r).read_bytes()).hexdigest(),e,r)
 def test_historical_qt_fixture_models_workspace_save_callback(self):
  t=(ROOT/"tests/test_v10612_browser_ui_lifecycle.py").read_text(encoding="utf-8"); self.assertIn("schedule_workspace_save=lambda: None",t); self.assertIn("slot = TaskSlotWidget(fake, 1)",t)
 def test_update_log_has_no_trailing_whitespace(self):
  for n,l in enumerate((ROOT/"UPDATE_LOG.md").read_text(encoding="utf-8").splitlines(),1): self.assertEqual(l,l.rstrip(" \t"),f"UPDATE_LOG.md:{n}")
if __name__=="__main__": unittest.main()
