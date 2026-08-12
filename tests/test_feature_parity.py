from __future__ import annotations
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FeatureParityTest(unittest.TestCase):
    def test_secure_api_v2_license_configuration(self):
        backend=(ROOT/'src/vibrapilot/backend.py').read_text(encoding='utf-8')
        client=(ROOT/'src/vibrapilot/licensing_v2.py').read_text(encoding='utf-8')
        public=(ROOT/'config/AppConfig/licensing_public.py').read_text(encoding='utf-8')
        self.assertIn('LICORA_API_BASE_URL = "https://', public)
        self.assertIn('LICORA_APP_ID = "vibrapilot"', public)
        for path in ['/api/v2/activate.php','/api/v2/status.php','/api/v2/refresh.php','/api/v2/deactivate.php']:
            self.assertIn(path, public)
        combined=backend+client+public
        self.assertNotIn('LICENSE_API_KEY =', combined)
        self.assertNotIn('X-API-Key', combined)
        self.assertNotIn('/api/verify.php', combined)
        self.assertNotIn('VIB_TOOLS_LICENSE_API_KEY', combined)


    def test_phase02_startup_restore_and_expired_token_recheck(self):
        ui=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        self.assertIn('"Restoring secure license session…"', ui)
        self.assertIn('threading.Thread(target=restore_session, daemon=True).start()', ui)
        self.assertIn('if self.license_manager.license_key:', ui)
        self.assertNotIn(
            'if self.license_manager.is_activated() and self.license_manager.license_key:',
            ui,
        )

    def test_primary_pages_exist(self):
        text=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        pages=['Dashboard','Tasks','Workflows','Workflow Inputs','Reports','Live Logs','App Settings','Browser Settings','About']
        if (ROOT/'config/verification/v1.0.6.30_workflow_plugin_system_scope.json').is_file():
            pages.append('Workflow Settings')
        for page in pages:
            self.assertIn(page,text)


    def test_settings_navigation_order(self):
        text=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        current_scope = ROOT/'config/verification/v1.0.6.30_workflow_plugin_system_scope.json'
        marker = ('NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Workflow Settings", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]' if current_scope.is_file() else 'NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]')
        self.assertIn(marker, text)

    def test_browser_settings_page_and_runtime_markers(self):
        ui=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        backend=(ROOT/'src/vibrapilot/backend.py').read_text(encoding='utf-8')
        share=(ROOT/'src/vibrapilot/workflow/share_invite/workflow.py').read_text(encoding='utf-8')
        runtime=backend+'\n'+share
        self.assertIn('def make_browser_settings_page(self) -> QWidget:', ui)
        self.assertIn('def save_browser_settings(self) -> None:', ui)
        self.assertIn('"Browser Settings": "search"', ui)
        for marker in [
            'navigation_wait_until', 'allow_chromium_fallback', 'block_images',
            'preserve_storage_state_on_recycle', 'scroll_before_interaction',
            'network_idle_timeout', 'notification_poll_interval',
        ]:
            self.assertIn(marker, ui)
            self.assertIn(marker, runtime)

    def test_data_formats_and_exports(self):
        text=(ROOT/'src/vibrapilot/data_io.py').read_text(encoding='utf-8').lower()
        for ext in ['.txt','.csv','.xlsx','.xls']:
            self.assertIn(ext,text)
        self.assertIn('export_report_csv',text)
        self.assertIn('export_report_excel',text)

    def test_worker_event_bridge(self):
        backend=(ROOT/'src/vibrapilot/backend.py').read_text(encoding='utf-8')
        ui=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        for event in ['log','progress','status','item','security','browser','login','send_limit','done']:
            self.assertIn(f'"{event}"',backend)
            self.assertIn(f'"{event}"',ui)

if __name__ == '__main__': unittest.main()
