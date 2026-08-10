"""VibraPilot ‚Äî Vib Tools official desktop UI edition.

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
    WorkflowError,
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


NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]
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
 'Downloads': ['accept_downloads', 'downloads_path'], 'Network & Proxy': ['proxy_server', 'proxy_username', 'proxy_password', 'proxy_bypass'], 'Cookies & Storage': ['cookies_enabled',
                          'partitioned_cookies',
                           'third_party_cookies',
                           'http_cache_enabled',
                           'cache_directory',
                            'clear_cache_on_browser_close',
                            'clear_cookies_on_browser_close'], 'Images & Media': ['images_enabled',
                       'image_load_strategy',
                       'media_autoplay_enabled',
                       'media_controls_enabled'], 'Extensions': ['extensions_enabled',
                    'extension_paths'], 'Page Navigation': ['navigation_timeout',
                        'wait_until',
                        'page_load_strategy',
                        'netwo◊æ|˜ß!jª-ÆÈ‹j◊ù