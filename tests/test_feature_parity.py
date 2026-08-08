from __future__ import annotations
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FeatureParityTest(unittest.TestCase):
    def test_license_configuration_is_source_controlled(self):
        text=(ROOT/'src/vibrapilot/backend.py').read_text(encoding='utf-8')
        self.assertIn('LICENSE_API_BASE_URL = "https://', text)
        self.assertIn('LICENSE_API_KEY = "', text)
        self.assertNotIn('VIB_TOOLS_LICENSE_API_KEY', text)
        self.assertNotIn('VIB_TOOLS_LICENSE_API_KEY',text)

    def test_primary_pages_exist(self):
        text=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        for page in ['Dashboard','Tasks','Reports','Live Logs','App Settings','Browser Settings','About']:
            self.assertIn(page,text)


    def test_settings_navigation_order(self):
        text=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        self.assertIn('NAV_SECTIONS = ["Dashboard", "Tasks", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]', text)

    def test_browser_settings_page_and_runtime_markers(self):
        ui=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        backend=(ROOT/'src/vibrapilot/backend.py').read_text(encoding='utf-8')
        self.assertIn('def make_browser_settings_page(self) -> QWidget:', ui)
        self.assertIn('def save_browser_settings(self) -> None:', ui)
        self.assertIn('"Browser Settings": "search"', ui)
        for marker in [
            'navigation_wait_until', 'allow_chromium_fallback', 'block_images',
            'preserve_storage_state_on_recycle', 'scroll_before_interaction',
            'network_idle_timeout', 'notification_poll_interval',
        ]:
            self.assertIn(marker, ui)
            self.assertIn(marker, backend)

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
