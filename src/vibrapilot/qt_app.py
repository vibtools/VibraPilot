"""VibraPilot — Vib Tools official desktop UI edition.

The visual shell and component styling consume the frozen Vib Tools desktop UI
contract verbatim from ``vib_validation_app``. Backend behavior is provided by
``vibrapilot.backend`` and preserves the v1.0.6 baseline licensing, browser-worker,
safety, retry, reporting-row, persistence and shutdown logic.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, QSize, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon, QKeySequence, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vib_validation_app.button_contract import apply_nav_button_contract
from vib_validation_app.focus_manager import install_keyboard_focus_ring
from vib_validation_app.styles import app_qss
from vib_validation_app.tokens import CONST, COLORS
from vib_validation_app.widgets import (
    ToggleSwitch,
    apply_accessibility,
    button,
    card,
    combo_box,
    divider,
    elide_label,
    form_group,
    hbox,
    icon,
    label,
    line_input,
    metric_card,
    page_frame,
    page_header,
    password_input,
    search_input,
    status_badge,
    text_area,
    title,
    token_chip,
    vbox,
)

from .app_config import ABOUT, APP, ENABLED_SOCIAL_LINKS, LICENSING, SUPPORT

from .backend import (
    APP_AUTHOR,
    APP_DATA_DIR,
    APP_STATE_FILE,
    APP_NAME,
    APP_VERSION,
    DEFAULT_SETTINGS,
    DEFAULT_TEST_SEND_LIMIT,
    DISPLAY_APP_NAME,
    EMAIL_RE,
    LOGS_DIR,
    REPORTS_DIR,
    ROOT_DIR,
    SETTINGS_FILE,
    TASK_RUNTIME_DB,
    AutomationWorker,
    LicenseManager,
    SettingsManager,
    TaskItem,
    TaskState,
    now_str,
    license_validation_failure_is_transient,
    safe_test_send_limit,
    validate_test_send_limit,
)
from .data_io import (
    export_report_csv,
    export_report_excel,
    parse_data,
    parse_data_with_audit,
)
from .task_runtime_store import TaskRuntimeStore
from .workflow_inputs import WORKFLOW_INPUT_FIELDS, WORKFLOW_INPUT_KEYS
from .workspace_state import WorkspaceStateStore
from .workflow import (
    WorkflowManager,
    WorkflowStateError,
    WorkflowSwitchBlockedError,
    WorkflowSwitchError,
    WorkflowStateStore,
    WorkflowSwitchTransaction,
)
from .browser_capabilities import (
    ensure_task_download_directory,
    normalize_extension_paths,
    validate_unpacked_extension_directories,
)


NAV_SECTIONS = ["Dashboard", "Tasks", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]
VIEW_NAV_SHORTCUTS = {
    "Dashboard": "Ctrl+1",
    "Tasks": "Ctrl+2",
    "Reports": "Ctrl+3",
    "Live Logs": "Ctrl+4",
    "App Settings": "Ctrl+5",
    "Browser Settings": "Ctrl+6",
}
UI_QUEUE_CAPACITY = 4096
UI_QUEUE_MAX_EVENTS_PER_TICK = 250
REPORT_RECENT_LIMIT = 1000


APP_ICON_PATH = ROOT_DIR / "assets" / "icons" / "app.ico"
APP_LOGO_PATH = ROOT_DIR / "assets" / "icons" / "app.png"


def application_icon() -> QIcon:
    """Return the source-controlled VibraPilot application icon when available."""
    return QIcon(str(APP_ICON_PATH)) if APP_ICON_PATH.is_file() else QIcon()


def brand_pixmap(size: int) -> QPixmap:
    """Return the VibraPilot logo scaled for compact UI placement."""
    if not APP_LOGO_PATH.is_file():
        return QPixmap()
    pixmap = QPixmap(str(APP_LOGO_PATH))
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def brand_icon_label(size: int, accessible_name: str | None = None) -> QLabel:
    widget = QLabel()
    widget.setFixedSize(size, size)
    widget.setAlignment(Qt.AlignCenter)
    widget.setAccessibleName(accessible_name or APP.display_name)
    pixmap = brand_pixmap(size)
    if not pixmap.isNull():
        widget.setPixmap(pixmap)
    else:
        widget.setText(APP.short_name)
    return widget


BROWSER_SETTING_GROUPS: dict[str, list[str]] = {'Browser Engine & Binary': ['browser_slot_default',
                             'browser_executable_path',
                             'headless',
                             'use_chrome_channel',
                             'allow_chromium_fallback',
                             'gpu_enabled',
                             'sandbox_enabled',
                             'browser_launch_timeout',
                             'slow_mo_delay',
                             'handle_sigint',
                             'handle_sigterm',
                             'handle_sighup'],
 'Persistent Profile & Session': ['use_persistent_context',
                                  'persistent_user_data_dir',
                                  'dedicated_profile_per_task',
                                  'persistent_profile_directory',
                                  'profile_lock_policy',
                                  'persist_profile_between_runs',
                                  'persist_profile_cache',
                                  'restore_previous_session',
                                  'browser_startup_url',
                                  'browser_context_recycle_after_n_items',
                                  'browser_context_recycle_after_n_minutes',
                                  'preserve_storage_state_on_recycle',
                                  'preserve_cookies_on_recycle',
                                  'preserve_local_storage_on_recycle',
                                  'preserve_indexeddb_on_recycle',
                                  'restore_page_after_context_recycle',
                                  're_open_after_success_per_order'],
 'Window & Display': ['start_maximized',
                      'window_width',
                      'window_height',
                      'window_position_x',
                      'window_position_y',
                      'no_viewport',
                      'viewport_width',
                      'viewport_height',
                      'screen_width',
                      'screen_height',
                      'device_scale_factor',
                      'color_scheme',
                      'reduced_motion',
                      'forced_colors',
                      'contrast',
                      'has_touch',
                      'is_mobile'],
 'Locale & Region': ['locale',
                     'accept_language',
                     'timezone_id',
                     'geolocation_enabled',
                     'geolocation_latitude',
                     'geolocation_longitude',
                     'geolocation_accuracy'],
 'Permissions': ['permission_notifications',
                 'permission_clipboard_read',
                 'permission_clipboard_write',
                 'permission_camera',
                 'permission_microphone',
                 'permission_geolocation'],
 'Downloads': ['accept_downloads', 'downloads_path'],
 'Navigation & DOM': ['page_navigation_timeout',
                      'navigation_wait_until',
                      'wait_for_network_idle',
                      'network_idle_timeout',
                      'selector_timeout',
                      'javascript_enabled',
                      'strict_selectors',
                      'page_init_script_enabled',
                      'page_init_script_path',
                      'base_url',
                      'bypass_csp'],
 'Identity & Proxy': ['user_agent', 'proxy', 'proxy_bypass', 'extra_http_headers_json'],
 'Resource Loading & Media': ['block_images',
                              'block_fonts',
                              'block_media',
                              'audio_enabled',
                              'autoplay_policy',
                              'hardware_video_decode_enabled'],
 'Security & Network': ['ignore_https_errors',
                        'client_certificates_json',
                        'allow_popups',
                        'offline',
                        'service_workers',
                        'http_cache_enabled',
                        'dns_host_resolver_rules',
                        'webrtc_ip_policy'],
 'Extensions': ['extensions_enabled', 'extension_paths'],
 'Page & Window Behavior': ['auto_focus_browser_on_open',
                            'auto_dismiss_browser_dialogs',
                            'scroll_before_interaction'],
 'DevTools & Debugging': ['devtools_auto_open', 'remote_debugging_port'],
 'Launch Arguments & Environment': ['additional_chromium_args',
                                    'ignored_default_args',
                                    'browser_env_json',
                                    'enable_chrome_features',
                                    'disable_chrome_features',
                                    'enable_blink_features',
                                    'disable_blink_features'],
 'Performance': ['background_throttling_enabled', 'renderer_process_limit'],
 'Logging & Diagnostics': ['browser_console_logging',
                           'network_event_logging',
                           'chromium_logging_enabled',
                           'chromium_log_file',
                           'record_har_enabled',
                           'record_har_directory',
                           'record_har_mode',
                           'record_har_content',
                           'crash_dumps_directory',
                           'record_har_url_filter',
                           'record_video_enabled',
                           'record_video_directory',
                           'record_video_width',
                           'record_video_height',
                           'traces_dir'],
 'Crash Recovery': ['auto_restart_browser_on_crash',
                    'browser_restart_max_attempts',
                    'browser_restart_delay'],
 'Retry & Backoff': ['max_retry_per_item',
                     'max_navigation_retry',
                     'max_selector_retry',
                     'retry_delay_min',
                     'retry_delay_max',
                     'backoff_multiplier'],
 'Network Retry': ['connection_retry_count', 'network_error_retry_delay'],
 'Inter-item Timing': ['delay_between_items_min', 'delay_between_items_max'],
 'Advanced Browser Timing': ['login_state_poll_interval',
                             'short_dom_probe_timeout',
                             'standard_dom_probe_timeout',
                             'modal_state_probe_timeout',
                             'modal_close_probe_timeout',
                             'modal_close_poll_interval',
                             'modal_close_poll_count',
                             'notification_poll_interval',
                             'notification_visibility_timeout',
                             'visible_text_timeout',
                             'text_content_timeout',
                             'security_body_read_timeout',
                             'security_body_text_limit']}
BROWSER_SETTING_KEYS = tuple(
    key for keys in BROWSER_SETTING_GROUPS.values() for key in keys
)
BROWSER_SETTING_LABELS = {'browser_slot_default': 'Browser Slot Default',
 'browser_executable_path': 'Google Chrome / Chromium Executable Path',
 'headless': 'Headless Mode',
 'use_chrome_channel': 'Use Google Chrome Channel',
 'allow_chromium_fallback': 'Allow Bundled Chromium Fallback',
 'gpu_enabled': 'GPU / Hardware Acceleration Enabled',
 'sandbox_enabled': 'Chromium Sandbox Enabled',
 'browser_launch_timeout': 'Browser Launch Timeout (ms)',
 'slow_mo_delay': 'Playwright Slow Motion Delay (ms)',
 'use_persistent_context': 'Use Persistent Browser Context',
 'persistent_user_data_dir': 'Persistent User Data Directory',
 'dedicated_profile_per_task': 'Dedicated Profile Per Task',
 'persistent_profile_directory': 'Chrome Profile Directory Name',
 'profile_lock_policy': 'Persistent Context Failure Policy',
 'persist_profile_between_runs': 'Persist Profile Between App Runs',
 'persist_profile_cache': 'Persist Browser Profile Cache',
 'restore_previous_session': 'Restore Previous Browser Session',
 'browser_startup_url': 'Optional Browser Startup URL',
 'browser_context_recycle_after_n_items': 'Recycle Context After N Items',
 'browser_context_recycle_after_n_minutes': 'Recycle Context After N Minutes',
 'preserve_storage_state_on_recycle': 'Preserve Storage State on Recycle',
 'preserve_cookies_on_recycle': 'Preserve Cookies on Recycle',
 'preserve_local_storage_on_recycle': 'Preserve LocalStorage on Recycle',
 'preserve_indexeddb_on_recycle': 'Preserve IndexedDB on Recycle',
 'restore_page_after_context_recycle': 'Restore Current Page After Recycle',
 're_open_after_success_per_order': 'Re-open Page After Successful Item',
 'start_maximized': 'Start Browser Maximized',
 'window_width': 'Window Width (px; 0 = browser default)',
 'window_height': 'Window Height (px; 0 = browser default)',
 'window_position_x': 'Window X Position (-1 = browser default)',
 'window_position_y': 'Window Y Position (-1 = browser default)',
 'no_viewport': 'Use Native / No Fixed Viewport',
 'viewport_width': 'Viewport Width (px)',
 'viewport_height': 'Viewport Height (px)',
 'screen_width': 'Emulated Screen Width (0 = unset)',
 'screen_height': 'Emulated Screen Height (0 = unset)',
 'device_scale_factor': 'Device Scale Factor',
 'color_scheme': 'Color Scheme',
 'reduced_motion': 'Reduced Motion',
 'forced_colors': 'Forced Colors',
 'contrast': 'Preferred Contrast',
 'has_touch': 'Touch Support',
 'is_mobile': 'Mobile Viewport Semantics',
 'locale': 'Locale',
 'accept_language': 'Accept-Language Header',
 'timezone_id': 'Timezone ID',
 'geolocation_enabled': 'Enable Geolocation',
 'geolocation_latitude': 'Geolocation Latitude',
 'geolocation_longitude': 'Geolocation Longitude',
 'geolocation_accuracy': 'Geolocation Accuracy (m)',
 'permission_notifications': 'Allow Notifications',
 'permission_clipboard_read': 'Allow Clipboard Read',
 'permission_clipboard_write': 'Allow Clipboard Write',
 'permission_camera': 'Allow Camera',
 'permission_microphone': 'Allow Microphone',
 'permission_geolocation': 'Grant Geolocation Permission',
 'accept_downloads': 'Accept Downloads',
 'downloads_path': 'Download Directory',
 'page_navigation_timeout': 'Page Navigation Timeout (ms)',
 'navigation_wait_until': 'Navigation Wait Strategy',
 'wait_for_network_idle': 'Best-effort Network Idle Wait',
 'network_idle_timeout': 'Network Idle Wait Timeout (ms)',
 'selector_timeout': 'DOM / Selector Operation Timeout (ms)',
 'javascript_enabled': 'JavaScript Enabled',
 'strict_selectors': 'Strict Selector Mode',
 'page_init_script_enabled': 'Enable Page Initialization Script',
 'page_init_script_path': 'Page Initialization Script File',
 'user_agent': 'Custom User Agent',
 'proxy': 'Proxy Server',
 'proxy_bypass': 'Proxy Bypass Domains',
 'extra_http_headers_json': 'Extra HTTP Headers (JSON object)',
 'block_images': 'Block Images',
 'block_fonts': 'Block Fonts',
 'block_media': 'Block Media',
 'audio_enabled': 'Audio Enabled',
 'autoplay_policy': 'Autoplay Policy',
 'hardware_video_decode_enabled': 'Hardware Video Decode Enabled',
 'ignore_https_errors': 'Ignore HTTPS Certificate Errors',
 'client_certificates_json': 'Client Certificates (JSON array)',
 'allow_popups': 'Allow Popups',
 'offline': 'Offline Network Emulation',
 'service_workers': 'Service Workers',
 'http_cache_enabled': 'HTTP Cache Enabled',
 'dns_host_resolver_rules': 'DNS / Host Resolver Rules',
 'webrtc_ip_policy': 'WebRTC IP Handling Policy',
 'extensions_enabled': 'Load Chromium Extensions',
 'extension_paths': 'Extension Directories (; separated)',
 'auto_focus_browser_on_open': 'Bring Browser to Front on Open',
 'auto_dismiss_browser_dialogs': 'Auto-dismiss Browser Dialogs',
 'scroll_before_interaction': 'Scroll Element Into View Before Interaction',
 'devtools_auto_open': 'Auto-open DevTools',
 'remote_debugging_port': 'Remote Debugging / CDP Port (0 = disabled, loopback only)',
 'additional_chromium_args': 'Additional Chromium Arguments',
 'ignored_default_args': 'Ignored Playwright Default Arguments',
 'browser_env_json': 'Browser Environment Variables (JSON object)',
 'enable_chrome_features': 'Enable Chrome Features',
 'disable_chrome_features': 'Disable Chrome Features',
 'enable_blink_features': 'Enable Blink Features',
 'disable_blink_features': 'Disable Blink Features',
 'background_throttling_enabled': 'Background Throttling Enabled',
 'renderer_process_limit': 'Renderer Process Limit (0 = browser default)',
 'browser_console_logging': 'Log Browser Console',
 'network_event_logging': 'Log Browser Network Events',
 'chromium_logging_enabled': 'Enable Chromium Internal Logging',
 'chromium_log_file': 'Chromium Log File',
 'record_har_enabled': 'Record Network HAR',
 'record_har_directory': 'HAR Output Directory',
 'record_har_mode': 'HAR Mode',
 'record_har_content': 'HAR Content Mode',
 'crash_dumps_directory': 'Crash Dump Directory',
 'auto_restart_browser_on_crash': 'Automatically Restart Browser After Crash',
 'browser_restart_max_attempts': 'Maximum Automatic Browser Restarts',
 'browser_restart_delay': 'Browser Restart Delay (s)',
 'max_retry_per_item': 'Maximum Retry Per Item',
 'max_navigation_retry': 'Maximum Navigation Retry',
 'max_selector_retry': 'Maximum DOM / Selector Retry',
 'retry_delay_min': 'Retry Delay Minimum (s)',
 'retry_delay_max': 'Retry Delay Maximum (s)',
 'backoff_multiplier': 'Retry Backoff Multiplier',
 'connection_retry_count': 'Connection Retry Count',
 'network_error_retry_delay': 'Network Error Retry Delay (s)',
 'delay_between_items_min': 'Delay Between Items Minimum (s)',
 'delay_between_items_max': 'Delay Between Items Maximum (s)',
 'login_state_poll_interval': 'Browser Login-state Poll Interval (s)',
 'short_dom_probe_timeout': 'Short DOM Probe Timeout (ms)',
 'standard_dom_probe_timeout': 'Standard DOM Probe Timeout (ms)',
 'modal_state_probe_timeout': 'Modal State Probe Timeout (ms)',
 'modal_close_probe_timeout': 'Modal Close Probe Timeout (ms)',
 'modal_close_poll_interval': 'Modal Close Poll Interval (s)',
 'modal_close_poll_count': 'Modal Close Poll Count',
 'notification_poll_interval': 'Notification Poll Interval (s)',
 'notification_visibility_timeout': 'Notification Visibility Timeout (ms)',
 'visible_text_timeout': 'Visible Text Probe Timeout (ms)',
 'text_content_timeout': 'Text Content Read Timeout (ms)',
 'security_body_read_timeout': 'Security Page Body Read Timeout (ms)',
 'security_body_text_limit': 'Security Page Text Scan Limit (characters)',
 'handle_sigint': 'Handle SIGINT / Ctrl-C',
 'handle_sigterm': 'Handle SIGTERM',
 'handle_sighup': 'Handle SIGHUP',
 'traces_dir': 'Playwright Traces Directory',
 'bypass_csp': 'Bypass Content Security Policy',
 'base_url': 'Playwright Base URL',
 'record_har_url_filter': 'HAR URL Filter',
 'record_video_enabled': 'Record Browser Video',
 'record_video_directory': 'Browser Video Output Directory',
 'record_video_width': 'Recorded Video Width (0 = automatic)',
 'record_video_height': 'Recorded Video Height (0 = automatic)'}
BROWSER_SETTING_COMBO_CHOICES = {'navigation_wait_until': ['commit', 'domcontentloaded', 'load', 'networkidle'],
 'profile_lock_policy': ['fail', 'fallback_ephemeral'],
 'color_scheme': ['default', 'light', 'dark', 'no-preference'],
 'reduced_motion': ['default', 'reduce', 'no-preference'],
 'forced_colors': ['default', 'active', 'none'],
 'contrast': ['default', 'more', 'no-preference'],
 'service_workers': ['allow', 'block'],
 'webrtc_ip_policy': ['default',
                      'default_public_interface_only',
                      'default_public_and_private_interfaces',
                      'disable_non_proxied_udp'],
 'autoplay_policy': ['default',
                     'no-user-gesture-required',
                     'user-gesture-required',
                     'document-user-activation-required'],
 'record_har_mode': ['full', 'minimal'],
 'record_har_content': ['embed', 'attach', 'omit']}

def _message(parent: QWidget, title_text: str, text: str, level: str = "info") -> None:
    if level == "error":
        QMessageBox.critical(parent, title_text, text)
    elif level == "warning":
        QMessageBox.warning(parent, title_text, text)
    else:
        QMessageBox.information(parent, title_text, text)


def _confirm(parent: QWidget, title_text: str, text: str) -> bool:
    return (
        QMessageBox.question(
            parent,
            title_text,
            text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        == QMessageBox.Yes
    )


class SettingsToggleSwitch(ToggleSwitch):
    """Settings-only toggle with a hit area matching its painted track.

    The shared Vib Tools ToggleSwitch is a custom-painted QCheckBox. On Windows,
    QCheckBox's native hit test can be narrower than the visible 36x20 track when
    the checkbox text is empty, so clicks on parts of the painted switch may not
    toggle state. Settings requires the whole visible track to be interactive.
    """

    def hitButton(self, pos) -> bool:  # type: ignore[override]
        return self.rect().contains(pos)


class ActivationPage(QWidget):
    """Scope-locked compact Licora activation window for general users."""

    WINDOW_BACKGROUND = "#0F172A"
    SURFACE = "#1E293B"
    BORDER = "#334155"
    PRIMARY = "#3B82F6"
    PRIMARY_HOVER = "#2563EB"
    TEXT_PRIMARY = "#F8FAFC"
    TEXT_LABEL = "#E2E8F0"
    TEXT_SECONDARY = "#94A3B8"
    TEXT_FOOTER = "#64748B"
    SUCCESS = "#10B981"

    def __init__(self, app: "MainWindow") -> None:
        super().__init__()
        self.app = app
        self._transition_requested = False
        self.setObjectName("ActivationRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        content = QWidget()
        content.setObjectName("ActivationContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 1. Brand header — centered, compact and free of developer metadata.
        brand_icon = brand_icon_label(48, APP.display_name)
        brand_icon.setObjectName("ActivationBrandIcon")
        lay.addWidget(brand_icon, 0, Qt.AlignHCenter)
        lay.addSpacing(12)

        brand_title = QLabel(f"{APP.display_name} Activation")
        brand_title.setObjectName("ActivationTitle")
        brand_title.setAlignment(Qt.AlignCenter)
        brand_title.setAccessibleName(f"{APP.display_name} Activation")
        lay.addWidget(brand_title)
        lay.addSpacing(6)

        subtitle = QLabel(f"Enter your license key to unlock {APP.display_name}")
        subtitle.setObjectName("ActivationSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(False)
        lay.addWidget(subtitle)

        # Activation feedback is preserved inside the specified 32px header/form gap
        # so runtime messages never change the locked layout geometry.
        self.status = QLabel("")
        self.status.setObjectName("ActivationStatus")
        self.status.setFixedHeight(18)
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setProperty("activationState", "idle")
        lay.addWidget(self.status)
        lay.addSpacing(14)

        # 2. Form section — exact 44px touch/eye-friendly fields.
        email_label = QLabel("Email Address (Optional)")
        email_label.setObjectName("ActivationFieldLabel")
        lay.addWidget(email_label)
        lay.addSpacing(8)

        self.email = line_input("name@example.com", self.app.license_manager.user_email)
        self.email.setObjectName("ActivationEmailInput")
        self.email.setFixedHeight(44)
        self.email.setAccessibleName("Email Address (Optional)")
        lay.addWidget(self.email)
        lay.addSpacing(20)

        license_label = QLabel("License Key")
        license_label.setObjectName("ActivationFieldLabel")
        lay.addWidget(license_label)
        lay.addSpacing(8)

        self.license_key = password_input(self.app.license_manager.license_key)
        self.license_key.setObjectName("ActivationLicenseInput")
        self.license_key.setPlaceholderText("VT-XXXX-XXXX-XXXX-XXXX")
        self.license_key.setFixedHeight(44)
        self.license_key.setAccessibleName("License Key")
        lay.addWidget(self.license_key)
        lay.addSpacing(28)

        # 3. Full-width primary CTA.
        self.activate_button = button("Activate License", "primary")
        self.activate_button.setObjectName("ActivationPrimaryButton")
        self.activate_button.setFixedHeight(44)
        self.activate_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.activate_button.clicked.connect(self.activate)
        lay.addWidget(self.activate_button)

        # 4. Trust footer — exactly 24px below the primary action.
        lay.addSpacing(24)
        trust = QLabel("🔒 Secured by Licora Activation Engine")
        trust.setObjectName("ActivationTrust")
        trust.setAlignment(Qt.AlignCenter)
        trust.setAccessibleName("Secured by Licora Activation Engine")
        lay.addWidget(trust)

        root.addWidget(content)
        root.addStretch(1)

    @classmethod
    def activation_qss(cls) -> str:
        return f"""
        QWidget#ActivationRoot,
        QWidget#ActivationContent {{
            background: {cls.WINDOW_BACKGROUND};
            border: none;
            font-family: "Segoe UI";
        }}

        QLabel#ActivationBrandIcon {{
            background: {cls.SURFACE};
            color: {cls.PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: 12px;
            font-family: "Segoe UI";
            font-size: 16px;
            font-weight: 700;
        }}

        QLabel#ActivationTitle {{
            background: transparent;
            color: {cls.TEXT_PRIMARY};
            border: none;
            font-family: "Segoe UI";
            font-size: 22px;
            font-weight: 700;
        }}

        QLabel#ActivationSubtitle {{
            background: transparent;
            color: {cls.TEXT_SECONDARY};
            border: none;
            font-family: "Segoe UI";
            font-size: 13px;
            font-weight: 400;
        }}

        QLabel#ActivationFieldLabel {{
            background: transparent;
            color: {cls.TEXT_LABEL};
            border: none;
            font-family: "Segoe UI";
            font-size: 14px;
            font-weight: 500;
        }}

        QLineEdit#ActivationEmailInput,
        QLineEdit#ActivationLicenseInput {{
            min-height: 44px;
            max-height: 44px;
            background: {cls.SURFACE};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding-left: 12px;
            padding-right: 12px;
            font-family: "Segoe UI";
            font-size: 14px;
            font-weight: 400;
            placeholder-text-color: {cls.TEXT_SECONDARY};
            selection-background-color: {cls.PRIMARY};
            selection-color: #FFFFFF;
        }}

        QLineEdit#ActivationLicenseInput {{
            padding-right: 36px;
        }}

        QLineEdit#ActivationEmailInput:hover,
        QLineEdit#ActivationLicenseInput:hover {{
            border: 1px solid {cls.BORDER};
            background: {cls.SURFACE};
        }}

        QLineEdit#ActivationEmailInput:focus,
        QLineEdit#ActivationLicenseInput:focus,
        QLineEdit#ActivationEmailInput[keyboardFocus="true"],
        QLineEdit#ActivationLicenseInput[keyboardFocus="true"] {{
            border: 1px solid {cls.PRIMARY};
            background: {cls.SURFACE};
        }}

        QPushButton#ActivationPrimaryButton {{
            min-height: 44px;
            max-height: 44px;
            min-width: 0px;
            background: {cls.PRIMARY};
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 0px 12px;
            font-family: "Segoe UI";
            font-size: 15px;
            font-weight: 600;
        }}

        QPushButton#ActivationPrimaryButton:hover {{
            background: {cls.PRIMARY_HOVER};
            color: #FFFFFF;
            border: none;
        }}

        QPushButton#ActivationPrimaryButton:pressed {{
            background: {cls.PRIMARY_HOVER};
            color: #FFFFFF;
            border: none;
        }}

        QPushButton#ActivationPrimaryButton[keyboardFocus="true"] {{
            background: {cls.PRIMARY};
            color: #FFFFFF;
            border: 1px solid {cls.TEXT_PRIMARY};
            padding: 0px 11px;
        }}

        QPushButton#ActivationPrimaryButton:disabled {{
            background: {cls.BORDER};
            color: {cls.TEXT_SECONDARY};
            border: none;
        }}

        QLabel#ActivationStatus {{
            background: transparent;
            color: {cls.TEXT_SECONDARY};
            border: none;
            font-family: "Segoe UI";
            font-size: 12px;
            font-weight: 400;
        }}

        QLabel#ActivationStatus[activationState="success"] {{
            color: {cls.SUCCESS};
        }}

        QLabel#ActivationTrust {{
            background: transparent;
            color: {cls.TEXT_FOOTER};
            border: none;
            font-family: "Segoe UI";
            font-size: 12px;
            font-weight: 400;
        }}
        """

    def _set_status_state(self, state: str, text: str) -> None:
        self.status.setText(text)
        self.status.setProperty("activationState", state)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def activate(self) -> None:
        if self._transition_requested:
            return
        key = self.license_key.text().strip()
        email = self.email.text().strip()
        self.activate_button.setEnabled(False)
        self._set_status_state("pending", "Validating license…")

        def run() -> None:
            ok, msg = self.app.license_manager.validate(key, email)
            self.app.ui_queue.put(
                (
                    "activation_result",
                    {"slot_id": 0, "ok": ok, "message": msg},
                )
            )

        threading.Thread(target=run, daemon=True).start()

    def finish(self, ok: bool, message: str) -> None:
        self._set_status_state("success" if ok else "error", message)
        if ok:
            # Keep the CTA disabled once activation succeeds. This prevents a second
            # validation result from scheduling another workspace transition while
            # the 250 ms success message is visible.
            self._transition_requested = True
            self.activate_button.setEnabled(False)
            QTimer.singleShot(250, self.app.show_workspace)
        else:
            self.activate_button.setEnabled(True)


class TaskSlotWidget(QFrame):
    """One independent browser/task slot using the frozen Vib Tools card contract."""

    def __init__(self, app: "MainWindow", slot_id: int) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.app = app
        self.slot_id = slot_id
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.worker: AutomationWorker | None = None
        self.browser_lifecycle_state = "Closed"
        self.browser_action_button: QPushButton | None = None
        self.state = TaskState(
            slot_id=slot_id,
            target_url=str(app.settings.get("default_target_url", DEFAULT_SETTINGS["default_target_url"])),
        )
        self.loaded_path: Path | None = None
        self.import_audit = None
        # Task-page-only responsive spacing state.  The values are derived from
        # the containing Tasks viewport so the approved percentage contract
        # scales with the application window without touching task behavior.
        self._task_root_layout: QVBoxLayout | None = None
        self._task_top_layout: QVBoxLayout | None = None
        self._task_separator_layout: QVBoxLayout | None = None
        self._task_target_layout: QHBoxLayout | None = None
        self._task_metrics_grid: QGridLayout | None = None
        self._task_metric_layouts: list[QVBoxLayout] = []
        self._task_upload_button: QPushButton | None = None
        self._task_spacing_signature: tuple[int, ...] | None = None
        self._build()
        QTimer.singleShot(0, self._apply_task_spacing_contract)

    @classmethod
    def task_qss(cls) -> str:
        """Task-page-only QSS for the approved compact monitoring layout."""
        return """
            QFrame[vibTaskCard="compact-v1"] {
                background: #111722;
                border: 1px solid #1E2633;
                border-radius: 8px;
            }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskStartButton {
                min-height: 26px; max-height: 26px;
                background: #3B82F6; color: #FFFFFF;
                border: 1px solid #3B82F6; border-radius: 6px;
                padding: 0 8px; font-size: 11px; font-weight: 600;
            }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskStartButton:hover { background: #2563EB; }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskPauseButton,
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskResumeButton {
                min-height: 26px; max-height: 26px;
                background: #334155; color: #F8FAFC;
                border: 1px solid #475569; border-radius: 6px;
                padding: 0 8px; font-size: 11px; font-weight: 600;
            }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskPauseButton:hover,
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskResumeButton:hover { background: #475569; }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskStopButton {
                min-height: 26px; max-height: 26px;
                background: #1A212E; color: #FCA5A5;
                border: 1px solid #7F1D1D; border-radius: 6px;
                padding: 0 8px; font-size: 11px; font-weight: 600;
            }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskStopButton:hover {
                background: #7F1D1D; color: #FFFFFF;
            }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskOpenBrowserButton,
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskDownloadsButton,
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskCloseButton {
                min-height: 26px; max-height: 26px; border-radius: 6px;
                padding: 0 8px; font-size: 11px;
            }
            QFrame[vibTaskCard="compact-v1"] QLineEdit#TaskUrlInput {
                min-height: 28px; max-height: 28px;
                background: #161D2A; color: #F8FAFC;
                border: 1px solid #334155; border-radius: 8px;
                padding: 0 12px;
            }
            QFrame[vibTaskCard="compact-v1"] QLineEdit#TaskUrlInput:focus { border: 1px solid #38BDF8; }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskUploadButton {
                min-height: 28px; max-height: 28px;
                background: #1E293B; color: #F8FAFC;
                border: 1px solid #334155; border-radius: 8px;
                padding: 0 8px; font-size: 11px; font-weight: 600;
            }
            QFrame[vibTaskCard="compact-v1"] QPushButton#TaskUploadButton:hover { background: #334155; }
            QFrame[vibTaskCard="compact-v1"] QLabel#TaskDataBadge {
                min-height: 22px; max-height: 22px;
                background: transparent; color: #94A3B8;
                border: none;
                padding: 0; font-size: 12px;
            }
            QFrame#TaskMetric {
                min-height: 32px; max-height: 32px;
                background: rgba(255,255,255,8);
                border: none; border-radius: 7px;
            }
            QLabel#TaskMetricLabel { color: #94A3B8; font-size: 10px; }
            QLabel#TaskMetricValue, QLabel#TaskMetricValueSuccess, QLabel#TaskMetricValueFailed {
                color: #F8FAFC; font-size: 12px; font-weight: 700;
            }
            QLabel#TaskMetricValueSuccess { color: #10B981; }
            QLabel#TaskMetricValueFailed { color: #EF4444; }
            QFrame#TaskToolbarSeparator {
                background: #334155; border: none;
                min-width: 1px; max-width: 1px;
                min-height: 22px; max-height: 22px;
            }
            QFrame#TaskBrowserStatusPill {
                background: transparent; border: none;
                min-height: 26px; max-height: 26px;
            }
            QFrame#TaskBrowserStatusDot {
                min-width: 8px; max-width: 8px;
                min-height: 8px; max-height: 8px;
                border: none; border-radius: 4px;
                background: #94A3B8;
            }
            QFrame#TaskBrowserStatusDot[browserState="open"] { background: #10B981; }
            QFrame#TaskBrowserStatusDot[browserState="closed"] { background: #EF4444; }
            QFrame#TaskBrowserStatusDot[browserState="neutral"] { background: #94A3B8; }
            QLabel#TaskBrowserStatusText {
                background: transparent; border: none;
                color: #94A3B8; font-size: 12px;
                padding: 0;
            }
            QLabel#TaskSubtitle {
                background: transparent; border: none;
                color: #64748B; font-size: 10px;
                padding: 0;
            }
            QPushButton#TasksOpenClosedButton, QPushButton#TasksAddButton {
                min-height: 24px; max-height: 24px;
                padding: 0 8px; font-size: 11px;
            }
            QProgressBar#TaskProgress {
                min-height: 3px; max-height: 3px;
                border: none; border-radius: 1px; background: #1E293B;
            }
            QProgressBar#TaskProgress::chunk { background: #3B82F6; border-radius: 1px; }
            """

    def _build(self) -> None:
        # Scope-locked Tasks-page density/clarity repair. Every existing action,
        # metric and backend binding is preserved; only presentation is changed.
        self.setProperty("vibTaskCard", "compact-v1")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Fixed-pixel compact layout: no viewport-percentage padding or gaps.
        root = vbox(self, margins=(12, 12, 12, 12), spacing=8)
        self._task_root_layout = root

        # Row 1: task identity + three clearly separated toolbar groups.
        top_section = QWidget()
        top_lay = vbox(top_section, margins=(0, 0, 0, 0), spacing=6)
        self._task_top_layout = top_lay

        header = QWidget()
        header_lay = hbox(header, margins=(0, 0, 0, 8), spacing=16)
        text_col = QWidget()
        text_lay = vbox(text_col, spacing=2)
        text_lay.addWidget(title(f"Task {self.slot_id}", "CardTitle"))
        self.subtitle = elide_label("Independent authenticated Test Mode browser slot", "Caption")
        self.subtitle.setObjectName("TaskSubtitle")
        text_lay.addWidget(self.subtitle)
        header_lay.addWidget(text_col, 1)

        # Group 1: automation controls.
        control_group = QWidget()
        control_lay = hbox(control_group, margins=(0, 0, 0, 0), spacing=4)
        self.start_btn = button("Start", "primary")
        self.start_btn.setObjectName("TaskStartButton")
        self.start_btn.setFixedHeight(26)
        self.start_btn.clicked.connect(self.start)
        self.pause_btn = button("Pause", "secondary")
        self.pause_btn.setObjectName("TaskPauseButton")
        self.pause_btn.setFixedHeight(26)
        self.pause_btn.clicked.connect(self.pause)
        # Resume remains present because it is an existing v1.0.6 feature.
        self.resume_btn = button("Resume", "secondary")
        self.resume_btn.setObjectName("TaskResumeButton")
        self.resume_btn.setFixedHeight(26)
        self.resume_btn.clicked.connect(self.resume)
        self.stop_btn = button("Stop", "danger")
        self.stop_btn.setObjectName("TaskStopButton")
        self.stop_btn.setFixedHeight(26)
        self.stop_btn.clicked.connect(self.stop)
        for control in (self.start_btn, self.pause_btn, self.resume_btn, self.stop_btn):
            control_lay.addWidget(control)
        header_lay.addWidget(control_group)

        separator_one = QFrame()
        separator_one.setObjectName("TaskToolbarSeparator")
        separator_one.setFixedSize(1, 22)
        header_lay.addWidget(separator_one)

        # Group 2: non-clickable browser status pill with an 8px state dot.
        browser_status_pill = QFrame()
        browser_status_pill.setObjectName("TaskBrowserStatusPill")
        browser_status_lay = hbox(browser_status_pill, margins=(0, 0, 0, 0), spacing=6)
        self.browser_status_dot = QFrame()
        self.browser_status_dot.setObjectName("TaskBrowserStatusDot")
        self.browser_status_dot.setFixedSize(8, 8)
        self.browser_status_dot.setProperty("browserState", "closed")
        self.browser_status = QLabel("Browser: Closed")
        self.browser_status.setObjectName("TaskBrowserStatusText")
        self.browser_status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        browser_status_lay.addWidget(self.browser_status_dot)
        browser_status_lay.addWidget(self.browser_status)
        header_lay.addWidget(browser_status_pill)

        separator_two = QFrame()
        separator_two.setObjectName("TaskToolbarSeparator")
        separator_two.setFixedSize(1, 22)
        header_lay.addWidget(separator_two)

        # Group 3: browser/window actions.
        action_group = QWidget()
        action_lay = hbox(action_group, margins=(0, 0, 0, 0), spacing=6)
        self.browser_action_button = button("Open Browser", "primary")
        self.browser_action_button.setObjectName("TaskOpenBrowserButton")
        self.browser_action_button.setFixedHeight(26)
        self.browser_action_button.clicked.connect(self.browser_action)
        action_lay.addWidget(self.browser_action_button)
        downloads_btn = button("Downloads", "secondary", "folder")
        downloads_btn.setObjectName("TaskDownloadsButton")
        downloads_btn.setFixedHeight(26)
        downloads_btn.clicked.connect(self.open_downloads_folder)
        action_lay.addWidget(downloads_btn)
        close_btn = button("Close Task", "danger")
        close_btn.setObjectName("TaskCloseButton")
        close_btn.setFixedHeight(26)
        close_btn.clicked.connect(self.close)
        action_lay.addWidget(close_btn)
        header_lay.addWidget(action_group)
        top_lay.addWidget(header)

        # Existing progress feature is preserved inside the top section so it
        # does not create a fourth visual row or break the 14px row spacing.
        self.progress = QProgressBar()
        self.progress.setObjectName("TaskProgress")
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setAccessibleName(f"Task {self.slot_id} progress")
        progress_holder = QWidget()
        progress_lay = vbox(progress_holder, margins=(0, 0, 0, 0), spacing=0)
        progress_lay.addWidget(self.progress)
        self._task_separator_layout = progress_lay
        top_lay.addWidget(progress_holder)
        root.addWidget(top_section)

        # Row 2: fixed-pixel compact Target URL + upload/data status.
        target_row = QWidget()
        target_lay = hbox(target_row, margins=(0, 0, 0, 0), spacing=8)
        self._task_target_layout = target_lay
        target_label = label("Target URL", "FormLabel", False)
        target_label.setFixedWidth(72)
        target_lay.addWidget(target_label)

        self.url = line_input("https://…", self.state.target_url)
        self.url.setObjectName("TaskUrlInput")
        self.url.setMinimumHeight(28)
        self.url.setMaximumHeight(28)
        self.url.editingFinished.connect(self.app.schedule_workspace_save)
        target_lay.addWidget(self.url, 3)

        data_cluster = QWidget()
        data_lay = hbox(data_cluster, margins=(0, 0, 0, 0), spacing=8)
        load_btn = button("Upload Email/Data", "secondary", "open")
        load_btn.setObjectName("TaskUploadButton")
        load_btn.setMinimumHeight(28)
        load_btn.setMaximumHeight(28)
        self._task_upload_button = load_btn
        load_btn.clicked.connect(self.load_data)
        data_lay.addWidget(load_btn, 2)
        self.path_label = elide_label("No data", "TaskDataBadge")
        self.path_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.path_label.setMinimumHeight(22)
        self.path_label.setMaximumHeight(22)
        data_lay.addWidget(self.path_label, 1)
        target_lay.addWidget(data_cluster, 1)
        root.addWidget(target_row)

        # Row 3: one-line, seven-column compact metrics strip.
        metrics = QWidget()
        grid = QGridLayout(metrics)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(0)
        self._task_metrics_grid = grid
        self.metric_labels: dict[str, QLabel] = {}
        names = ["Status", "Login", "Send Limit", "Total", "Success", "Failed", "Remaining"]
        defaults = [
            "Ready",
            "Not Verified",
            f"0/{safe_test_send_limit(self.app.settings.get('max_test_send_limit', DEFAULT_TEST_SEND_LIMIT))}",
            "0", "0", "0", "0",
        ]
        for i, (name, value) in enumerate(zip(names, defaults)):
            metric = QFrame()
            metric.setObjectName("TaskMetric")
            metric.setFixedHeight(32)
            metric.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            metric_lay = vbox(metric, margins=(8, 2, 8, 2), spacing=0)
            self._task_metric_layouts.append(metric_lay)
            visible_metric_name = "Send Attempts / Limit" if name == "Send Limit" else name
            metric_lay.addWidget(elide_label(visible_metric_name, "TaskMetricLabel"))
            value_object = (
                "TaskMetricValueSuccess" if name == "Success"
                else "TaskMetricValueFailed" if name == "Failed"
                else "TaskMetricValue"
            )
            value_label = elide_label(value, value_object)
            self.metric_labels[name] = value_label
            metric_lay.addWidget(value_label)
            grid.addWidget(metric, 0, i)
            grid.setColumnStretch(i, 1)
        root.addWidget(metrics)

    def _task_viewport_dimensions(self) -> tuple[int, int]:
        """Return the current Tasks viewport size for resize invalidation only."""
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                viewport = parent.viewport()
                return max(1, viewport.width()), max(1, viewport.height())
            parent = parent.parentWidget()

        window = self.window()
        return max(1, window.width()), max(1, window.height())

    def _apply_task_spacing_contract(self) -> None:
        """Apply the fixed-pixel compact Tasks-page spacing contract."""
        if self._task_root_layout is None:
            return

        # Viewport dimensions only invalidate the cached application of this
        # fixed-pixel contract. They never scale padding, gaps, heights or fonts.
        viewport_width, viewport_height = self._task_viewport_dimensions()
        signature = (viewport_width, viewport_height, 12, 12, 8, 4, 2, 8, 28, 0, 0)
        if signature == self._task_spacing_signature:
            return
        self._task_spacing_signature = signature

        # Content-driven height replaces the previous 35% viewport minimum.
        self.setMinimumHeight(0)
        self._task_root_layout.setContentsMargins(12, 12, 12, 12)
        self._task_root_layout.setSpacing(8)

        if self._task_separator_layout is not None:
            self._task_separator_layout.setContentsMargins(0, 0, 0, 0)

        if self._task_target_layout is not None:
            self._task_target_layout.setContentsMargins(0, 0, 0, 0)

        if self._task_metrics_grid is not None:
            self._task_metrics_grid.setHorizontalSpacing(4)

        for metric_lay in self._task_metric_layouts:
            metric_lay.setContentsMargins(8, 2, 8, 2)

        if self._task_upload_button is not None:
            self._task_upload_button.setFixedHeight(28)
        self.url.setFixedHeight(28)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_task_spacing_contract()

    def _set_metric(self, name: str, value: Any) -> None:
        w = self.metric_labels.get(name)
        if w:
            w.setText(str(value))
            w.setToolTip(str(value))

    def _render_browser_status(self, status: str) -> None:
        """Render one deterministic browser lifecycle state and matching action."""
        normalized = str(status).strip().title()
        if normalized not in {"Closed", "Opening", "Open", "Closing"}:
            normalized = "Closed"
        self.browser_lifecycle_state = normalized
        self.browser_status.setText(f"Browser: {normalized}")
        state = "open" if normalized == "Open" else "closed" if normalized == "Closed" else "neutral"
        self.browser_status_dot.setProperty("browserState", state)
        style = self.browser_status_dot.style()
        style.unpolish(self.browser_status_dot)
        style.polish(self.browser_status_dot)
        self.browser_status_dot.update()

        action = self.browser_action_button
        if action is not None:
            if normalized == "Closed":
                action.setText("Open Browser")
                action.setEnabled(True)
            elif normalized == "Open":
                action.setText("Close Browser")
                action.setEnabled(True)
            elif normalized == "Opening":
                action.setText("Opening...")
                action.setEnabled(False)
            else:
                action.setText("Closing...")
                action.setEnabled(False)

    def browser_action(self) -> None:
        """Execute the single browser action that matches the visible lifecycle state."""
        if self.browser_lifecycle_state == "Closed":
            self.open_browser()
            return
        if self.browser_lifecycle_state != "Open":
            return
        if self.worker and self.worker.is_processing():
            if not _confirm(
                self,
                "Close browser",
                "This task is running. Closing its browser will stop processing and preserve the current recovery/unprocessed state. Close browser?",
            ):
                return
        self.close_browser(wait=False)
        self.app.update_dashboard()

    def open_downloads_folder(self) -> None:
        """Open this Task's effective durable download directory."""
        try:
            directory = ensure_task_download_directory(
                self.app.settings.data, self.slot_id, APP_DATA_DIR
            )
        except Exception as exc:
            _message(
                self,
                "Downloads",
                f"The Task download directory could not be prepared: {exc}",
                "error",
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            _message(
                self,
                "Downloads",
                "The Task download directory could not be opened in the system file manager.",
                "warning",
            )

    def open_browser(self) -> None:
        url = self.url.text().strip()
        if not url.startswith(("http://", "https://")):
            _message(self, "Invalid URL", "Please enter a valid http/https Target URL before opening the browser.", "warning")
            return
        if self.worker and self.worker.is_alive():
            self.worker.request_focus()
            self.app.log_ui(f"Task {self.slot_id}: browser focus requested")
            return
        allowed, reason = self.app.can_open_task_browser(self)
        if not allowed:
            _message(self, "Browser launch blocked", reason, "warning")
            return

        self.stop_event.clear()
        self.pause_event.clear()
        self._render_browser_status("Opening")
        self._set_metric("Login", "Not Verified")
        self._set_metric("Status", "Opening Browser")
        self.worker = AutomationWorker(
            self.state,
            dict(self.app.settings.data),
            self.app.ui_queue,
            self.stop_event,
            self.pause_event,
            initial_url=url,
            runtime_store=self.app.runtime_store,
            active_workflow_id=self.app.active_workflow_id,
        )
        self.worker.start()
        self.app.log_ui(f"Task {self.slot_id}: opening browser session")

    def load_data(self) -> None:
        if self.worker and self.worker.is_processing():
            _message(self, "Task running", "Stop the running task before loading new data.", "warning")
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select TXT/CSV data",
            "",
            "Data files (*.txt *.csv *.xlsx *.xls);;All files (*.*)",
        )
        if not filename:
            return
        try:
            path = Path(filename)
            audit = parse_data_with_audit(
                path,
                remove_duplicates=bool(
                    self.app.settings.get(
                        "remove_duplicate_rows", DEFAULT_SETTINGS["remove_duplicate_rows"]
                    )
                ),
            )
            items = audit.items
            self.state.items = items
            self.state.current_index = 0
            self.state.success_count = 0
            self.state.failed_count = 0
            self.state.manual_review_required = False
            self.state.send_limit_used = 0
            self.state.source_file = str(path)
            self.state.source_fingerprint = audit.source_fingerprint
            self.state.status = (
                "Login Verified"
                if self.is_login_verified()
                else ("Login Required" if self.is_browser_open() else "Ready")
            )
            self.state.created_at = now_str()
            self.state.run_id = self.app.runtime_store.start_run(
                slot_id=self.slot_id,
                target_url=self.url.text().strip(),
                source_file=str(path),
                source_fingerprint=audit.source_fingerprint,
                items=items,
                created_at=self.state.created_at,
            )
            self.loaded_path = path
            self.import_audit = audit
            self.path_label.setText(f"Loaded ({audit.accepted_rows})")
            reconciliation = (
                f"{path.name} • Source {audit.source_rows} • Valid {audit.valid_rows} • "
                f"Invalid {audit.invalid_rows} • Duplicate rows {audit.duplicate_rows} • "
                f"Accepted {audit.accepted_rows}"
            )
            self.path_label.setToolTip(reconciliation)
            self._set_metric("Status", self.state.status)
            self.update_counts()
            self.app.log_ui(f"Task {self.slot_id}: {reconciliation}")
            self.app.schedule_workspace_save()
        except Exception as exc:
            logging.exception("Data load failed")
            _message(self, "Data load failed", str(exc), "error")

    def restore_runtime(
        self, run: dict[str, Any], *, preserve_task_status: bool = False
    ) -> None:
        """Restore persisted task state only; browser/login/Send never auto-start."""
        self.state.run_id = str(run.get("run_id", ""))
        self.state.target_url = str(run.get("target_url", ""))
        self.state.source_file = str(run.get("source_file", ""))
        self.state.source_fingerprint = str(run.get("source_fingerprint", ""))
        self.state.current_index = max(0, int(run.get("current_index", 0)))
        self.state.success_count = max(0, int(run.get("success_count", 0)))
        self.state.failed_count = max(0, int(run.get("failed_count", 0)))
        self.state.manual_review_required = bool(run.get("manual_review_required", 0))
        self.state.send_limit_used = max(0, int(run.get("send_limit_used", 0)))
        self.state.created_at = str(run.get("created_at", now_str()))
        self.state.items = [
            TaskItem(
                email=str(row.get("email", "")),
                name=str(row.get("name", "")),
                status=str(row.get("status", "pending")),
                attempts=int(row.get("attempts", 0)),
                message=str(row.get("message", "")),
                result=str(row.get("result", "")),
            )
            for row in run.get("items", [])
        ]
        if self.state.manual_review_required:
            self.state.status = "Manual Review Required"
        elif preserve_task_status:
            prior_status = str(run.get("task_status", "Ready")).strip() or "Ready"
            if prior_status in {
                "Running", "Paused", "Starting", "Login Verified", "Login Required",
                "Opening Browser", "Closing",
            }:
                prior_status = "Stopped" if self.state.items else "Ready"
            self.state.status = prior_status
        else:
            self.state.status = "Recovered"
        if self.state.target_url:
            self.url.setText(self.state.target_url)
        source = Path(self.state.source_file) if self.state.source_file else None
        self.loaded_path = source if source and source.exists() else None
        self.path_label.setText(f"Recovered ({self.state.total})")
        self.path_label.setToolTip(
            f"Recovered run {self.state.run_id} • Next index {self.state.current_index} • "
            f"Source {self.state.source_file or 'stored runtime data'}"
        )
        self._set_metric("Status", self.state.status)
        limit = safe_test_send_limit(
            self.app.settings.get("max_test_send_limit", DEFAULT_SETTINGS["max_test_send_limit"])
        )
        self._set_metric("Send Limit", f"{self.state.send_limit_used}/{limit}")
        self.update_counts()

    def start(self) -> None:
        if self.state.manual_review_required:
            if not self.app.resolve_manual_review(self):
                return
        if self.worker and self.worker.is_processing():
            _message(self, "Already running", "This task is already processing.")
            return
        if not self.state.items:
            _message(self, "No data", "Please upload a TXT/CSV/XLSX file first.", "warning")
            return
        url = self.url.text().strip()
        if not url.startswith(("http://", "https://")):
            _message(self, "Invalid URL", "Please enter a valid http/https Target URL.", "warning")
            return
        if not bool(self.app.settings.get("authorized_testing_only", DEFAULT_SETTINGS["authorized_testing_only"])):
            _message(self, "Authorization required", "Enable authorized testing mode in App Settings before running automation.", "warning")
            return
        if not self.worker or not self.worker.is_alive() or not self.worker.is_browser_ready():
            _message(
                self,
                "Browser not ready",
                "Click Open Browser first, complete account login, and keep the Target URL open.",
                "warning",
            )
            return
        if not self.worker.is_login_verified():
            self.worker.request_focus()
            _message(
                self,
                "Login not verified",
                "Complete login in the opened browser and open the Target URL in Test Mode. "
                "Wait until this task shows Login Verified, then click Start.",
                "warning",
            )
            return
        try:
            max_limit = validate_test_send_limit(
                self.app.settings.get("max_test_send_limit", DEFAULT_SETTINGS["max_test_send_limit"])
            )
        except (TypeError, ValueError) as exc:
            _message(self, "Invalid send limit", str(exc), "warning")
            return
        if max_limit == 0:
            _message(
                self,
                "Sending disabled",
                "Max Test Send Limit is set to 0. Increase it in App Settings before starting automation.",
                "warning",
            )
            self._set_metric("Send Limit", "0/0")
            return
        self._set_metric("Send Limit", f"{self.state.send_limit_used}/{max_limit}")
        self.state.target_url = url
        self.stop_event.clear()
        self.pause_event.clear()
        self.worker.request_start(dict(self.app.settings.data), url)
        self._set_metric("Status", "Starting")
        self.app.log_ui(f"Task {self.slot_id}: Share invite workflow started")

    def stop(self) -> None:
        if not self.worker or not self.worker.is_processing():
            self._set_metric(
                "Status",
                "Login Verified"
                if self.is_login_verified()
                else ("Login Required" if self.is_browser_open() else "Ready"),
            )
            return
        self.stop_event.set()
        self.pause_event.clear()
        self._set_metric("Status", "Stopping")
        self.app.log_ui(f"Task {self.slot_id}: stop requested")

    def pause(self) -> None:
        if not self.worker or not self.worker.is_processing():
            _message(self, "Not running", "Start the task before using Pause.")
            return
        self.pause_event.set()
        self._set_metric("Status", "Paused")
        self.app.log_ui(f"Task {self.slot_id}: paused")

    def resume(self) -> None:
        if not self.worker or not self.worker.is_processing():
            _message(self, "Not paused", "There is no active task to resume.")
            return
        self.pause_event.clear()
        self._set_metric("Status", "Running")
        self.app.log_ui(f"Task {self.slot_id}: resumed")

    def close_browser(self, wait: bool = True) -> bool:
        worker = self.worker
        if not worker:
            self._render_browser_status("Closed")
            self._set_metric("Login", "Not Verified")
            return True
        self._render_browser_status("Closing")
        self._set_metric("Login", "Not Verified")
        worker.request_close()
        self._set_metric("Status", "Closing")
        if wait and worker.is_alive():
            if not worker.stopped_event.wait(timeout=8.0):
                self._set_metric("Status", "Closing / Worker Busy")
                self.app.log_ui(
                    f"Task {self.slot_id}: worker did not finish cleanup within 8 seconds; "
                    "the live worker reference was retained.",
                    "WARNING",
                )
                return False
            worker.join(timeout=1.0)
        if worker.is_alive():
            return False
        self.worker = None
        self._render_browser_status("Closed")
        self._set_metric("Login", "Not Verified")
        return True

    def _persist_closed_task(self) -> None:
        """Archive the current Task snapshot before removing its widget."""
        timestamp = now_str()
        self.state.target_url = self.url.text().strip()
        if not self.state.created_at:
            self.state.created_at = timestamp
        if not self.state.run_id:
            self.state.run_id = self.app.runtime_store.start_run(
                slot_id=self.slot_id,
                target_url=self.state.target_url,
                source_file=self.state.source_file,
                source_fingerprint=self.state.source_fingerprint,
                items=self.state.items,
                created_at=self.state.created_at,
            )
        self.app.runtime_store.close_run(
            run_id=self.state.run_id,
            task_status=self.state.status,
            timestamp=timestamp,
            current_index=self.state.current_index,
            total=self.state.total,
            success_count=self.state.success_count,
            failed_count=self.state.failed_count,
            send_limit_used=self.state.send_limit_used,
            manual_review_required=self.state.manual_review_required,
            target_url=self.state.target_url,
            items=self.state.items,
        )

    def close(self) -> None:
        if self.worker and self.worker.is_processing():
            if not _confirm(
                self,
                "Close task",
                "Task is running. Stop it, save unprocessed data, and close its browser session?",
            ):
                return
        if not self.close_browser(wait=True):
            _message(
                self,
                "Worker still closing",
                "The browser worker is still completing cleanup. The task was kept open; try again after it closes.",
                "warning",
            )
            return
        try:
            self._persist_closed_task()
        except Exception as exc:
            logging.exception("Closed Task persistence failed")
            _message(
                self,
                "Close task failed",
                f"The Task could not be saved for later reopening and was kept visible. Detail: {exc}",
                "error",
            )
            return
        self.app.remove_task(self.slot_id)
        self.setParent(None)
        self.deleteLater()

    def _finalize_closed_browser_state(self) -> None:
        """Release a stopped worker only after its thread has actually exited."""
        if self.browser_lifecycle_state != "Closing":
            return
        worker = self.worker
        if worker is not None and worker.is_alive():
            QTimer.singleShot(100, self._finalize_closed_browser_state)
            return
        self.worker = None
        self._render_browser_status("Closed")
        self._set_metric("Login", "Not Verified")
        if not self.is_running() and self.state.status not in {
            "Completed", "Failed", "Stopped", "Test Send Limit Reached", "Login/Test Mode Required"
        }:
            self._set_metric("Status", "Ready")
        self.app.update_dashboard()

    def set_browser_status(self, status: str) -> None:
        normalized = str(status).strip().title()
        if normalized == "Closed" and self.worker and self.worker.is_alive():
            # The visible browser is already unavailable, but keep the Task action
            # disabled until the worker finishes its deterministic cleanup.
            self._render_browser_status("Closing")
            self._set_metric("Login", "Not Verified")
            if not self.is_running():
                self._set_metric("Status", "Closing")
            QTimer.singleShot(100, self._finalize_closed_browser_state)
            return

        self._render_browser_status(normalized)
        if normalized == "Closed" and self.worker and not self.worker.is_alive():
            self.worker = None
        if normalized == "Open" and not self.is_running():
            self._set_metric("Status", "Login Verified" if self.is_login_verified() else "Login Required")
        elif normalized == "Opening" and not self.is_running():
            self._set_metric("Login", "Not Verified")
            self._set_metric("Status", "Opening Browser")
        elif normalized == "Closing" and not self.is_running():
            self._set_metric("Login", "Not Verified")
            self._set_metric("Status", "Closing")
        elif normalized == "Closed" and not self.is_running() and self.state.status not in {
            "Completed", "Failed", "Stopped", "Test Send Limit Reached", "Login/Test Mode Required"
        }:
            self._set_metric("Login", "Not Verified")
            self._set_metric("Status", "Ready")

    def set_login_status(self, verified: bool, message: str = "") -> None:
        self._set_metric("Login", "Verified" if verified else "Not Verified")
        if not self.is_running():
            if not verified and self.browser_lifecycle_state == "Closing":
                self._set_metric("Status", "Closing")
            elif not verified and self.browser_lifecycle_state == "Closed":
                self._set_metric("Status", "Ready")
            elif not verified and self.browser_lifecycle_state == "Opening":
                self._set_metric("Status", "Opening Browser")
            else:
                self._set_metric("Status", "Login Verified" if verified else "Login Required")
        if message:
            self.app.log_ui(
                f"Task {self.slot_id}: {message}",
                "INFO" if verified else "WARNING",
            )

    def update_send_limit(self, used: int, limit: int) -> None:
        self._set_metric("Send Limit", f"{max(0, int(used))}/{max(0, int(limit))}")

    def update_counts(self, data: dict[str, Any] | None = None) -> None:
        if data:
            progress = float(data.get("progress", 0.0))
            self.progress.setValue(max(0, min(1000, int(progress * 1000))))
            self._set_metric("Total", data.get("total", self.state.total))
            self._set_metric("Success", data.get("success", self.state.success_count))
            self._set_metric("Failed", data.get("failed", self.state.failed_count))
            self._set_metric("Remaining", data.get("remaining", self.state.remaining))
        else:
            self.progress.setValue(max(0, min(1000, int(self.state.progress * 1000))))
            self._set_metric("Total", self.state.total)
            self._set_metric("Success", self.state.success_count)
            self._set_metric("Failed", self.state.failed_count)
            self._set_metric("Remaining", self.state.remaining)

    def set_status(self, status: str) -> None:
        self.state.status = status
        self._set_metric("Status", status)

    def is_browser_open(self) -> bool:
        return bool(
            self.browser_lifecycle_state == "Open"
            and self.worker
            and self.worker.is_alive()
            and self.worker.is_browser_ready()
        )

    def is_login_verified(self) -> bool:
        return bool(self.worker and self.worker.is_alive() and self.worker.is_login_verified())

    def is_running(self) -> bool:
        return bool(self.worker and self.worker.is_processing())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        self.settings = SettingsManager(SETTINGS_FILE)
        super().__init__()
        self.workflow_catalog = WorkflowManager.with_builtin_workflows()
        self.workflow_state_store = WorkflowStateStore(
            APP_DATA_DIR / "workflow_state.json", manager=self.workflow_catalog
        )
        self.workflow_switch_root = APP_DATA_DIR / "WorkflowSwitch"
        self.workflow_state_error = ""
        self.active_workflow_id: str | None = None
        self._workflow_recovery_actions: list[str] = []
        self._workflow_switch_in_progress = False
        self._workflow_restart_required = False
        try:
            self._workflow_recovery_actions = WorkflowSwitchTransaction.recover_all(
                data_root=APP_DATA_DIR,
                transaction_root=self.workflow_switch_root,
                state_store=self.workflow_state_store,
            )
            if self._workflow_recovery_actions:
                # A PREPARED recovery may have restored settings.json after the
                # first SettingsManager read. Re-read it before constructing any
                # subsystem that consumes settings.
                self.settings = SettingsManager(SETTINGS_FILE)
            workflow_state = self.workflow_state_store.load_or_migrate()
            self.active_workflow_id = workflow_state.active_workflow_id
        except (WorkflowStateError, WorkflowSwitchError) as exc:
            self.workflow_state_error = str(exc)

        self.license_manager = LicenseManager(self.settings)
        self.runtime_store = TaskRuntimeStore(TASK_RUNTIME_DB)
        self.workspace_store = WorkspaceStateStore(APP_STATE_FILE)
        self.ui_queue: queue.Queue = queue.Queue(maxsize=UI_QUEUE_CAPACITY)
        self.tasks: dict[int, TaskSlotWidget] = {}
        self.next_slot_id = 1
        self._selected_page_name = "Dashboard"
        self._workspace_restore_in_progress = False
        self._workspace_restored_run_ids: set[str] = set()
        self.report_rows: list[dict[str, Any]] = self.runtime_store.results(limit=REPORT_RECENT_LIMIT)
        self._report_dirty = False
        self.log_lines: list[dict[str, str]] = []
        self.license_stop = threading.Event()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.pages: dict[str, int] = {}
        self.setting_widgets: dict[str, QWidget] = {}
        self.workflow_input_widgets: dict[str, QWidget] = {}
        self.browser_setting_widgets: dict[str, QWidget] = {}
        self._workspace_active = False
        self._workspace_transitioning = False
        self.activation_page: ActivationPage | None = None
        self._pending_license_invalid_message: str | None = None
        self.breadcrumb = None
        self.window_title_label = None
        self.license_badge = None
        self.responsive_badge = None
        self.dashboard_metrics: dict[str, QLabel] = {}
        self.dashboard_details: dict[str, QLabel] = {}
        self.dashboard_next_message: QLabel | None = None
        self.dashboard_next_button: QPushButton | None = None
        self.dashboard_next_action: tuple[str, int | None] = ("tasks", None)
        self.task_layout = None

        self.setWindowTitle(f"{DISPLAY_APP_NAME} — {APP.company_name}")
        self.setWindowIcon(application_icon())
        self.setMinimumSize(CONST.min_window_width, CONST.min_window_height)
        self.resize(CONST.default_window_width, CONST.default_window_height)
        self.setStyleSheet(app_qss("dark") + ActivationPage.activation_qss() + TaskSlotWidget.task_qss())
        install_keyboard_focus_ring(QApplication.instance())

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_queue)
        self.poll_timer.start(200)

        self.workspace_save_timer = QTimer(self)
        self.workspace_save_timer.setSingleShot(True)
        self.workspace_save_timer.setInterval(350)
        self.workspace_save_timer.timeout.connect(self.save_workspace_state)

        self.show_login_or_main()
        self.start_license_recheck()
        logging.info("Vib Tools UI edition started")

    # ---------- top-level shell ----------

    def show_login_or_main(self) -> None:
        if self.license_manager.is_activated():
            self.show_workspace()
            return

        self.show_login()
        # Phase-02 secure restore: an expired access token, rotated-session cache,
        # or legacy protected license cache must recover through the same API v2
        # validate/refresh/activate path without requiring the user to retype a
        # license that is already protected locally.  The locked ActivationPage
        # design is preserved; only its existing status/button controls are used.
        if self.license_manager.license_key:
            activation_page = self.activation_page
            if activation_page is not None:
                activation_page.activate_button.setEnabled(False)
                activation_page._set_status_state(
                    "pending", "Restoring secure license session…"
                )
            license_key = self.license_manager.license_key
            user_email = self.license_manager.user_email

            def restore_session() -> None:
                ok, msg = self.license_manager.validate(license_key, user_email)
                self.ui_queue.put(
                    (
                        "activation_result",
                        {"slot_id": 0, "ok": ok, "message": msg},
                    )
                )

            threading.Thread(target=restore_session, daemon=True).start()

    def show_login(self) -> None:
        self._workspace_active = False
        self._workspace_transitioning = False
        self.menuBar().clear()
        self.menuBar().hide()
        self.statusBar().clearMessage()
        self.statusBar().hide()
        self.nav_buttons.clear()
        self.pages.clear()

        # Drop Python references to widgets owned by the previous central widget.
        # Qt deletes those children when setCentralWidget() replaces the workspace;
        # retaining the wrappers caused resize/update callbacks to access deleted C++
        # objects during the next successful activation.
        self.breadcrumb = None
        self.window_title_label = None
        self.license_badge = None
        self.responsive_badge = None
        self.dashboard_metrics = {}
        self.dashboard_details = {}
        self.dashboard_next_message = None
        self.dashboard_next_button = None
        self.dashboard_next_action = ("tasks", None)
        self.task_layout = None

        # Scope-locked activation window: compact, fixed and centered.
        self.setFixedSize(460, 560)
        current = self.centralWidget()
        if isinstance(current, ActivationPage):
            self.activation_page = current
        else:
            self.activation_page = ActivationPage(self)
            self.setCentralWidget(self.activation_page)
        self._center_login_window()
        QTimer.singleShot(0, self._center_login_window)

    def _center_login_window(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def _fit_workspace_to_screen(self) -> None:
        """Resize and center the workspace fully inside the current screen."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.setMinimumSize(CONST.min_window_width, CONST.min_window_height)
            self.resize(CONST.default_window_width, CONST.default_window_height)
            return

        available = screen.availableGeometry()
        target_width = max(1, min(CONST.default_window_width, available.width()))
        target_height = max(1, min(CONST.default_window_height, available.height()))
        self.setMinimumSize(0, 0)
        self.resize(target_width, target_height)

        # Account for the native frame/title-bar size after the client resize so
        # the complete top-level window remains inside availableGeometry().
        frame = self.frameGeometry()
        excess_width = max(0, frame.width() - available.width())
        excess_height = max(0, frame.height() - available.height())
        if excess_width or excess_height:
            self.resize(
                max(1, self.width() - excess_width),
                max(1, self.height() - excess_height),
            )
            frame = self.frameGeometry()

        minimum_width = min(CONST.min_window_width, self.width())
        minimum_height = min(CONST.min_window_height, self.height())
        self.setMinimumSize(minimum_width, minimum_height)

        frame.moveCenter(available.center())
        left = max(available.left(), min(frame.left(), available.right() - frame.width() + 1))
        top = max(available.top(), min(frame.top(), available.bottom() - frame.height() + 1))
        self.move(left, top)

    def schedule_workspace_save(self) -> None:
        """Debounce workspace metadata persistence while the live shell is active."""
        if (
            not self._workspace_active
            or self._workspace_transitioning
            or self._workspace_restore_in_progress
            or self._workflow_switch_in_progress
        ):
            return
        self.workspace_save_timer.start()

    def _workspace_snapshot(self) -> dict[str, Any]:
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        active_tasks = [
            {
                "slot_id": int(task.slot_id),
                "run_id": str(task.state.run_id or ""),
                "target_url": task.url.text().strip(),
            }
            for task in self.tasks.values()
        ]
        return {
            "saved_at": now_str(),
            "active_tasks": active_tasks,
            "next_slot_id": max(1, int(self.next_slot_id)),
            "selected_page": self._selected_page_name,
            "window": {
                "x": int(geometry.x()),
                "y": int(geometry.y()),
                "width": max(1, int(geometry.width())),
                "height": max(1, int(geometry.height())),
                "maximized": bool(self.isMaximized()),
            },
        }

    def save_workspace_state(self) -> bool:
        """Persist lightweight active-workspace metadata without duplicating Task data."""
        if (
            not self._workspace_active
            or self._workspace_restore_in_progress
            or self._workflow_switch_in_progress
        ):
            return False
        if self.workspace_save_timer.isActive():
            self.workspace_save_timer.stop()
        try:
            self.workspace_store.save(self._workspace_snapshot())
            return True
        except Exception as exc:
            logging.exception("Workspace state save failed")
            self.log_ui(f"Workspace state could not be saved: {exc}", "ERROR")
            return False

    def _restore_workspace_geometry(self, value: dict[str, Any] | None) -> None:
        """Restore saved workspace geometry, clamped to currently available screens."""
        if not isinstance(value, dict):
            self._fit_workspace_to_screen()
            return
        try:
            x = int(value.get("x", 0))
            y = int(value.get("y", 0))
            width = max(1, int(value.get("width", CONST.default_window_width)))
            height = max(1, int(value.get("height", CONST.default_window_height)))
        except (TypeError, ValueError):
            self._fit_workspace_to_screen()
            return
        maximized = bool(value.get("maximized", False))
        screens = list(QApplication.screens())
        if not screens:
            self._fit_workspace_to_screen()
            return

        def overlap_area(screen) -> int:
            available = screen.availableGeometry()
            left = max(x, available.left())
            top = max(y, available.top())
            right = min(x + width - 1, available.right())
            bottom = min(y + height - 1, available.bottom())
            return max(0, right - left + 1) * max(0, bottom - top + 1)

        screen = max(screens, key=overlap_area)
        if overlap_area(screen) <= 0:
            screen = self.screen() or QApplication.primaryScreen() or screens[0]
        available = screen.availableGeometry()

        self.showNormal()
        self.setMinimumSize(0, 0)
        self.resize(min(width, available.width()), min(height, available.height()))
        frame = self.frameGeometry()
        left = max(available.left(), min(x, available.right() - frame.width() + 1))
        top = max(available.top(), min(y, available.bottom() - frame.height() + 1))
        self.move(left, top)
        self.setMinimumSize(
            min(CONST.min_window_width, self.width()),
            min(CONST.min_window_height, self.height()),
        )
        if maximized:
            QTimer.singleShot(0, self.showMaximized)

    def _restore_active_workspace_tasks(self, state: dict[str, Any]) -> None:
        """Restore active Task cards only; deliberately Closed Tasks remain archived."""
        self._workspace_restored_run_ids.clear()
        closed_run_ids = {
            str(row.get("run_id", ""))
            for row in self.runtime_store.closed_runs()
            if row.get("run_id")
        }
        for entry in state.get("active_tasks", []):
            try:
                slot_id = int(entry.get("slot_id", 0))
            except (TypeError, ValueError, AttributeError):
                continue
            if slot_id <= 0:
                continue
            run_id = str(entry.get("run_id", "") or "")
            target_url = str(entry.get("target_url", "") or "")
            if run_id and run_id in closed_run_ids:
                self.log_ui(
                    f"Task {slot_id}: workspace restore skipped because it is deliberately Closed."
                )
                continue
            slot = self._add_task_with_id(slot_id)
            if slot is None:
                continue
            if run_id:
                run = self.runtime_store.load_run(run_id)
                if run is not None:
                    slot.restore_runtime(run, preserve_task_status=True)
                    self._workspace_restored_run_ids.add(run_id)
                else:
                    self.log_ui(
                        f"Task {slot_id}: saved run {run_id} was unavailable; restored the Task shell only.",
                        "WARNING",
                    )
            if target_url:
                slot.url.setText(target_url)
                slot.state.target_url = target_url
            slot._render_browser_status("Closed")
            slot._set_metric("Login", "Not Verified")

        try:
            saved_next = max(1, int(state.get("next_slot_id", 1)))
        except (TypeError, ValueError):
            saved_next = 1
        self.next_slot_id = max(self.next_slot_id, saved_next)

    def show_workspace(self) -> None:
        # A successful activation may only enter the workspace once. Repeated queued
        # callbacks are ignored instead of rebuilding/deleting the same Qt widgets.
        if self._workspace_active or self._workspace_transitioning:
            return

        self._workspace_transitioning = True
        self._workspace_restore_in_progress = True
        try:
            # setFixedSize() locked both minimum and maximum dimensions on the login
            # screen. Unlock without forcing the large workspace minimum first; the
            # old ordering emitted resizeEvent while stale workspace wrappers could
            # still exist. Build the live shell before applying workspace geometry.
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.menuBar().show()
            self.statusBar().show()
            self._build_menu_bar()
            self._build_shell()
            self.activation_page = None
            self._build_status_bar()

            workspace_state = self.workspace_store.load()
            if workspace_state is None:
                self._fit_workspace_to_screen()
            else:
                self._restore_workspace_geometry(workspace_state.get("window"))
                if not self.workflow_state_error and self.active_workflow_id:
                    self._restore_active_workspace_tasks(workspace_state)

            if (
                workspace_state is None
                and not self.tasks
                and not self.workflow_state_error
                and self.active_workflow_id
            ):
                initial_slots = max(1, int(self.settings.get(
                    "browser_slot_default", DEFAULT_SETTINGS["browser_slot_default"]
                )))
                for _ in range(initial_slots):
                    self.add_task()

            selected_page = (
                str(workspace_state.get("selected_page", "Dashboard"))
                if workspace_state is not None
                else "Dashboard"
            )
            if selected_page not in self.pages:
                selected_page = "Dashboard"
            self.navigate(selected_page)
            self._workspace_active = True
            self.log_ui("License validated. Main workspace loaded.")
            for action in self._workflow_recovery_actions:
                self.log_ui(f"Workflow switch recovery: {action}", "WARNING")
            self._workflow_recovery_actions.clear()
            if self.workflow_state_error:
                self.log_ui(
                    f"Workflow state is unavailable; automation is blocked: {self.workflow_state_error}",
                    "ERROR",
                )
                QTimer.singleShot(
                    0,
                    lambda: _message(
                        self,
                        "Workflow state blocked",
                        "VibraPilot cannot safely determine the active workflow. "
                        f"Automation is blocked until the workflow state is repaired.\n\n{self.workflow_state_error}",
                        "error",
                    ),
                )
            if self.workspace_store.warning:
                self.log_ui(self.workspace_store.warning, "WARNING")
                self.workspace_store.warning = ""
            if self.runtime_store.recovery_warning:
                self.log_ui(self.runtime_store.recovery_warning, "ERROR")
                self.runtime_store.recovery_warning = ""
            if not self.workflow_state_error and self.active_workflow_id:
                QTimer.singleShot(0, self.offer_task_recovery)
        finally:
            self._workspace_restore_in_progress = False
            self._workspace_transitioning = False
        self.schedule_workspace_save()

    def _build_menu_bar(self) -> None:
        self.menuBar().clear()
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Export Report CSV", self.export_report_csv, QKeySequence("Ctrl+Shift+C"))
        file_menu.addAction("Export Report Excel", self.export_report_excel, QKeySequence("Ctrl+Shift+E"))
        file_menu.addAction("Save Logs", self.save_logs, QKeySequence("Ctrl+S"))
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, QKeySequence("Alt+F4"))

        task_menu = self.menuBar().addMenu("Task")
        task_menu.addAction("Add Task", self.add_task, QKeySequence("Ctrl+N"))
        task_menu.addAction("Open Tasks", lambda: self.navigate("Tasks"), QKeySequence("Ctrl+1"))

        view_menu = self.menuBar().addMenu("View")
        for name in NAV_SECTIONS:
            shortcut = VIEW_NAV_SHORTCUTS.get(name)
            view_menu.addAction(
                name,
                lambda checked=False, n=name: self.navigate(n),
                QKeySequence(shortcut) if shortcut else QKeySequence(),
            )
        view_menu.addSeparator()
        locked = view_menu.addAction("Vib Tools Dark Theme — Locked")
        locked.setEnabled(False)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("About", lambda: self.navigate("About"))

    def _build_shell(self) -> None:
        central = QWidget()
        central.setObjectName("AppRoot")
        apply_accessibility(
            central,
            f"{DISPLAY_APP_NAME} {APP.company_name} desktop application",
            "Main application shell with sidebar navigation and native window controls.",
        )
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("WindowHeader")
        header_lay = hbox(header, margins=(12, 0, 12, 0), spacing=CONST.shell_header_gap)
        header_lay.addWidget(brand_icon_label(24, APP.display_name))
        self.window_title_label = elide_label(DISPLAY_APP_NAME, "WindowTitle")
        header_lay.addWidget(self.window_title_label)
        self.breadcrumb = elide_label("Home / Dashboard", "Breadcrumb")
        self.breadcrumb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_lay.addWidget(self.breadcrumb, 1)

        cluster = QWidget()
        cluster.setObjectName("HeaderActionCluster")
        cl = hbox(cluster, margins=(0, 0, 0, 0), spacing=CONST.shell_header_gap)
        self.license_badge = token_chip("Licensed")
        cl.addWidget(self.license_badge)
        self.responsive_badge = token_chip("Medium")
        cl.addWidget(self.responsive_badge)
        logout_btn = button("Logout", "ghost")
        logout_btn.clicked.connect(self.logout)
        cl.addWidget(logout_btn)
        header_lay.addWidget(cluster, 0, Qt.AlignRight | Qt.AlignVCenter)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = self._make_sidebar()
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("PageViewport")
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        self.setCentralWidget(central)

        self._register_pages()
        self._apply_responsive_mode()

    def _create_nav_button(self, section: str) -> QPushButton:
        btn = QPushButton(section)
        icon_name = {
            "Dashboard": "home",
            "Tasks": "refresh",
            "Workflow Inputs": "file",
            "Browser Settings": "search",
            "Reports": "file",
            "Live Logs": "info",
            "App Settings": "settings",
            "About": "help",
        }.get(section, "file")
        apply_nav_button_contract(btn, icon_obj=icon(icon_name))
        btn.clicked.connect(lambda _=False, name=section: self.navigate(name))
        self.nav_buttons[section] = btn
        return btn

    def _make_sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(CONST.sidebar_width)
        lay = vbox(
            side,
            margins=(CONST.sidebar_padding, CONST.sidebar_padding, CONST.sidebar_padding, CONST.sidebar_padding),
            spacing=4,
        )
        lay.addWidget(label(DISPLAY_APP_NAME, "SidebarTitle", False))
        lay.addWidget(label("Vib Tools • Authorized Test Mode", "Caption", False))

        nav_host = QWidget()
        nav_host.setObjectName("SidebarNavHost")
        nav_lay = vbox(nav_host, margins=(0, 4, 0, 2), spacing=2)
        for section in NAV_SECTIONS[:-1]:
            nav_lay.addWidget(self._create_nav_button(section))
        nav_lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("MinimalScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(nav_host)
        lay.addWidget(scroll, 1)
        lay.addWidget(divider())
        lay.addWidget(self._create_nav_button("About"))
        return side

    def _register_pages(self) -> None:
        for name, maker in (
            ("Dashboard", self.make_dashboard_page),
            ("Tasks", self.make_tasks_page),
            ("Workflow Inputs", self.make_workflow_inputs_page),
            ("Reports", self.make_reports_page),
            ("Live Logs", self.make_logs_page),
            ("App Settings", self.make_settings_page),
            ("Browser Settings", self.make_browser_settings_page),
            ("About", self.make_about_page),
        ):
            page = maker()
            self.pages[name] = self.stack.addWidget(page)

    def _build_status_bar(self) -> None:
        self.statusBar().setSizeGripEnabled(True)
        self.statusBar().addPermanentWidget(elide_label("● Ready", "StatusText"))
        self.statusBar().addPermanentWidget(elide_label("Vib Tools dark contract • Test Mode safety enforced", "StatusText"))
        self.statusBar().showMessage("Ready")

    def navigate(self, name: str) -> None:
        if name not in self.pages:
            return
        self._selected_page_name = name
        self.stack.setCurrentIndex(self.pages[name])
        self.breadcrumb.setText(f"Home / {name}")
        for section, btn in self.nav_buttons.items():
            btn.setChecked(section == name)
        # Tasks-page-only tooltip cleanup: suppress the inherited shell tooltip
        # while this page is active, then restore the frozen accessibility name
        # on every other page. Accessible name/description remain unchanged.
        central = self.centralWidget()
        if central is not None:
            central.setToolTip("" if name == "Tasks" else central.accessibleName())
        self.statusBar().showMessage(f"Viewing: {name}")
        if name == "Dashboard":
            self.update_dashboard()
        elif name == "Workflow Inputs":
            self.refresh_workflow_input_widgets()
        elif name == "Browser Settings":
            # Always render the current persisted SettingsManager values when the
            # advanced page is opened; this prevents stale UI if a value changed
            # through migration, reset, or another application code path.
            self.refresh_browser_settings_widgets()
        self.schedule_workspace_save()

    # ---------- pages ----------

    def _scroll_page(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("MinimalScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        return scroll

    def make_dashboard_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        root.addWidget(
            page_header(
                "Dashboard",
                "Live overview of browser slots, automation progress, license state and next actions.",
                [button("Add Task", "primary", "open")],
            )
        )
        add_action = root.itemAt(0).widget().findChildren(QPushButton)
        if add_action:
            def add_task_from_dashboard() -> None:
                self.add_task()
                self.navigate("Tasks")

            add_action[-1].clicked.connect(add_task_from_dashboard)

        content = QWidget()
        content.setObjectName("PageInner")
        content_lay = vbox(
            content,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.section_gap,
        )

        # Existing top-row metrics are intentionally preserved unchanged.
        self.dashboard_metrics = {}
        metrics_host = QWidget()
        grid = QGridLayout(metrics_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(CONST.content_gap)
        cards = [
            ("Browser Slots", "0", "Independent sessions"),
            ("Running", "0", "Active workflows"),
            ("Complete", "0", "Confirmed invites"),
            ("Failed", "0", "Failed records"),
        ]
        for i, (name, value, note) in enumerate(cards):
            m = metric_card(name, value, note)
            val = m.findChild(QLabel, "PageTitle")
            if val:
                self.dashboard_metrics[name] = val
            grid.addWidget(m, 0, i)
            grid.setColumnStretch(i, 1)
        content_lay.addWidget(metrics_host)

        self.dashboard_details = {}

        def summary_card(title_text: str, rows: list[tuple[str, str]]) -> QFrame:
            # Dashboard values are live runtime data, so use a normal QLabel rather
            # than an empty ElideLabel.  ElideLabel starts with an ignored horizontal
            # size hint; when its text is populated later, Qt can keep the label at
            # effectively zero width and render only the row name.
            panel = card(title_text)
            panel_layout = panel.layout()
            panel_layout.setContentsMargins(12, 10, 12, 10)
            panel_layout.setSpacing(6)
            for key, row_label in rows:
                row = QWidget()
                row.setMinimumHeight(22)
                row_layout = hbox(row, margins=(0, 0, 0, 0), spacing=10)
                row_layout.addWidget(elide_label(row_label, "Description"), 1)

                value = QLabel("")
                value.setObjectName("CardTitle")
                value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                value.setMinimumWidth(110)
                value.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                row_layout.addWidget(value, 0)
                panel_layout.addWidget(row)
                self.dashboard_details[key] = value
            return panel

        summary_host = QWidget()
        summary_grid = QGridLayout(summary_host)
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setHorizontalSpacing(CONST.content_gap)
        summary_grid.setVerticalSpacing(CONST.content_gap)

        readiness = summary_card(
            "Workspace Readiness",
            [
                ("Browsers Ready", "Browsers Ready"),
                ("Login Verified", "Login Verified"),
                ("Tasks with Data", "Tasks with Data"),
                ("Ready to Start", "Ready to Start"),
            ],
        )
        activity = summary_card(
            "Current Session Activity",
            [
                ("Processed", "Processed"),
                ("Successful", "Successful"),
                ("Session Failed", "Failed"),
                ("Remaining", "Remaining"),
            ],
        )
        license_summary = summary_card(
            "License Summary",
            [
                ("License Status", "License Status"),
                ("License Expires", "Expires"),
                ("Device Status", "Current Device"),
            ],
        )
        usage = summary_card(
            "Usage Summary",
            [
                ("Current Usage", "Current Usage"),
                ("Available", "Available"),
                ("Task Limit", "Task Limit"),
            ],
        )

        summary_grid.addWidget(readiness, 0, 0)
        summary_grid.addWidget(activity, 0, 1)
        summary_grid.addWidget(license_summary, 1, 0)
        summary_grid.addWidget(usage, 1, 1)
        summary_grid.setColumnStretch(0, 1)
        summary_grid.setColumnStretch(1, 1)
        content_lay.addWidget(summary_host)

        next_card = card("Next Step")
        next_layout = next_card.layout()
        next_layout.setContentsMargins(12, 10, 12, 10)
        next_layout.setSpacing(6)
        next_row = QWidget()
        next_row_layout = hbox(next_row, margins=(0, 0, 0, 0), spacing=CONST.content_gap)
        self.dashboard_next_message = label("", "Description")
        next_row_layout.addWidget(self.dashboard_next_message, 1)
        self.dashboard_next_button = button("View Tasks", "primary")
        self.dashboard_next_button.clicked.connect(self._dashboard_next_step_clicked)
        next_row_layout.addWidget(self.dashboard_next_button, 0, Qt.AlignRight | Qt.AlignVCenter)
        next_layout.addWidget(next_row)
        content_lay.addWidget(next_card)

        content_lay.addStretch(1)
        root.addWidget(self._scroll_page(content), 1)
        self.update_dashboard()
        return page

    def _dashboard_next_step_clicked(self) -> None:
        action, _slot_id = self.dashboard_next_action
        if action == "add":
            self.add_task()
        self.navigate("Tasks")

    def make_tasks_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        open_closed_btn = button("Open Closed Tasks", "secondary")
        open_closed_btn.setObjectName("TasksOpenClosedButton")
        open_closed_btn.setFixedHeight(24)
        open_closed_btn.clicked.connect(self.open_closed_tasks)
        add_btn = button("Add Task", "primary", "open")
        add_btn.setObjectName("TasksAddButton")
        add_btn.setFixedHeight(24)
        add_btn.clicked.connect(self.add_task)
        root.addWidget(
            page_header(
                "Tasks",
                "Independent authorized Test Mode browser slots with file import, controls and live counters.",
                [open_closed_btn, add_btn],
            )
        )

        outer = QWidget()
        outer.setObjectName("PageInner")
        outer_lay = vbox(
            outer,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )
        self.task_host = QWidget()
        self.task_host.setObjectName("PageInner")
        self.task_layout = vbox(self.task_host, margins=(0, 0, 0, 0), spacing=8)
        self.task_layout.addStretch(1)
        outer_lay.addWidget(self.task_host)
        outer_lay.addStretch(1)
        root.addWidget(self._scroll_page(outer), 1)
        return page

    def make_reports_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        csv_btn = button("Export CSV", "secondary", "save")
        csv_btn.clicked.connect(self.export_report_csv)
        xls_btn = button("Export Excel", "secondary", "save")
        xls_btn.clicked.connect(self.export_report_excel)
        root.addWidget(
            page_header(
                "Reports",
                "Live processing records with search, status filtering and spreadsheet-safe export.",
                [csv_btn, xls_btn],
            )
        )

        content = QWidget()
        content.setObjectName("PageInner")
        lay = vbox(
            content,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )
        toolbar = card()
        toolbar.layout().setContentsMargins(CONST.card_padding, 8, CONST.card_padding, 8)
        toolbar_row = QWidget()
        tl = hbox(toolbar_row, margins=(0, 0, 0, 0), spacing=CONST.action_gap)
        toolbar.layout().addWidget(toolbar_row)
        self.report_search = search_input("Search report…")
        self.report_search.setMinimumWidth(CONST.table_search_min_width)
        self.report_search.textChanged.connect(self.refresh_report_table)
        tl.addWidget(self.report_search, 1)
        self.report_task = combo_box(["All Tasks"])
        self.report_task.currentTextChanged.connect(self.refresh_report_table)
        tl.addWidget(self.report_task)
        self.report_status = combo_box(
            ["All", "processing", "success", "failed", "interrupted", "unprocessed", "blocked", "limit_reached"]
        )
        self.report_status.currentTextChanged.connect(self.refresh_report_table)
        tl.addWidget(self.report_status)
        clear_btn = button("Clear Report", "danger")
        clear_btn.clicked.connect(self.clear_report)
        tl.addWidget(clear_btn)
        lay.addWidget(toolbar)

        self.report_table = QTableWidget(0, 8)
        self.report_table.setObjectName("InvoiceProductGrid")
        columns = ["timestamp", "slot_id", "email", "status", "message", "attempts", "target_url", "result"]
        self.report_columns = columns
        self.report_table.setHorizontalHeaderLabels([c.replace("_", " ").title() for c in columns])
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.report_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.report_table.setAlternatingRowColors(False)
        header = self.report_table.horizontalHeader()
        for i in range(len(columns)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        lay.addWidget(self.report_table, 1)
        root.addWidget(content, 1)
        return page

    def make_logs_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        save_btn = button("Save Logs", "secondary", "save")
        save_btn.clicked.connect(self.save_logs)
        clear_btn = button("Clear Logs", "danger")
        clear_btn.clicked.connect(self.clear_logs)
        root.addWidget(
            page_header(
                "Live Logs",
                "Application, browser-worker, validation and automation events.",
                [save_btn, clear_btn],
            )
        )
        content = QWidget()
        content.setObjectName("PageInner")
        lay = vbox(
            content,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )
        controls = card()
        controls.layout().setContentsMargins(CONST.card_padding, 8, CONST.card_padding, 8)
        controls_row = QWidget()
        cl = hbox(controls_row, margins=(0, 0, 0, 0), spacing=CONST.action_gap)
        controls.layout().addWidget(controls_row)
        self.autoscroll = QCheckBox("Auto-scroll")
        self.autoscroll.setChecked(True)
        cl.addWidget(self.autoscroll)
        cl.addStretch(1)
        lay.addWidget(controls)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("LogViewer")
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(CONST.log_viewer_min_height)
        lay.addWidget(self.log_text, 1)
        root.addWidget(content, 1)
        return page

    def make_browser_settings_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        save_btn = button("Save Browser Settings", "primary", "save")
        save_btn.clicked.connect(self.save_browser_settings)
        reset_btn = button("Reset Browser Defaults", "danger")
        reset_btn.clicked.connect(self.reset_browser_settings)
        root.addWidget(
            page_header(
                "Browser Settings",
                "Advanced Playwright/Chromium controls backed by real persisted runtime settings.",
                [save_btn, reset_btn],
            )
        )

        inner = QWidget()
        inner.setObjectName("PageInner")
        lay = vbox(
            inner,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )

        # Browser Settings contains editable, backend-backed controls only.
        # Architecture notes and unsupported Chrome policies are documented in
        # README/CHANGELOG instead of appearing as read-only UI settings.

        self.browser_setting_widgets.clear()
        for group_name, keys in BROWSER_SETTING_GROUPS.items():
            c = card(group_name)
            grid = QGridLayout()
            grid.setHorizontalSpacing(CONST.content_gap)
            grid.setVerticalSpacing(CONST.form_group_gap)
            grid.setColumnStretch(1, 1)
            c.layout().addLayout(grid)
            for row, key in enumerate(keys):
                grid.addWidget(
                    label(
                        BROWSER_SETTING_LABELS.get(
                            key, key.replace("_", " ").title()
                        ),
                        "FormLabel",
                        False,
                    ),
                    row,
                    0,
                )
                value = self.settings.get(key, DEFAULT_SETTINGS[key])
                if isinstance(DEFAULT_SETTINGS[key], bool):
                    w = SettingsToggleSwitch(bool(value))
                elif key in BROWSER_SETTING_COMBO_CHOICES:
                    w = combo_box(BROWSER_SETTING_COMBO_CHOICES[key])
                    w.setCurrentText(str(value))
                else:
                    w = line_input("", str(value))

                launch_only_keys = {
                    "browser_executable_path",
                    "headless",
                    "use_chrome_channel",
                    "allow_chromium_fallback",
                    "gpu_enabled",
                    "sandbox_enabled",
                    "audio_enabled",
                    "autoplay_policy",
                    "hardware_video_decode_enabled",
                    "dns_host_resolver_rules",
                    "webrtc_ip_policy",
                    "start_maximized",
                    "window_width",
                    "window_height",
                    "window_position_x",
                    "window_position_y",
                    "browser_launch_timeout",
                    "slow_mo_delay",
                    "downloads_path",
                    "devtools_auto_open",
                    "remote_debugging_port",
                    "additional_chromium_args",
                    "ignored_default_args",
                    "browser_env_json",
                    "background_throttling_enabled",
                    "renderer_process_limit",
                    "chromium_logging_enabled",
                    "chromium_log_file",
                    "crash_dumps_directory",
                    "enable_chrome_features",
                    "disable_chrome_features",
                    "enable_blink_features",
                    "disable_blink_features",
                    "handle_sigint",
                    "handle_sigterm",
                    "handle_sighup",
                    "traces_dir",
                }
                context_only_keys = {
                    "no_viewport",
                    "viewport_width",
                    "viewport_height",
                    "screen_width",
                    "screen_height",
                    "device_scale_factor",
                    "locale",
                    "timezone_id",
                    "geolocation_enabled",
                    "geolocation_latitude",
                    "geolocation_longitude",
                    "geolocation_accuracy",
                    "color_scheme",
                    "reduced_motion",
                    "forced_colors",
                    "contrast",
                    "has_touch",
                    "is_mobile",
                    "accept_downloads",
                    "ignore_https_errors",
                    "client_certificates_json",
                    "javascript_enabled",
                    "strict_selectors",
                    "service_workers",
                    "user_agent",
                    "proxy",
                    "proxy_bypass",
                    "record_har_enabled",
                    "record_har_directory",
                    "record_har_mode",
                    "record_har_content",
                    "page_init_script_enabled",
                    "page_init_script_path",
                    "bypass_csp",
                    "base_url",
                    "record_har_url_filter",
                    "record_video_enabled",
                    "record_video_directory",
                    "record_video_width",
                    "record_video_height",
                }
                if key == "browser_slot_default":
                    w.setToolTip(
                        "Initial browser/task slot count for a newly created workspace."
                    )
                elif key in launch_only_keys:
                    w.setToolTip(
                        "Launch-level control. Saved immediately; takes effect when the browser is next opened."
                    )
                elif key in context_only_keys:
                    w.setToolTip(
                        "Browser-context control. Saved immediately; takes effect on the next context creation/recycle unless Playwright supports a live update."
                    )
                elif key == "use_persistent_context":
                    w.setToolTip(
                        "Managed persistent browser profiles are enabled by default. Applies when the next browser session is opened."
                    )
                elif key == "persistent_user_data_dir":
                    w.setToolTip(
                        "Blank uses VibraPilot's managed LocalAppData browser-profile root. Do not select your everyday Google Chrome User Data folder."
                    )
                elif key == "downloads_path":
                    w.setToolTip(
                        "Blank uses VibraPilot's durable per-Task managed Downloads folder. An explicit path preserves the configured shared download directory."
                    )
                elif key == "dedicated_profile_per_task":
                    w.setToolTip(
                        "Each Task slot owns a separate managed browser User Data Directory when enabled."
                    )
                elif key in {
                    "persistent_profile_directory",
                    "profile_lock_policy",
                    "persist_profile_between_runs",
                    "persist_profile_cache",
                    "restore_previous_session",
                    "extensions_enabled",
                }:
                    w.setToolTip(
                        "Persistent-profile control. Applies when the next browser session is opened."
                    )
                elif key == "browser_startup_url":
                    w.setToolTip(
                        "Optional page opened when a browser is first created. The task Target URL remains authoritative when automation starts."
                    )
                elif key == "remote_debugging_port":
                    w.setToolTip(
                        "0 disables the external debugging port. Non-zero ports bind to 127.0.0.1 only."
                    )
                elif key == "extra_http_headers_json":
                    w.setToolTip(
                        'JSON object, for example {"X-Test-Header":"value"}.'
                    )
                elif key == "client_certificates_json":
                    w.setToolTip(
                        'JSON array using Playwright client-certificate fields: origin plus pfxPath, or certPath + keyPath. Optional passphrase is stored in local settings if supplied.'
                    )
                elif key == "browser_env_json":
                    w.setToolTip(
                        'JSON object of environment variables visible to the Chromium process.'
                    )
                elif key == "extension_paths":
                    w.setToolTip(
                        "Semicolon-separated unpacked extension directories. Each directory must contain a valid manifest.json. Extensions require Persistent Browser Context and bundled/custom Chromium."
                    )

                self.browser_setting_widgets[key] = w
                grid.addWidget(w, row, 1)
            lay.addWidget(c)

        lay.addStretch(1)
        root.addWidget(self._scroll_page(inner), 1)
        return page

    def make_workflow_inputs_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        save_btn = button("Save Workflow Inputs", "primary", "save")
        save_btn.clicked.connect(self.save_workflow_inputs)
        reset_btn = button("Reset Workflow Inputs", "danger")
        reset_btn.clicked.connect(self.reset_workflow_inputs)
        root.addWidget(
            page_header(
                "Workflow Inputs",
                "Workflow-specific form values are kept separate from application and browser settings.",
                [save_btn, reset_btn],
            )
        )

        inner = QWidget()
        inner.setObjectName("PageInner")
        lay = vbox(
            inner,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )

        form_card = card("Default Form Inputs")
        grid = QGridLayout()
        grid.setHorizontalSpacing(CONST.content_gap)
        grid.setVerticalSpacing(CONST.form_group_gap)
        grid.setColumnStretch(1, 1)
        form_card.layout().addLayout(grid)

        self.workflow_input_widgets.clear()
        for row, field in enumerate(WORKFLOW_INPUT_FIELDS):
            grid.addWidget(label(field.label, "FormLabel", False), row, 0)
            value = self.settings.get(field.key, DEFAULT_SETTINGS[field.key])
            widget = line_input(field.placeholder, str(value))
            if field.help_text:
                widget.setToolTip(field.help_text)
            self.workflow_input_widgets[field.key] = widget
            grid.addWidget(widget, row, 1)

        lay.addWidget(form_card)
        lay.addStretch(1)
        root.addWidget(self._scroll_page(inner), 1)
        return page

    def make_settings_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        save_btn = button("Save App Settings", "primary", "save")
        save_btn.clicked.connect(self.save_settings)
        reset_btn = button("Reset App Defaults", "danger")
        reset_btn.clicked.connect(self.reset_settings)
        root.addWidget(
            page_header(
                "App Settings",
                "Application, safety, task-processing and license/API runtime configuration.",
                [save_btn, reset_btn],
            )
        )
        inner = QWidget()
        inner.setObjectName("PageInner")
        lay = vbox(
            inner,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )

        groups = {
            "Test Safety Settings": ["authorized_testing_only", "max_test_send_limit"],
            "Task Processing Settings": [
                "batch_size", "auto_save_interval", "max_concurrent_tasks", "save_failed_data",
                "save_unprocessed_data_on_close", "remove_duplicate_rows",
            ],
            "App Settings": [
                "theme_mode", "log_level", "auto_open_report_after_export",
                "confirm_before_close_while_running", "license_recheck_minutes",
                "request_timeout",
            ],
            "App-specific Settings": ["default_target_url"],
        }

        self.setting_widgets.clear()
        for group_name, keys in groups.items():
            c = card(group_name)
            grid = QGridLayout()
            grid.setHorizontalSpacing(CONST.content_gap)
            grid.setVerticalSpacing(CONST.form_group_gap)
            grid.setColumnStretch(1, 1)
            c.layout().addLayout(grid)
            for row, key in enumerate(keys):
                grid.addWidget(label(key.replace("_", " ").title(), "FormLabel", False), row, 0)
                value = self.settings.get(key)
                if isinstance(value, bool):
                    w = SettingsToggleSwitch(bool(value))
                elif key == "theme_mode":
                    w = combo_box(["Dark"], 0)
                    w.setCurrentText("Dark")
                    w.setToolTip(f"v{APP_VERSION} supports the official Vib Tools Dark theme.")
                elif key == "log_level":
                    w = combo_box(["DEBUG", "INFO", "WARNING", "ERROR"])
                    w.setCurrentText(str(value))
                else:
                    w = line_input("", str(value))
                if key == "default_target_url":
                    w.setToolTip(
                        "Initial URL for newly created tasks only. Editing a task URL remains independent and is not overwritten by this setting."
                    )
                elif key == "batch_size":
                    w.setToolTip(
                        "Sequential batch boundary size. Processing remains one recipient at a time; a durable checkpoint boundary is committed after each batch."
                    )
                elif key == "auto_save_interval":
                    w.setToolTip(
                        "Periodic task-state autosave interval in seconds. 0 disables time-based autosave; finalized recipients are still persisted safely."
                    )
                elif key == "max_concurrent_tasks":
                    w.setToolTip(
                        "Maximum number of task browser workers that may be open at the same time. Additional task cards may still be created."
                    )
                elif key == "request_timeout":
                    w.setToolTip(
                        "HTTP timeout for license/API validation requests. This is an application/network setting, not a Playwright page-navigation timeout."
                    )
                self.setting_widgets[key] = w
                grid.addWidget(w, row, 1)
            lay.addWidget(c)

        notice = card("Secure Licora API v2")
        notice.layout().addWidget(
            label(
                f"Secure licensing endpoint: {LICENSING.api_base_url}/api/v2/. "
                f"Application ID: {LICENSING.app_id}. Device-bound P-256 proofs and "
                "locally verified RS256 access tokens are used; no client master API key is embedded.",
                "Description",
            )
        )
        lay.addWidget(notice)
        lay.addStretch(1)
        root.addWidget(self._scroll_page(inner), 1)
        return page

    def make_about_page(self) -> QWidget:
        page = page_frame()
        root = vbox(page, margins=(0, 0, 0, 0), spacing=0)
        root.addWidget(page_header(ABOUT.page_title, ABOUT.page_subtitle))
        content = QWidget()
        content.setObjectName("PageInner")
        lay = vbox(
            content,
            margins=(CONST.page_padding, CONST.page_padding, CONST.page_padding, CONST.page_padding),
            spacing=CONST.content_gap,
        )
        identity = card(APP.display_name, f"{ABOUT.edition_label} • backend v{APP.version}")
        identity.layout().addWidget(label(ABOUT.app_description, "Description"))
        identity.layout().addWidget(label(ABOUT.company_description, "Description", False))
        identity.layout().addWidget(label(ABOUT.company_profile_description, "Description", False))
        if ABOUT.company_legal_name:
            identity.layout().addWidget(
                label(f"Legal name: {ABOUT.company_legal_name}", "Description", False)
            )
        identity.layout().addWidget(status_badge(ABOUT.identity_badge, "success"))
        lay.addWidget(identity)

        design = card(ABOUT.design_contract_title)
        dl = design.layout()
        for text in ABOUT.design_contract_items:
            dl.addWidget(label(text, "Description", False))
        lay.addWidget(design)

        license_card = card(ABOUT.license_session_title)
        ll = license_card.layout()
        ll.addWidget(label(f"License app ID: {APP.app_id}", "Description", False))
        ll.addWidget(label(f"Activated until: {self.license_manager.activated_until or 'Server-managed'}", "Description", False))
        if SUPPORT.support_email:
            ll.addWidget(label(f"Support: {SUPPORT.support_email}", "Description", False))
        for link_label, url in SUPPORT.about_support_links:
            ll.addWidget(label(f"{link_label}: {url}", "Description", False))
        for social_link in ENABLED_SOCIAL_LINKS:
            ll.addWidget(label(f"{social_link.platform}: {social_link.url}", "Description", False))
        lay.addWidget(license_card)
        lay.addStretch(1)
        root.addWidget(self._scroll_page(content), 1)
        return page

    # ---------- task collection ----------

    def _add_task_with_id(self, slot_id: int) -> TaskSlotWidget | None:
        task_layout = self.task_layout
        if task_layout is None:
            return None
        if slot_id in self.tasks:
            return self.tasks[slot_id]
        slot = TaskSlotWidget(self, slot_id)
        insert_at = max(0, task_layout.count() - 1)
        task_layout.insertWidget(insert_at, slot)
        self.tasks[slot_id] = slot
        self.next_slot_id = max(self.next_slot_id, slot_id + 1)
        self._refresh_report_task_filter()
        self.update_dashboard()
        return slot

    def add_task(self) -> None:
        closed_slots = set(self.runtime_store.closed_slot_ids())
        candidate = max(1, int(self.next_slot_id))
        while candidate in self.tasks or candidate in closed_slots:
            candidate += 1
        self._add_task_with_id(candidate)
        self.schedule_workspace_save()

    def remove_task(self, slot_id: int) -> None:
        self.tasks.pop(slot_id, None)
        self._refresh_report_task_filter()
        self.update_dashboard()
        self.schedule_workspace_save()

    def open_closed_tasks(self) -> None:
        if self.workflow_state_error or not self.active_workflow_id:
            _message(
                self,
                "Workflow state blocked",
                "Closed Task recovery is blocked until the active workflow state is valid.",
                "warning",
            )
            return
        closed = sorted(
            self.runtime_store.closed_runs(),
            key=lambda row: (int(row.get("slot_id", 0)), str(row.get("updated_at", ""))),
        )
        if not closed:
            _message(self, "Closed Tasks", "There are no closed Tasks to reopen.")
            return

        restored = 0
        conflicts: list[int] = []
        for summary in closed:
            slot_id = int(summary.get("slot_id", 0))
            run_id = str(summary.get("run_id", ""))
            if slot_id <= 0 or not run_id:
                continue
            if slot_id in self.tasks:
                conflicts.append(slot_id)
                continue
            run = self.runtime_store.reopen_closed_run(run_id, now_str())
            if not run:
                continue
            slot = self._add_task_with_id(slot_id)
            if slot is None:
                # Restore the archived marker if the UI could not own the slot.
                self.runtime_store.close_run(
                    run_id=run_id,
                    task_status=str(run.get("task_status", "Ready")),
                    timestamp=now_str(),
                    current_index=int(run.get("current_index", 0)),
                    total=int(run.get("total", 0)),
                    success_count=int(run.get("success_count", 0)),
                    failed_count=int(run.get("failed_count", 0)),
                    send_limit_used=int(run.get("send_limit_used", 0)),
                    manual_review_required=bool(run.get("manual_review_required", 0)),
                    target_url=str(run.get("target_url", "")),
                    items=[
                        TaskItem(
                            email=str(item.get("email", "")),
                            name=str(item.get("name", "")),
                            status=str(item.get("status", "pending")),
                            attempts=int(item.get("attempts", 0)),
                            message=str(item.get("message", "")),
                            result=str(item.get("result", "")),
                        )
                        for item in run.get("items", [])
                    ],
                )
                continue
            slot.restore_runtime(run, preserve_task_status=True)
            slot._render_browser_status("Closed")
            slot._set_metric("Login", "Not Verified")
            restored += 1
            self.log_ui(
                f"Task {slot_id}: reopened from Closed Tasks; browser remains closed until explicitly opened."
            )

        self.update_dashboard()
        if conflicts:
            self.log_ui(
                "Closed Task restore skipped occupied slot IDs: "
                + ", ".join(str(slot_id) for slot_id in sorted(set(conflicts))),
                "WARNING",
            )
        if restored == 0:
            _message(
                self,
                "Closed Tasks",
                "No closed Task could be reopened because its original slot is currently in use.",
                "warning",
            )
        self.schedule_workspace_save()

    def _persistent_profile_claim(self, slot: TaskSlotWidget) -> str | None:
        if not bool(self.settings.get("use_persistent_context", DEFAULT_SETTINGS["use_persistent_context"])):
            return None
        if not bool(self.settings.get("persist_profile_between_runs", DEFAULT_SETTINGS["persist_profile_between_runs"])):
            return None
        return str(
            AutomationWorker.resolve_persistent_user_data_dir(
                dict(self.settings.data), slot.slot_id
            )
        )

    def can_open_task_browser(self, slot: TaskSlotWidget) -> tuple[bool, str]:
        if self._workflow_restart_required:
            return False, "Workflow switch is committed. Restart VibraPilot before opening automation browsers."
        if self.workflow_state_error or not self.active_workflow_id:
            return False, (
                "Active workflow state is unavailable. Automation is fail-closed until "
                "the workflow state is repaired."
            )
        limit = max(1, int(self.settings.get("max_concurrent_tasks", DEFAULT_SETTINGS["max_concurrent_tasks"])))
        active = [
            task for task in self.tasks.values()
            if task.slot_id != slot.slot_id and task.worker and task.worker.is_alive()
        ]
        if len(active) >= limit:
            return False, f"Maximum Concurrent Tasks is {limit}. Close an active task browser before opening another."
        try:
            claim = self._persistent_profile_claim(slot)
            if claim:
                for other in active:
                    if self._persistent_profile_claim(other) == claim:
                        return False, (
                            "Another running task already owns the same persistent browser profile. "
                            "Enable Dedicated Profile Per Task or close the other browser first."
                        )
        except ValueError as exc:
            return False, str(exc)
        return True, ""

    def _workflow_switch_paths(self) -> list[Path]:
        """Return only the approved workflow-scoped persistence files."""
        paths = [
            TASK_RUNTIME_DB,
            Path(str(TASK_RUNTIME_DB) + "-wal"),
            Path(str(TASK_RUNTIME_DB) + "-shm"),
            APP_STATE_FILE,
            SETTINGS_FILE,
        ]
        paths.extend(sorted(APP_DATA_DIR.glob("slot_*_checkpoint.json")))
        return paths

    def _workflow_switch_block_reason(self) -> str:
        if self._workflow_switch_in_progress:
            return "Another workflow switch transaction is already in progress."
        if self.workflow_state_error or not self.active_workflow_id:
            return "Active workflow state is invalid or unavailable."
        running = [task.slot_id for task in self.tasks.values() if task.is_running()]
        if running:
            return "Workflow switching is blocked while Tasks are running: " + ", ".join(
                str(value) for value in running
            )
        manual = [
            task.slot_id
            for task in self.tasks.values()
            if bool(task.state.manual_review_required)
        ]
        if manual:
            return (
                "Workflow switching is blocked while Tasks require manual review: "
                + ", ".join(str(value) for value in manual)
            )
        return ""

    def _confirm_workflow_switch(self, current: str, target: str) -> bool:
        return _confirm(
            self,
            "Switch workflow",
            f"Switch workflow from {current} to {target}?\n\n"
            "This will clear current Task cards, the live task runtime database/results, "
            "Task checkpoints, workspace Task references and current Workflow Input values.\n\n"
            "License/device identity, global App Settings, Browser Settings, browser profiles "
            "and session storage, downloads/extensions, exported Reports/FailedData, Logs, "
            "user source files, window geometry and selected page will be preserved.\n\n"
            "VibraPilot will restart after the switch is committed.",
        )

    def _settle_workflow_workers(self) -> bool:
        for task in list(self.tasks.values()):
            if task.worker and task.worker.is_alive():
                if task.worker.is_processing():
                    return False
                if not task.close_browser(wait=True):
                    return False
        return True

    def _clear_workflow_scoped_state(self, workspace_snapshot: dict[str, Any]) -> None:
        """Apply only the owner-approved clear list before workflow-state commit."""
        self.runtime_store.close()
        for path in (
            TASK_RUNTIME_DB,
            Path(str(TASK_RUNTIME_DB) + "-wal"),
            Path(str(TASK_RUNTIME_DB) + "-shm"),
        ):
            if path.exists():
                path.unlink()
        for path in APP_DATA_DIR.glob("slot_*_checkpoint.json"):
            if path.is_file():
                path.unlink()

        for key in WORKFLOW_INPUT_KEYS:
            self.settings.data[key] = DEFAULT_SETTINGS.get(key, "")
        self.settings.save()

        self.workspace_store.save(
            {
                "saved_at": now_str(),
                "active_tasks": [],
                "next_slot_id": 1,
                "selected_page": workspace_snapshot.get(
                    "selected_page", self._selected_page_name
                ),
                "window": workspace_snapshot.get("window", {}),
            }
        )
        self.runtime_store = TaskRuntimeStore(TASK_RUNTIME_DB)
        self.report_rows = []
        self._report_dirty = True

    def _restore_after_failed_workflow_switch(
        self, settings_snapshot: dict[str, Any]
    ) -> None:
        self.settings.data = dict(settings_snapshot)
        self.runtime_store = TaskRuntimeStore(TASK_RUNTIME_DB)
        self.report_rows = self.runtime_store.results(limit=REPORT_RECENT_LIMIT)
        self._report_dirty = True
        self._refresh_report_task_filter()
        self.update_dashboard()

    def _finalize_committed_workflow_switch(self, workflow_id: str) -> None:
        self.active_workflow_id = workflow_id
        for task in list(self.tasks.values()):
            task.worker = None
            task.setParent(None)
            task.deleteLater()
        self.tasks.clear()
        self.next_slot_id = 1
        self._workspace_restored_run_ids.clear()
        self.report_rows = []
        self._report_dirty = True
        self._refresh_report_task_filter()
        self.update_dashboard()

    def _spawn_workflow_restart(self) -> None:
        if getattr(sys, "frozen", False):
            command = [sys.executable]
            cwd = str(Path(sys.executable).resolve().parent)
        else:
            command = [sys.executable, str(ROOT_DIR / "run.py")]
            cwd = str(ROOT_DIR)
        subprocess.Popen(command, cwd=cwd)

    def request_workflow_switch(self, target_workflow_id: str) -> str:
        """Execute the PR-06 fail-closed atomic switch transaction.

        PR-07 may call this service from future Workflow UI. PR-06 itself adds no
        workflow-selection page or activation button.
        """
        target = str(target_workflow_id).strip()
        if not target:
            raise WorkflowSwitchBlockedError("Target workflow ID is empty.")
        if self._workflow_switch_in_progress:
            raise WorkflowSwitchBlockedError(
                "Another workflow switch transaction is already in progress."
            )
        try:
            persisted = self.workflow_state_store.load_existing()
        except WorkflowStateError as exc:
            self.workflow_state_error = str(exc)
            raise WorkflowSwitchBlockedError(
                f"Active workflow state is unavailable: {exc}"
            ) from exc
        current = persisted.active_workflow_id
        if target == current:
            return "already_active"

        # Validate both manifest registration and an explicit source-controlled
        # runtime factory before asking the user to confirm any destructive action.
        self.workflow_catalog.require_workflow(target)
        self.workflow_catalog.require_runtime_factory(target)
        blocker = self._workflow_switch_block_reason()
        if blocker:
            raise WorkflowSwitchBlockedError(blocker)
        if not self._confirm_workflow_switch(current, target):
            return "cancelled"

        # Persist the latest approved workspace snapshot before rollback staging.
        if self.workspace_save_timer.isActive():
            self.workspace_save_timer.stop()
        self.save_workspace_state()
        workspace_snapshot = self._workspace_snapshot()
        settings_snapshot = dict(self.settings.data)

        self._workflow_switch_in_progress = True
        transaction = WorkflowSwitchTransaction(
            data_root=APP_DATA_DIR,
            transaction_root=self.workflow_switch_root,
            old_workflow_id=current,
            target_workflow_id=target,
        )
        committed = False
        try:
            if not self._settle_workflow_workers():
                raise WorkflowSwitchBlockedError(
                    "One or more Task workers could not settle safely; workflow switch aborted."
                )
            transaction.prepare(self._workflow_switch_paths())
            try:
                self._clear_workflow_scoped_state(workspace_snapshot)
                new_state = self.workflow_state_store.commit_active_workflow(
                    target, expected_current_workflow_id=current
                )
                committed = True
            except BaseException:
                transaction.rollback()
                self._restore_after_failed_workflow_switch(settings_snapshot)
                raise

            # The workflow-state os.replace above is the commit point. From here
            # onward the target workflow is authoritative and old data must not be
            # restored, even if restart spawning fails.
            try:
                transaction.mark_committed()
            except Exception as exc:
                logging.exception("Workflow switch committed but transaction marker update failed")
                self.log_ui(
                    f"Workflow switch committed; transaction cleanup will be recovered on restart: {exc}",
                    "WARNING",
                )
            self._finalize_committed_workflow_switch(new_state.active_workflow_id)
            try:
                transaction.cleanup()
            except Exception as exc:
                logging.exception("Committed workflow switch staging cleanup failed")
                self.log_ui(
                    f"Workflow switch committed; stale transaction staging will be cleaned on restart: {exc}",
                    "WARNING",
                )

            self._workflow_restart_required = True
            try:
                self._spawn_workflow_restart()
            except Exception as exc:
                logging.exception("Workflow switch restart spawn failed")
                _message(
                    self,
                    "Manual restart required",
                    "Workflow switch was committed successfully, but VibraPilot could not "
                    f"start the replacement process. Restart VibraPilot manually.\n\n{exc}",
                    "error",
                )
                return "committed_restart_required"

            QTimer.singleShot(0, self.close)
            return "switched"
        except WorkflowSwitchBlockedError:
            if not committed:
                self._workflow_switch_in_progress = False
            raise
        except BaseException:
            if not committed:
                self._workflow_switch_in_progress = False
            raise

    def _refresh_report_task_filter(self) -> None:
        if not hasattr(self, "report_task"):
            return
        current = self.report_task.currentText()
        slot_ids = sorted(set(self.tasks) | set(self.runtime_store.result_slot_ids()))
        values = ["All Tasks"] + [f"Task {slot_id}" for slot_id in slot_ids]
        self.report_task.blockSignals(True)
        self.report_task.clear()
        self.report_task.addItems(values)
        self.report_task.setCurrentText(current if current in values else "All Tasks")
        self.report_task.blockSignals(False)

    def offer_task_recovery(self) -> None:
        if self.workflow_state_error or not self.active_workflow_id:
            return
        recoverable = self.runtime_store.recoverable_runs()
        for summary in recoverable:
            run_id = str(summary.get("run_id", ""))
            if run_id in self._workspace_restored_run_ids:
                continue
            run = self.runtime_store.load_run(run_id)
            if not run:
                continue
            slot_id = int(run.get("slot_id", 0))
            manual = bool(run.get("manual_review_required", 0))
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning if manual else QMessageBox.Question)
            box.setWindowTitle("Task Recovery")
            if manual:
                box.setText(
                    f"Task {slot_id} has an ambiguous Send outcome. Automatic retry is blocked. "
                    "Choose how to preserve or review this recovery state."
                )
                keep = box.addButton("Keep for Manual Review", QMessageBox.AcceptRole)
                skip = box.addButton("Mark Reviewed / Skip Current", QMessageBox.ActionRole)
                discard = box.addButton("Discard Recovery", QMessageBox.DestructiveRole)
                box.exec()
                clicked = box.clickedButton()
                if clicked is discard:
                    self.runtime_store.discard_run(run_id, now_str())
                    continue
                if clicked is skip:
                    self.runtime_store.skip_current_manual_review(run_id, now_str())
                    run = self.runtime_store.load_run(run_id) or run
                elif clicked is not keep:
                    continue
            else:
                box.setText(
                    f"Recover unfinished Task {slot_id}? Recovery restores data/progress only; "
                    "it will not open a browser or send automatically."
                )
                restore = box.addButton("Recover Task", QMessageBox.AcceptRole)
                discard = box.addButton("Discard Recovery", QMessageBox.DestructiveRole)
                box.exec()
                clicked = box.clickedButton()
                if clicked is discard:
                    self.runtime_store.discard_run(run_id, now_str())
                    continue
                if clicked is not restore:
                    continue
            slot = self._add_task_with_id(slot_id)
            if slot is not None:
                slot.restore_runtime(run)
                self.log_ui(f"Task {slot_id}: recovered runtime state; browser remains closed until explicitly opened.")
        self.report_rows = self.runtime_store.results(limit=REPORT_RECENT_LIMIT)
        self._refresh_report_task_filter()
        self.refresh_report_table()
        self.schedule_workspace_save()

    def resolve_manual_review(self, slot: TaskSlotWidget) -> bool:
        if not slot.state.manual_review_required:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Manual Review Required")
        box.setText(
            "The current recipient has an ambiguous prior Send outcome. Automatic retry is blocked. "
            "After reviewing the target manually, you may skip this recipient and continue."
        )
        skip = box.addButton("Mark Reviewed / Skip Current", QMessageBox.AcceptRole)
        keep = box.addButton("Keep for Manual Review", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not skip:
            return False
        self.runtime_store.skip_current_manual_review(slot.state.run_id, now_str())
        run = self.runtime_store.load_run(slot.state.run_id)
        if run:
            slot.restore_runtime(run)
        return True

    # ---------- settings ----------

    def _widget_value(self, key: str, widget: QWidget) -> Any:
        if isinstance(widget, ToggleSwitch):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QLineEdit):
            return widget.text()
        return ""

    def parse_setting_value(self, key: str, value: Any) -> Any:
        default = DEFAULT_SETTINGS[key]
        if isinstance(default, bool):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "t", "y")

        if isinstance(default, int):
            parsed = int(value)
            if key == "max_test_send_limit":
                return validate_test_send_limit(parsed)
            minimums = {
                "browser_slot_default": 1,
                "browser_launch_timeout": 1000,
                "page_navigation_timeout": 1000,
                "selector_timeout": 1000,
                "slow_mo_delay": 0,
                "network_idle_timeout": 1,
                "short_dom_probe_timeout": 1,
                "standard_dom_probe_timeout": 1,
                "modal_state_probe_timeout": 1,
                "modal_close_probe_timeout": 1,
                "modal_close_poll_count": 1,
                "notification_visibility_timeout": 1,
                "visible_text_timeout": 1,
                "text_content_timeout": 1,
                "security_body_read_timeout": 1,
                "security_body_text_limit": 1,
                "browser_context_recycle_after_n_items": 0,
                "browser_context_recycle_after_n_minutes": 0,
                "max_retry_per_item": 0,
                "max_navigation_retry": 0,
                "max_selector_retry": 0,
                "batch_size": 1,
                "auto_save_interval": 0,
                "max_concurrent_tasks": 1,
                "connection_retry_count": 0,
                "network_error_retry_delay": 0,
                "license_recheck_minutes": 1,
                "window_width": 0,
                "window_height": 0,
                "window_position_x": -1,
                "window_position_y": -1,
                "viewport_width": 1,
                "viewport_height": 1,
                "screen_width": 0,
                "screen_height": 0,
                "remote_debugging_port": 0,
                "renderer_process_limit": 0,
                "browser_restart_max_attempts": 0,
                "record_video_width": 0,
                "record_video_height": 0,
            }
            if key in minimums and parsed < minimums[key]:
                raise ValueError(
                    f"{BROWSER_SETTING_LABELS.get(key, key.replace('_', ' ').title())} "
                    f"must be {minimums[key]} or greater."
                )
            if key == "request_timeout" and not 1 <= parsed <= 300:
                raise ValueError(
                    "Request Timeout must be between 1 and 300 seconds."
                )
            if key == "remote_debugging_port" and parsed not in {0} and not 1024 <= parsed <= 65535:
                raise ValueError(
                    "Remote Debugging Port must be 0 (disabled) or between 1024 and 65535."
                )
            return parsed

        if isinstance(default, float):
            parsed = float(value)
            minimums = {
                "browser_context_recycle_after_n_minutes": 0.0,
                "login_state_poll_interval": 0.0,
                "modal_close_poll_interval": 0.01,
                "notification_poll_interval": 0.01,
                "retry_delay_min": 0.0,
                "retry_delay_max": 0.0,
                "backoff_multiplier": 1.0,
                "delay_between_items_min": 0.0,
                "delay_between_items_max": 0.0,
                "device_scale_factor": 0.1,
                "geolocation_accuracy": 0.0,
                "browser_restart_delay": 0.0,
            }
            if key in minimums and parsed < minimums[key]:
                raise ValueError(
                    f"{BROWSER_SETTING_LABELS.get(key, key.replace('_', ' ').title())} "
                    f"must be {minimums[key]} or greater."
                )
            if key == "geolocation_latitude" and not -90 <= parsed <= 90:
                raise ValueError("Geolocation Latitude must be between -90 and 90.")
            if key == "geolocation_longitude" and not -180 <= parsed <= 180:
                raise ValueError(
                    "Geolocation Longitude must be between -180 and 180."
                )
            return parsed

        parsed_text = str(value).strip()
        if key in BROWSER_SETTING_COMBO_CHOICES:
            allowed = set(BROWSER_SETTING_COMBO_CHOICES[key])
            if parsed_text not in allowed:
                raise ValueError(
                    f"{BROWSER_SETTING_LABELS.get(key, key)} must be one of: "
                    + ", ".join(BROWSER_SETTING_COMBO_CHOICES[key])
                )
            return parsed_text

        if key in {"extra_http_headers_json", "browser_env_json"}:
            if not parsed_text:
                parsed_text = "{}"
            parsed_json = json.loads(parsed_text)
            if not isinstance(parsed_json, dict):
                raise ValueError(
                    f"{BROWSER_SETTING_LABELS.get(key, key)} must be a JSON object."
                )
            return json.dumps(parsed_json, separators=(",", ":"), ensure_ascii=False)

        if key == "client_certificates_json":
            if not parsed_text:
                parsed_text = "[]"
            parsed_json = json.loads(parsed_text)
            if not isinstance(parsed_json, list):
                raise ValueError("Client Certificates must be a JSON array.")
            for index, item in enumerate(parsed_json, start=1):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"Client Certificate #{index} must be a JSON object."
                    )
                origin = str(item.get("origin", "")).strip()
                if not origin.startswith(("http://", "https://")):
                    raise ValueError(
                        f"Client Certificate #{index} requires an http(s) origin."
                    )
                cert_path = str(item.get("certPath", "")).strip()
                key_path = str(item.get("keyPath", "")).strip()
                pfx_path = str(item.get("pfxPath", "")).strip()
                if pfx_path:
                    if not Path(pfx_path).expanduser().is_file():
                        raise ValueError(
                            f"Client Certificate #{index} PFX file does not exist."
                        )
                elif cert_path and key_path:
                    if not Path(cert_path).expanduser().is_file():
                        raise ValueError(
                            f"Client Certificate #{index} certificate file does not exist."
                        )
                    if not Path(key_path).expanduser().is_file():
                        raise ValueError(
                            f"Client Certificate #{index} key file does not exist."
                        )
                else:
                    raise ValueError(
                        f"Client Certificate #{index} requires pfxPath or certPath + keyPath."
                    )
            return json.dumps(parsed_json, separators=(",", ":"), ensure_ascii=False)

        return parsed_text

    def refresh_browser_settings_widgets(self) -> None:
        """Display the exact values held by the backend SettingsManager."""
        for key, widget in self.browser_setting_widgets.items():
            if key not in DEFAULT_SETTINGS:
                continue
            value = self.settings.get(key, DEFAULT_SETTINGS[key])
            if isinstance(widget, ToggleSwitch):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

    def save_browser_settings(self) -> None:
        try:
            parsed_settings: dict[str, Any] = {}
            for key, widget in self.browser_setting_widgets.items():
                parsed_settings[key] = self.parse_setting_value(
                    key, self._widget_value(key, widget)
                )

            if parsed_settings["retry_delay_max"] < parsed_settings["retry_delay_min"]:
                raise ValueError(
                    "Retry Delay Max cannot be lower than Retry Delay Min."
                )
            if parsed_settings["delay_between_items_max"] < parsed_settings["delay_between_items_min"]:
                raise ValueError(
                    "Delay Between Items Max cannot be lower than Delay Between Items Min."
                )

            window_dimensions = (
                parsed_settings["window_width"],
                parsed_settings["window_height"],
            )
            if (window_dimensions[0] == 0) != (window_dimensions[1] == 0):
                raise ValueError(
                    "Window Width and Window Height must both be 0 or both be greater than 0."
                )

            window_position = (
                parsed_settings["window_position_x"],
                parsed_settings["window_position_y"],
            )
            if (window_position[0] < 0) != (window_position[1] < 0):
                raise ValueError(
                    "Window Position X and Y must both be -1 (automatic) or both be 0 or greater."
                )

            screen_dimensions = (
                parsed_settings["screen_width"],
                parsed_settings["screen_height"],
            )
            if (screen_dimensions[0] == 0) != (screen_dimensions[1] == 0):
                raise ValueError(
                    "Screen Width and Screen Height must both be 0 or both be greater than 0."
                )

            executable_path = str(
                parsed_settings["browser_executable_path"]
            ).strip()
            if executable_path and not Path(executable_path).expanduser().is_file():
                raise ValueError(
                    "Google Chrome / Chromium Executable Path does not exist."
                )

            startup_url = str(parsed_settings["browser_startup_url"]).strip()
            if startup_url and not startup_url.startswith(("http://", "https://")):
                raise ValueError(
                    "Optional Browser Startup URL must begin with http:// or https://."
                )

            base_url = str(parsed_settings["base_url"]).strip()
            if base_url and not base_url.startswith(("http://", "https://")):
                raise ValueError(
                    "Browser Base URL must begin with http:// or https://."
                )

            video_dimensions = (
                parsed_settings["record_video_width"],
                parsed_settings["record_video_height"],
            )
            if (video_dimensions[0] == 0) != (video_dimensions[1] == 0):
                raise ValueError(
                    "Video Width and Video Height must both be 0 or both be greater than 0."
                )
            if parsed_settings["record_video_enabled"] and not str(
                parsed_settings["record_video_directory"]
            ).strip():
                raise ValueError(
                    "Video Recording is enabled but Record Video Directory is empty."
                )

            init_script = str(parsed_settings["page_init_script_path"]).strip()
            if parsed_settings["page_init_script_enabled"]:
                if not init_script:
                    raise ValueError(
                        "Page Initialization Script is enabled but no script file was selected."
                    )
                if not Path(init_script).expanduser().is_file():
                    raise ValueError(
                        "Page Initialization Script File does not exist."
                    )

            extension_paths = normalize_extension_paths(
                str(parsed_settings["extension_paths"])
            )
            if parsed_settings["restore_previous_session"] and not parsed_settings["use_persistent_context"]:
                raise ValueError(
                    "Restore Previous Browser Session requires Use Persistent Browser Context."
                )
            if parsed_settings["restore_previous_session"] and not parsed_settings["persist_profile_between_runs"]:
                raise ValueError(
                    "Restore Previous Browser Session requires Persist Profile Between Runs."
                )

            if parsed_settings["extensions_enabled"]:
                if not parsed_settings["use_persistent_context"]:
                    raise ValueError(
                        "Extension Loading requires Use Persistent Browser Context."
                    )
                extension_paths = validate_unpacked_extension_directories(
                    str(parsed_settings["extension_paths"])
                )
                parsed_settings["extension_paths"] = ";".join(
                    str(path) for path in extension_paths
                )
                if (
                    parsed_settings["use_chrome_channel"]
                    and not executable_path
                ):
                    raise ValueError(
                        "Google Chrome no longer supports Playwright side-loaded extension flags. "
                        "For unpacked extensions, disable Use Google Chrome Channel and use bundled Chromium, "
                        "or provide a compatible custom Chromium executable."
                    )

            if parsed_settings["use_persistent_context"]:
                raw_profile_root = str(parsed_settings["persistent_user_data_dir"]).strip()
                if raw_profile_root:
                    profile_root = Path(raw_profile_root).expanduser()
                    if not profile_root.is_absolute():
                        profile_root = APP_DATA_DIR / profile_root
                    AutomationWorker.validate_managed_browser_profile_path(profile_root)

            self.settings.data.update(parsed_settings)
            self.settings.save()

            # Active workers own Playwright objects in their own threads. Queue
            # the new settings into each worker instead of touching browser/context
            # objects from the Qt UI thread. Runtime-safe values become effective
            # immediately; launch/context-construction values apply on the next
            # browser/context lifecycle as appropriate.
            synced_workers = 0
            for slot in self.tasks.values():
                worker = slot.worker
                if worker and worker.is_alive():
                    worker.settings = dict(self.settings.data)
                    worker.control_queue.put(
                        ("settings", {"settings": dict(self.settings.data)})
                    )
                    synced_workers += 1

            # Render back from the backend settings manager after normalization.
            self.refresh_browser_settings_widgets()

            self.log_ui(
                f"Browser settings saved; synchronized {synced_workers} active browser worker(s)."
            )
            _message(
                self,
                "Browser Settings",
                "Browser settings saved successfully. Runtime-safe settings were synchronized "
                "to active workers. Launch-level controls apply when a browser is next opened; "
                "persistent-profile and context-construction controls apply on the next relevant lifecycle.",
            )
        except Exception as exc:
            _message(self, "Browser Settings error", str(exc), "error")

    def reset_browser_settings(self) -> None:
        if not _confirm(
            self, "Reset Browser Settings", "Reset only Browser Settings to source defaults?"
        ):
            return
        for key in BROWSER_SETTING_KEYS:
            self.settings.data[key] = DEFAULT_SETTINGS[key]
        self.settings.save()
        for slot in self.tasks.values():
            worker = slot.worker
            if worker and worker.is_alive():
                worker.settings = dict(self.settings.data)
                worker.control_queue.put(("settings", {"settings": dict(self.settings.data)}))
        self.refresh_browser_settings_widgets()
        self.log_ui("Browser settings reset to source defaults.")
        _message(self, "Browser Settings", "Browser settings reset to defaults.")

    def refresh_workflow_input_widgets(self) -> None:
        """Render the exact persisted values for the dedicated workflow form inputs."""
        for key in WORKFLOW_INPUT_KEYS:
            widget = self.workflow_input_widgets.get(key)
            if widget is None:
                continue
            value = self.settings.get(key, DEFAULT_SETTINGS[key])
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))

    def save_workflow_inputs(self) -> None:
        previous_values = {
            key: self.settings.get(key, DEFAULT_SETTINGS[key]) for key in WORKFLOW_INPUT_KEYS
        }
        try:
            parsed_settings: dict[str, Any] = {}
            for key in WORKFLOW_INPUT_KEYS:
                widget = self.workflow_input_widgets.get(key)
                if widget is None:
                    raise RuntimeError(f"Workflow input widget is unavailable: {key}")
                parsed_settings[key] = self.parse_setting_value(
                    key, self._widget_value(key, widget)
                )

            self.settings.data.update(parsed_settings)
            try:
                self.settings.save()
            except Exception:
                # A failed settings write must not make unsaved Workflow Inputs
                # authoritative in memory. Restore the exact pre-save values so
                # this page remains consistent with the persisted settings state.
                self.settings.data.update(previous_values)
                self.refresh_workflow_input_widgets()
                raise

            self.refresh_workflow_input_widgets()
            self.log_ui("Workflow Inputs saved.")
            _message(
                self,
                "Workflow Inputs",
                "Workflow Inputs saved successfully. Existing setting keys and saved-value compatibility are preserved.",
            )
        except Exception as exc:
            _message(self, "Workflow Inputs error", str(exc), "error")

    def reset_workflow_inputs(self) -> None:
        if not _confirm(
            self,
            "Reset Workflow Inputs",
            "Reset only Workflow Inputs to source defaults? App Settings and Browser Settings will be preserved.",
        ):
            return
        previous_values = {
            key: self.settings.get(key, DEFAULT_SETTINGS[key]) for key in WORKFLOW_INPUT_KEYS
        }
        try:
            for key in WORKFLOW_INPUT_KEYS:
                self.settings.data[key] = DEFAULT_SETTINGS[key]
            try:
                self.settings.save()
            except Exception:
                # Reset is transactional at the UI ownership boundary: if the
                # existing SettingsManager cannot persist, keep the prior values
                # in memory and surface the error instead of leaking it to Qt.
                self.settings.data.update(previous_values)
                self.refresh_workflow_input_widgets()
                raise

            self.refresh_workflow_input_widgets()
            self.log_ui("Workflow Inputs reset to source defaults.")
            _message(
                self,
                "Workflow Inputs",
                "Workflow Inputs reset to defaults. App Settings and Browser Settings were preserved.",
            )
        except Exception as exc:
            _message(self, "Workflow Inputs error", str(exc), "error")

    def save_settings(self) -> None:
        try:
            parsed_settings: dict[str, Any] = {}
            for key, widget in self.setting_widgets.items():
                value = self._widget_value(key, widget)
                if key == "theme_mode":
                    value = "Dark"
                parsed_settings[key] = self.parse_setting_value(key, value)

            if {"retry_delay_min", "retry_delay_max"}.issubset(parsed_settings):
                if parsed_settings["retry_delay_max"] < parsed_settings["retry_delay_min"]:
                    raise ValueError("Retry Delay Max cannot be lower than Retry Delay Min.")
            if {"delay_between_items_min", "delay_between_items_max"}.issubset(parsed_settings):
                if parsed_settings["delay_between_items_max"] < parsed_settings["delay_between_items_min"]:
                    raise ValueError("Delay Between Items Max cannot be lower than Delay Between Items Min.")

            self.settings.data.update(parsed_settings)
            self.settings.save()
            logging.getLogger().setLevel(
                getattr(logging, str(self.settings.get("log_level", DEFAULT_SETTINGS["log_level"])).upper(), logging.INFO)
            )
            self.log_ui("App Settings saved and applied.")
            _message(
                self,
                "App Settings",
                "App Settings saved successfully. The Default Target URL applies only to newly created tasks; advanced browser controls are managed from Browser Settings.",
            )
        except Exception as exc:
            _message(self, "App Settings error", str(exc), "error")

    def reset_settings(self) -> None:
        if not _confirm(self, "Reset App Settings", "Reset only App Settings to source defaults?"):
            return
        for key, widget in self.setting_widgets.items():
            self.settings.data[key] = DEFAULT_SETTINGS[key]
            value = DEFAULT_SETTINGS[key]
            if isinstance(widget, ToggleSwitch):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))
        self.settings.save()
        logging.getLogger().setLevel(
            getattr(
                logging,
                str(self.settings.get("log_level", DEFAULT_SETTINGS["log_level"])).upper(),
                logging.INFO,
            )
        )
        _message(
            self,
            "App Settings",
            "App Settings reset to source defaults. Browser Settings were preserved.",
        )

    # ---------- report ----------

    def _selected_report_slot(self) -> int | None:
        if not hasattr(self, "report_task"):
            return None
        text = self.report_task.currentText()
        if text.startswith("Task "):
            try:
                return int(text.split(" ", 1)[1])
            except ValueError:
                return None
        return None

    def add_report_row(self, row: dict[str, Any]) -> None:
        # Worker-side runtime storage is authoritative. Processing-start events stay
        # in Live Logs; Reports expose one latest outcome per recipient/run item.
        # Multiple worker results received in one UI tick are coalesced into one
        # bounded table refresh instead of rebuilding up to 1000 rows per event.
        if str(row.get("status", "")) == "processing":
            return
        self._report_dirty = True

    def refresh_report_table(self) -> None:
        if not hasattr(self, "report_table"):
            return
        status_filter = self.report_status.currentText() if hasattr(self, "report_status") else "All"
        search = self.report_search.text().lower() if hasattr(self, "report_search") else ""
        filtered = self.runtime_store.results(
            slot_id=self._selected_report_slot(),
            status=status_filter,
            search=search,
            limit=REPORT_RECENT_LIMIT,
        )
        self.report_rows = filtered
        self.report_table.setRowCount(len(filtered))
        for r, row in enumerate(filtered):
            for c, key in enumerate(self.report_columns):
                item = QTableWidgetItem(str(row.get(key, "")))
                item.setToolTip(str(row.get(key, "")))
                self.report_table.setItem(r, c, item)
        self.report_table.resizeRowsToContents()

    def _report_export_rows(self) -> list[dict[str, Any]]:
        status_filter = self.report_status.currentText() if hasattr(self, "report_status") else "All"
        search = self.report_search.text().lower() if hasattr(self, "report_search") else ""
        return self.runtime_store.results(
            slot_id=self._selected_report_slot(),
            status=status_filter,
            search=search,
            limit=None,
        )

    def export_report_csv(self) -> None:
        rows = self._report_export_rows()
        if not rows:
            _message(self, "Report", "No report rows to export.")
            return
        path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export_report_csv(rows, path)
        self.log_ui(f"Report exported: {path.name}")
        if self.settings.get("auto_open_report_after_export", DEFAULT_SETTINGS["auto_open_report_after_export"]):
            self.open_path(path)

    def export_report_excel(self) -> None:
        rows = self._report_export_rows()
        if not rows:
            _message(self, "Report", "No report rows to export.")
            return
        path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_report_excel(rows, path)
        self.log_ui(f"Excel report exported: {path.name}")
        if self.settings.get("auto_open_report_after_export", DEFAULT_SETTINGS["auto_open_report_after_export"]):
            self.open_path(path)

    def clear_report(self) -> None:
        if _confirm(self, "Clear report", "Clear live report data?"):
            self.runtime_store.clear_results()
            self.report_rows.clear()
            self.refresh_report_table()
            self.log_ui("Live report cleared.")

    # ---------- logs ----------

    def log_ui(self, message: str, level: str = "INFO") -> None:
        row = {"timestamp": now_str(), "level": level, "message": message}
        self.log_lines.append(row)
        logging.log(getattr(logging, level, logging.INFO), message)
        if hasattr(self, "log_text"):
            self.log_text.append(f"[{row['timestamp']}] [{level}] {message}")
            if hasattr(self, "autoscroll") and self.autoscroll.isChecked():
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.log_text.setTextCursor(cursor)

    def clear_logs(self) -> None:
        if hasattr(self, "log_text"):
            self.log_text.clear()
        self.log_lines.clear()

    def save_logs(self) -> None:
        path = LOGS_DIR / f"manual_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path.write_text(
            "\n".join(
                f"[{r['timestamp']}] [{r['level']}] {r['message']}"
                for r in self.log_lines
            ),
            encoding="utf-8",
        )
        self.log_ui(f"Logs saved: {path.name}")

    # ---------- worker event bridge ----------

    def _handle_browser_file_chooser(self, slot: TaskSlotWidget, payload: dict[str, Any]) -> None:
        """Collect explicit user file selection for a site-triggered chooser."""
        worker = slot.worker
        request_id = str(payload.get("request_id", ""))
        if not request_id or worker is None or not worker.is_alive():
            return
        directory = bool(payload.get("directory", False))
        multiple = bool(payload.get("multiple", False))
        selected: list[str] = []
        if directory:
            path = QFileDialog.getExistingDirectory(
                self,
                f"Task {slot.slot_id} — Select Upload Directory",
            )
            if path:
                selected = [path]
        elif multiple:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                f"Task {slot.slot_id} — Select Files to Upload",
            )
            selected = list(paths)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                f"Task {slot.slot_id} — Select File to Upload",
            )
            if path:
                selected = [path]
        worker.request_file_chooser_selection(
            request_id, selected, cancelled=not selected
        )

    def _render_download_event(self, slot_id: int, payload: dict[str, Any]) -> None:
        status = str(payload.get("status", "")).strip().lower()
        filename = str(payload.get("filename", "download"))
        if status == "started":
            self.log_ui(f"Task {slot_id}: browser download started: {filename}")
        elif status == "saved":
            self.log_ui(f"Task {slot_id}: browser download saved: {filename}")
        else:
            message = str(payload.get("message", "Download could not be saved."))
            self.log_ui(
                f"Task {slot_id}: browser download failed: {filename} — {message}",
                "ERROR",
            )

    def poll_queue(self) -> None:
        processed = 0
        while processed < UI_QUEUE_MAX_EVENTS_PER_TICK:
            try:
                kind, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            processed += 1
            slot_id = int(payload.get("slot_id", 0))
            slot = self.tasks.get(slot_id)

            if kind == "activation_result":
                activation_page = self.activation_page
                if activation_page is not None and not self._workspace_active:
                    activation_page.finish(bool(payload.get("ok")), str(payload.get("message", "")))
            elif kind == "log":
                self.log_ui(
                    f"Task {slot_id}: {payload.get('message')}",
                    str(payload.get("level", "INFO")),
                )
            elif kind == "progress" and slot:
                slot.update_counts(payload)
            elif kind == "status" and slot:
                slot.set_status(str(payload.get("status", "")))
            elif kind == "item":
                self.add_report_row(payload)
            elif kind == "security":
                _message(self, "Security challenge", str(payload.get("message", "Security challenge detected.")), "warning")
            elif kind == "browser" and slot:
                slot.set_browser_status(str(payload.get("status", "Closed")))
            elif kind == "login" and slot:
                slot.set_login_status(bool(payload.get("verified", False)), str(payload.get("message", "")))
            elif kind == "send_limit" and slot:
                slot.update_send_limit(int(payload.get("used", 0)), int(payload.get("limit", 1)))
            elif kind == "download":
                self._render_download_event(slot_id, payload)
            elif kind == "browser_file_chooser" and slot:
                self._handle_browser_file_chooser(slot, payload)
            elif kind == "done":
                pass
            elif kind == "license_invalid":
                self._pending_license_invalid_message = str(
                    payload.get("message", "License validation failed.")
                )
                for task in list(self.tasks.values()):
                    task.close_browser(wait=False)
                # Do not discard Task/Worker references while browser cleanup is still
                # running. The login transition is finalized asynchronously after every
                # worker thread has actually exited.
                QTimer.singleShot(0, self._finalize_license_invalid_transition)
        if self._report_dirty:
            self._report_dirty = False
            self.refresh_report_table()
        if processed:
            self.update_dashboard()

    def _finalize_license_invalid_transition(self) -> None:
        if self._pending_license_invalid_message is None:
            return
        waiting = False
        for task in list(self.tasks.values()):
            worker = task.worker
            if worker is None:
                continue
            if worker.is_alive():
                waiting = True
                continue
            task.close_browser(wait=False)
        if waiting:
            QTimer.singleShot(200, self._finalize_license_invalid_transition)
            return
        message = self._pending_license_invalid_message
        self._pending_license_invalid_message = None
        self.save_workspace_state()
        self.tasks.clear()
        _message(self, "License invalid", message, "error")
        self.show_login()

    def update_dashboard(self) -> None:
        tasks = [self.tasks[key] for key in sorted(self.tasks)]
        task_count = len(tasks)
        running = sum(1 for task in tasks if task.is_running())
        complete = sum(task.state.success_count for task in tasks)
        failed = sum(task.state.failed_count for task in tasks)
        values = {
            "Browser Slots": task_count,
            "Running": running,
            "Complete": complete,
            "Failed": failed,
        }

        browsers_ready = sum(1 for task in tasks if task.is_browser_open())
        login_verified = sum(1 for task in tasks if task.is_login_verified())
        tasks_with_data = sum(1 for task in tasks if task.state.total > 0)
        ready_to_start = sum(
            1
            for task in tasks
            if task.is_browser_open()
            and task.is_login_verified()
            and task.state.total > 0
            and task.state.remaining > 0
            and not task.is_running()
        )

        processed = sum(max(0, int(task.state.current_index)) for task in tasks)
        successful = sum(max(0, int(task.state.success_count)) for task in tasks)
        session_failed = sum(max(0, int(task.state.failed_count)) for task in tasks)
        remaining = sum(max(0, int(task.state.remaining)) for task in tasks)

        license_active = self.license_manager.is_activated()
        expiry_raw = self.license_manager.activated_until
        expiry_text = "Not provided"
        if expiry_raw:
            expiry_text = str(expiry_raw)
            raw_date = str(expiry_raw)[:10]
            try:
                expiry_text = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d %b %Y")
            except (TypeError, ValueError):
                pass

        task_limit = safe_test_send_limit(
            self.settings.get("max_test_send_limit", DEFAULT_SETTINGS["max_test_send_limit"])
        )
        usage_used = 0
        usage_capacity = 0
        for task in tasks:
            worker = task.worker
            if worker is not None:
                worker_limit = max(0, int(getattr(worker, "run_send_limit", task_limit)))
                worker_used = max(0, int(getattr(worker, "run_send_count", 0)))
            else:
                worker_limit = task_limit
                worker_used = max(0, int(task.state.send_limit_used))
            usage_capacity += worker_limit
            usage_used += min(worker_used, worker_limit)
        usage_available = max(0, usage_capacity - usage_used)

        details = {
            "Browsers Ready": f"{browsers_ready} / {task_count}",
            "Login Verified": f"{login_verified} / {task_count}",
            "Tasks with Data": f"{tasks_with_data} / {task_count}",
            "Ready to Start": str(ready_to_start),
            "Processed": str(processed),
            "Successful": str(successful),
            "Session Failed": str(session_failed),
            "Remaining": str(remaining),
            "License Status": "Active" if license_active else "Inactive",
            "License Expires": expiry_text,
            "Device Status": "Authorized" if license_active else "Not authorized",
            "Current Usage": f"{usage_used} / {usage_capacity}",
            "Available": str(usage_available),
            "Task Limit": f"{task_limit} per task",
        }

        next_action: tuple[str, int | None] = ("tasks", None)
        next_message = "Review your tasks to continue."
        next_button = "View Tasks"
        if not tasks:
            next_action = ("add", None)
            next_message = "No tasks yet. Create a task to get started."
            next_button = "Add Task"
        else:
            selected = next((task for task in tasks if not task.is_browser_open()), None)
            if selected is not None:
                next_action = ("tasks", selected.slot_id)
                next_message = f"Task {selected.slot_id} needs a browser session."
                next_button = f"Go to Task {selected.slot_id}"
            else:
                selected = next((task for task in tasks if not task.is_login_verified()), None)
                if selected is not None:
                    next_action = ("tasks", selected.slot_id)
                    next_message = f"Task {selected.slot_id} needs browser login verification."
                    next_button = f"Go to Task {selected.slot_id}"
                else:
                    selected = next((task for task in tasks if task.state.total <= 0), None)
                    if selected is not None:
                        next_action = ("tasks", selected.slot_id)
                        next_message = f"Upload data to Task {selected.slot_id} to continue."
                        next_button = f"Go to Task {selected.slot_id}"
                    else:
                        selected = next(
                            (
                                task
                                for task in tasks
                                if not task.is_running() and task.state.remaining > 0
                            ),
                            None,
                        )
                        if selected is not None:
                            next_action = ("tasks", selected.slot_id)
                            next_message = f"Task {selected.slot_id} is ready to start."
                            next_button = f"Go to Task {selected.slot_id}"
                        else:
                            selected = next((task for task in tasks if task.is_running()), None)
                            if selected is not None:
                                next_action = ("tasks", selected.slot_id)
                                next_message = f"Task {selected.slot_id} is currently running."
                                next_button = f"View Task {selected.slot_id}"
                            elif all(task.state.total > 0 and task.state.remaining == 0 for task in tasks):
                                next_message = "All loaded tasks are complete."

        if self._workspace_active or self._workspace_transitioning:
            for key, value in values.items():
                widget = self.dashboard_metrics.get(key)
                if widget is not None:
                    widget.setText(str(value))
            for key, value in details.items():
                widget = self.dashboard_details.get(key)
                if widget is not None:
                    widget.setText(value)
                    widget.setAccessibleName(f"{key}: {value}")
                    widget.updateGeometry()
            self.dashboard_next_action = next_action
            if self.dashboard_next_message is not None:
                self.dashboard_next_message.setText(next_message)
            if self.dashboard_next_button is not None:
                self.dashboard_next_button.setText(next_button)
            if self.license_badge is not None:
                self.license_badge.setText("Licensed" if license_active else "Unlicensed")

    # ---------- license / shutdown ----------

    def logout(self) -> None:
        if any(t.is_running() for t in self.tasks.values()):
            _message(self, "Running tasks", "Stop running tasks before logging out.", "warning")
            return
        blocked: list[int] = []
        for task in list(self.tasks.values()):
            if not task.close_browser(wait=True):
                blocked.append(task.slot_id)
        if blocked:
            _message(
                self,
                "Workers still closing",
                "These task workers are still completing browser cleanup: "
                + ", ".join(str(value) for value in blocked)
                + ". Logout was cancelled to avoid orphaning live workers.",
                "warning",
            )
            return
        self.save_workspace_state()
        self.tasks.clear()
        self.license_manager.logout()
        self.show_login()

    def start_license_recheck(self) -> None:
        def loop() -> None:
            while not self.license_stop.is_set():
                minutes = max(1, int(self.settings.get("license_recheck_minutes", DEFAULT_SETTINGS["license_recheck_minutes"])))
                for _ in range(minutes * 60):
                    if self.license_stop.is_set():
                        return
                    time.sleep(1)
                if self.license_manager.license_key:
                    ok, msg = self.license_manager.validate(
                        self.license_manager.license_key,
                        self.license_manager.user_email,
                    )
                    validation_code = str(
                        getattr(self.license_manager, "_last_validation_code", "")
                    )
                    still_locally_valid = self.license_manager.is_activated()
                    transient_with_valid_token = (
                        not ok
                        and still_locally_valid
                        and license_validation_failure_is_transient(validation_code)
                    )
                    self.ui_queue.put(
                        (
                            "log",
                            {
                                "slot_id": 0,
                                "message": f"Background license re-check: {msg}",
                                "level": (
                                    "WARNING"
                                    if transient_with_valid_token
                                    else ("INFO" if ok else "ERROR")
                                ),
                            },
                        )
                    )
                    if transient_with_valid_token:
                        # A temporary network/rate-limit/server-response failure is
                        # not authoritative while the locally verified access token
                        # is still valid. Keep the session and retry next interval.
                        continue
                    if not ok:
                        self.license_manager.logout()
                        self.ui_queue.put(
                            (
                                "license_invalid",
                                {
                                    "slot_id": 0,
                                    "message": "License re-validation failed. The session was closed.",
                                },
                            )
                        )

        threading.Thread(target=loop, daemon=True).start()

    def open_path(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            logging.exception("Failed to open path")

    def _apply_responsive_mode(self) -> None:
        breadcrumb = self.breadcrumb
        window_title_label = self.window_title_label
        responsive_badge = self.responsive_badge
        if breadcrumb is None or window_title_label is None:
            return
        width = self.width()
        compact = width < CONST.compact_breakpoint
        wide = width >= CONST.large_breakpoint
        breadcrumb.setVisible(not compact)
        window_title_label.setText(APP.display_name if compact else DISPLAY_APP_NAME)
        mode = "Compact" if compact else ("Wide" if wide else "Medium")
        if responsive_badge is not None:
            responsive_badge.setText(mode)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        if self._workspace_active or self._workspace_transitioning:
            self._apply_responsive_mode()
        super().resizeEvent(event)
        self.schedule_workspace_save()

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self.schedule_workspace_save()

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        running = [t for t in self.tasks.values() if t.is_running()]
        if running and self.settings.get("confirm_before_close_while_running", DEFAULT_SETTINGS["confirm_before_close_while_running"]):
            if not _confirm(
                self,
                "Processing is still running",
                "Processing is still running. Unprocessed data from every running task "
                "will be saved before exit. Do you want to close the app?",
            ):
                event.ignore()
                return
        blocked: list[int] = []
        for task in list(self.tasks.values()):
            if task.worker and task.worker.is_processing():
                task.stop_event.set()
                task.pause_event.clear()
            if not task.close_browser(wait=True):
                blocked.append(task.slot_id)
        if blocked:
            _message(
                self,
                "Workers still closing",
                "These task workers are still completing browser cleanup: "
                + ", ".join(str(value) for value in blocked)
                + ". The app was kept open to avoid orphaning live workers.",
                "warning",
            )
            event.ignore()
            return
        self.save_workspace_state()
        self.license_stop.set()
        self.runtime_store.close()
        self.log_ui("App closing. All task workers and browser sessions stopped cleanly.")
        event.accept()


def main() -> int:
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"VibTools.{APP.app_name}.{APP_VERSION}"
            )
        except Exception:
            logging.debug("Windows AppUserModelID could not be set", exc_info=True)
    application = QApplication(sys.argv)
    application.setApplicationName(DISPLAY_APP_NAME)
    application.setApplicationDisplayName(DISPLAY_APP_NAME)
    application.setOrganizationName(APP.company_name)
    application.setOrganizationDomain(APP.organization_domain)
    application.setWindowIcon(application_icon())
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
