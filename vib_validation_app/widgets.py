"""Compact internal widgets for Step-40J auth breathing-gap repair.

All reusable cards, badges, form controls, tables, toggles, dialogs and drop
zones consume ``tokens.CONST`` and ``tokens.COLORS`` so page implementations do
not repeat per-component style or density rules. Step-40C preserves the
Step-39B/Step-40 app baseline, keeps Step-40B readable text/card/form gaps,
and prevents wrapped labels/descriptions from vertically stretching inside
full-page cards without increasing approved control heights.
"""
from __future__ import annotations

from typing import Callable, Iterable, Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QDate, QTime, QSize
from PySide6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QStyle,
    QStyleOptionFocusRect,
    QTextEdit,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .tokens import COLORS, TYPE, CONST
from .button_contract import VibButton, apply_button_contract

ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"

STATE_CONTRACT_PROPERTY = "step-39b-responsive-breakage-repair-state-contract"
ACCESSIBILITY_CONTRACT_PROPERTY = "step-36-accessibility-contract-preserved"


def _clean_accessible_text(text: str) -> str:
    return " ".join(str(text).replace("&", "").split())


def apply_accessibility(widget: QWidget, name: str, description: str = "") -> QWidget:
    """Attach preserved Step-36 accessible metadata without changing visual geometry."""
    clean = _clean_accessible_text(name) or widget.objectName() or widget.__class__.__name__
    widget.setProperty("vibAccessibilityContract", ACCESSIBILITY_CONTRACT_PROPERTY)
    widget.setAccessibleName(clean)
    if description:
        widget.setAccessibleDescription(description)
    if not widget.toolTip():
        widget.setToolTip(clean)
    return widget


def apply_state_contract(widget: QWidget, role: str) -> QWidget:
    """Attach a central design-state marker without changing geometry.

    Step-38 uses this marker to verify that page-level controls use the shared
    responsive-safe interactive contract instead of undocumented per-page styling,
    clipping-prone layouts or accessibility gaps.
    """
    widget.setProperty("vibDesignStep", "step-39b")
    widget.setProperty("vibStateContract", STATE_CONTRACT_PROPERTY)
    widget.setProperty("vibComponentRole", role)
    return widget



def rgba_from_hex(hex_color: str, alpha: float) -> str:
    h = hex_color.strip().lstrip("#")
    if len(h) != 6:
        return hex_color
    a = max(0, min(255, int(round(alpha * 255))))
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def icon(name: str) -> QIcon:
    """Return a compact vector icon, falling back to native Qt standard icons.

    Step-31 replaces emoji-like search/password/file-tree symbols with local
    SVG icons so form controls and file hierarchy render consistently on
    Windows without color emoji glyph fallback.
    """
    svg_map = {
        "search": "search.svg",
        "eye": "eye.svg",
        "eye_off": "eye-off.svg",
        "folder": "folder.svg",
        "file": "file.svg",
        "chevron_right": "chevron-right.svg",
        "chevron_down": "chevron-down.svg",
    }
    svg_name = svg_map.get(name)
    if svg_name:
        path = ICON_DIR / svg_name
        if path.exists():
            return QIcon(str(path))

    style = QApplication.instance().style() if QApplication.instance() else None
    if not style:
        return QIcon()
    mapping = {
        "home": QStyle.SP_ComputerIcon,
        "settings": QStyle.SP_FileDialogDetailedView,
        "help": QStyle.SP_DialogHelpButton,
        "info": QStyle.SP_MessageBoxInformation,
        "warning": QStyle.SP_MessageBoxWarning,
        "error": QStyle.SP_MessageBoxCritical,
        "success": QStyle.SP_DialogApplyButton,
        "refresh": QStyle.SP_BrowserReload,
        "open": QStyle.SP_DialogOpenButton,
        "save": QStyle.SP_DialogSaveButton,
        "delete": QStyle.SP_TrashIcon,
        "close": QStyle.SP_DialogCloseButton,
    }
    return style.standardIcon(mapping.get(name, QStyle.SP_FileIcon))


def vbox(parent: QWidget | None = None, margins=(0, 0, 0, 0), spacing: int = 12) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def hbox(parent: QWidget | None = None, margins=(0, 0, 0, 0), spacing: int = 6) -> QHBoxLayout:
    layout = QHBoxLayout(parent)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout




class ResponsiveGrid(QWidget):
    """Flat responsive grid for frozen desktop layouts.

    Step-39B keeps parent-responsive width and makes the compact grid reduction
    visible by using the strengthened CONST.content_gap and min-card width. Column count may reflow; colors, control heights and
    page features remain unchanged.
    """

    def __init__(self, items: Sequence[QWidget], max_columns: int = 3, min_item_width: int | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ResponsiveGrid")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._items = list(items)
        self._max_columns = max(1, max_columns)
        self._min_item_width = min_item_width or CONST.responsive_card_min_width
        self._columns = 0
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(CONST.content_gap)
        self._layout.setVerticalSpacing(CONST.content_gap)
        for item in self._items:
            item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._reflow(force=True)

    def _target_columns(self) -> int:
        width = max(1, self.width())
        # Account for compact Step-25 gutters between columns.
        cols = max(1, (width + CONST.content_gap) // (self._min_item_width + CONST.content_gap))
        return int(max(1, min(self._max_columns, cols)))

    def _reflow(self, force: bool = False) -> None:
        columns = self._target_columns()
        if not force and columns == self._columns:
            return
        self._columns = columns
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for i, item in enumerate(self._items):
            self._layout.addWidget(item, i // columns, i % columns)
        for col in range(columns):
            self._layout.setColumnStretch(col, 1)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._reflow()
        super().resizeEvent(event)



class ElideLabel(QLabel):
    """Single-line QLabel that applies Qt.ElideRight and keeps a full-text tooltip.

    Tables, file/canvas labels and compact metadata must not wrap because the
    frozen row heights are fixed. This widget updates its displayed text on
    resize while preserving the full value in ``toolTip``.
    """

    def __init__(self, text: str = "", object_name: str = "Description", parent: QWidget | None = None):
        super().__init__(parent)
        self._full_text = str(text)
        self._elide_mode = Qt.ElideRight
        self.setObjectName(object_name)
        self.setWordWrap(False)
        self.setMinimumWidth(0)
        # Step-39B: QLabel minimumSizeHint from long text was forcing page widgets
        # wider than the viewport, creating horizontal scroll and clipped cards/tables.
        # Ignored horizontal policy lets layouts allocate available width while
        # ElideRight + tooltip preserve the full value.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setToolTip(self._full_text)
        apply_accessibility(self, self._full_text, "Single-line truncated text. Full value is available as tooltip.")
        super().setText(self._full_text)

    def full_text(self) -> str:
        return self._full_text

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = str(text)
        self.setToolTip(self._full_text)
        self.setAccessibleName(self._full_text)
        self._sync_elided_text()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._sync_elided_text()
        super().resizeEvent(event)

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._sync_elided_text()
        super().showEvent(event)

    def _sync_elided_text(self) -> None:
        width = max(0, self.contentsRect().width())
        if width <= 0:
            super().setText(self._full_text)
            return
        metrics = self.fontMetrics()
        super().setText(metrics.elidedText(self._full_text, self._elide_mode, width))


def elide_label(text: str, object_name: str = "Description") -> ElideLabel:
    return ElideLabel(text, object_name)


def apply_responsive_text_guard(widget: QLabel, text: str | None = None, role: str = "text") -> QLabel:
    """Mark text as Step-38 safe without changing font size or geometry.

The guard keeps fixed-height zones from wrapping under 125%/150% DPI. The full
string remains available through the tooltip and accessible name.
    """
    full_text = str(text if text is not None else widget.text())
    widget.setProperty("vibResponsiveContract", "step-38-high-dpi-responsive-certification")
    widget.setProperty("vibResponsiveRole", role)
    widget.setMinimumWidth(0)
    widget.setToolTip(full_text)
    widget.setAccessibleName(full_text)
    return widget


def constrain_widget_to_available_screen(widget: QWidget, margin: int | None = None) -> None:
    """Keep dialogs/popups within the current screen without enlarging them."""
    app = QApplication.instance()
    screen = widget.screen() or (app.primaryScreen() if app else None)
    if not screen:
        return
    safe_margin = CONST.responsive_dialog_margin if margin is None else margin
    available = screen.availableGeometry().adjusted(safe_margin, safe_margin, -safe_margin, -safe_margin)
    widget.adjustSize()
    if widget.width() > available.width():
        widget.resize(available.width(), widget.height())
    if widget.height() > available.height():
        widget.resize(widget.width(), available.height())
    geo = widget.frameGeometry()
    x = min(max(geo.x(), available.left()), max(available.left(), available.right() - geo.width()))
    y = min(max(geo.y(), available.top()), max(available.top(), available.bottom() - geo.height()))
    widget.move(x, y)


def label(text: str, object_name: str = "Description", word_wrap: bool = True) -> QLabel:
    w = QLabel(text)
    w.setObjectName(object_name)
    w.setWordWrap(word_wrap)
    w.setMinimumWidth(0)
    # Step-40C: word-wrapped descriptions must not create a viewport-wide
    # minimumSizeHint or vertically stretch inside full-page cards. Maximum
    # vertical policy keeps title/description stacks tight while still allowing
    # the label to take its natural wrapped height.
    w.setSizePolicy(QSizePolicy.Ignored if word_wrap else QSizePolicy.Expanding, QSizePolicy.Maximum if word_wrap else QSizePolicy.Fixed)
    apply_accessibility(w, text, "Static text label.")
    if not word_wrap:
        apply_responsive_text_guard(w, text, object_name)
    return w


def title(text: str, level: str = "PageTitle") -> QLabel:
    return label(text, level, False)


def button(text: str, kind: str = "secondary", icon_name: str | None = None) -> QPushButton:
    """Create every page/card/hero/form button through one frozen component.

    Step 13 removes page-specific button construction.  This factory delegates
    to VibButton + apply_button_contract(), so 28px height, compact padding/gaps,
    hover/active/focus/disabled, icon sizing, auto-default disabling and content-based width are centralized.
    """
    icon_obj = icon(icon_name) if icon_name else None
    b = VibButton(text, kind, icon_obj)
    if kind == "icon" and icon_obj is None:
        apply_button_contract(b, kind, icon_obj=icon("settings"), tooltip=text)
    return b


def card(title_text: str | None = None, description: str | None = None, nested: bool = False) -> QFrame:
    """Readable compact flat container: token padding, header/content spacing, 8px radius.

    Height is content-driven; no fixed 92px/96px card minimum is applied.
    Step-40C preserves readable title/subtitle/header/content breathing and
    prevents labels/descriptions from vertically stretching inside full-page cards.
    """
    f = QFrame()
    f.setObjectName("NestedCard" if nested else "Card")
    apply_state_contract(f, "card")
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    lay = vbox(f, margins=(CONST.card_padding, CONST.card_padding, CONST.card_padding, CONST.card_padding), spacing=CONST.card_header_content_gap)
    if title_text or description:
        header = QWidget()
        header.setObjectName("CardHeader")
        header_lay = vbox(header, spacing=CONST.card_header_gap)
        if title_text:
            header_lay.addWidget(title(title_text, "CardTitle"))
        if description:
            header_lay.addWidget(label(description, "Description"))
        lay.addWidget(header)
    return f


def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("Divider")
    f.setFrameShape(QFrame.HLine)
    return f


def metric_card(name: str, value: str, note: str = "") -> QFrame:
    f = QFrame()
    f.setObjectName("Metric")
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    lay = vbox(f, margins=(CONST.card_padding, CONST.card_padding - 3, CONST.card_padding, CONST.card_padding - 3), spacing=CONST.card_action_gap)
    lay.addWidget(elide_label(name, "Caption"))
    lay.addWidget(elide_label(value, "PageTitle"))
    if note:
        lay.addWidget(elide_label(note, "Caption"))
    return f


def status_badge(text: str, tone: str = "ready", *, weight: int = 600, object_name: str = "Caption") -> QLabel:
    """Compact semantic badge using token color without loud filled pills.

The frozen Identity/Feedback rules require flat, compact, professional badges
with semantic color only when status requires it. The hue comes from the
official token; the low-alpha surface prevents excessive color blocks against
the dark background while keeping readable text.
    """
    normalized = tone.strip().lower().replace("_", " ").replace("-", " ")
    color = {
        "ready": COLORS["success"],
        "success": COLORS["success"],
        "pass": COLORS["success"],
        "running": COLORS["primary"],
        "busy": COLORS["warning"],
        "warning": COLORS["warning"],
        "partial": COLORS["secondary_accent"],
        "needs review": COLORS["warning"],
        "review": COLORS["warning"],
        "user override": COLORS["warning"],
        "mismatch": COLORS["danger"],
        "error": COLORS["danger"],
        "offline": COLORS["disabled"],
        "info": COLORS["secondary_accent"],
    }.get(normalized, COLORS["secondary_accent"])
    lower_text = str(text).strip().lower()
    if object_name == "PluginCategoryChip":
        bg = COLORS.get("plugin_chip_background", rgba_from_hex(COLORS["secondary_accent"], 0.08))
        bd = COLORS.get("plugin_chip_border", bg)
        color = COLORS.get("plugin_chip_text", COLORS["secondary_text"])
        weight = 600
    elif normalized == "offline" or lower_text == "offline":
        bg = COLORS.get("status_badge_offline_bg", COLORS.get("badge_muted_background", rgba_from_hex(COLORS["secondary_text"], 0.12)))
        bd = COLORS.get("status_badge_offline_border", COLORS.get("badge_muted_border", rgba_from_hex(COLORS["secondary_text"], 0.24)))
        color = COLORS.get("status_badge_offline_text", COLORS.get("badge_muted_text", COLORS["secondary_text"]))
        weight = 600
    elif lower_text == "available":
        bg = COLORS.get("plugin_status_available_bg", COLORS.get("badge_muted_background", COLORS.get("plugin_chip_background", rgba_from_hex(COLORS["secondary_text"], 0.10))))
        bd = COLORS.get("plugin_status_available_border", COLORS.get("badge_muted_border", COLORS.get("plugin_chip_border", bg)))
        color = COLORS.get("plugin_status_available_text", COLORS.get("badge_muted_text", COLORS["secondary_text"]))
        weight = 600
    elif lower_text == "installed":
        bg = COLORS.get("plugin_status_installed_bg", rgba_from_hex(COLORS["success"], 0.12))
        bd = COLORS.get("plugin_status_installed_border", rgba_from_hex(COLORS["success"], 0.24))
        color = COLORS.get("plugin_status_installed_text", COLORS["success"])
        weight = 600
    else:
        bg = rgba_from_hex(color, 0.14)
        bd = rgba_from_hex(color, 0.30)
    w = QLabel(text)
    w.setObjectName(object_name)
    apply_state_contract(w, "badge")
    w.setWordWrap(False)
    w.setAlignment(Qt.AlignCenter)
    w.setToolTip(str(text))
    apply_accessibility(w, str(text), f"Status badge: {text}.")
    badge_line_height = CONST.badge_font_size + 4
    w.setStyleSheet(
        f"background:{bg}; color:{color}; border:1px solid {bd}; "
        f"border-radius:{CONST.badge_radius}px; "
        f"padding:{CONST.badge_padding_y}px {CONST.badge_padding_x}px; "
        f"font-size:{CONST.badge_font_size}px; font-weight:{weight}; "
        f"line-height:{badge_line_height}px;"
    )
    w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return w


def token_chip(text: str, object_name: str = "TokenChip") -> QLabel:
    w = QLabel(text)
    w.setObjectName(object_name)
    apply_state_contract(w, "token-chip")
    apply_accessibility(w, text, "Compact token chip.")
    w.setStyleSheet(
        f"background:{COLORS.get('badge_muted_background', COLORS['surface'])}; color:{COLORS.get('badge_muted_text', COLORS['secondary_text'])}; "
        f"border:1px solid {COLORS.get('badge_muted_border', COLORS['border'])}; border-radius:{CONST.badge_radius}px; "
        f"padding:{CONST.badge_padding_y + 1}px {CONST.badge_padding_x}px; font-size:{CONST.badge_font_size}px;"
    )
    w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return w


def page_frame() -> QWidget:
    w = QWidget()
    w.setObjectName("PageContent")
    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return w


def page_header(title_text: str, description: str = "", actions: Iterable[QWidget] | None = None) -> QFrame:
    """Content-driven page header. Decorative descriptions are optional.

    v1.0.6.34 keeps the existing title/action component contract but does not
    allocate a subtitle row when no description is supplied. Security, error
    and state text remains owned by the page body rather than this header.
    """
    f = QFrame()
    f.setObjectName("PageHeader")
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    lay = hbox(
        f,
        margins=(CONST.page_padding, CONST.page_header_padding_y, CONST.page_padding, CONST.page_header_padding_y),
        spacing=CONST.card_internal_gap,
    )
    text_col = QWidget()
    text_col.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    text_lay = vbox(text_col, spacing=CONST.page_header_text_gap)
    page_title = elide_label(title_text, "PageTitle")
    page_title.setToolTip(title_text)
    text_lay.addWidget(page_title)
    if description:
        desc = elide_label(description, "Description")
        desc.setToolTip(description)
        text_lay.addWidget(desc)
    lay.addWidget(text_col, 1, Qt.AlignVCenter)
    if actions:
        action_host = QWidget()
        action_host.setObjectName("HeroActions")
        action_lay = hbox(action_host, margins=(0, 0, 0, 0), spacing=CONST.action_gap)
        for w in actions:
            action_lay.addWidget(w)
        lay.addWidget(action_host, 0, Qt.AlignRight | Qt.AlignVCenter)
    return f


def form_group(label_text: str, field: QWidget, help_text: str = "", validation_text: str = "", validation_tone: str = "", *, spacing: int | None = None) -> QWidget:
    """Central label-above-input contract used by every form-like page.

    Step-40J keeps the frozen 32px field geometry and prevents helper/validation
    rows from visually colliding with inputs by using one explicit form-group
    spacing source.  Login can request the stricter 4px global form contract
    without changing the reusable field/button dimensions.
    """
    box = QWidget()
    box.setObjectName("GlobalFormGroup")
    box.setProperty("vibGlobalFormContract", "step-40i-global-form-contract")
    box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    lay = vbox(box, spacing=CONST.form_group_gap if spacing is None else spacing)
    lay.setSizeConstraint(QVBoxLayout.SetMinimumSize)
    form_label = elide_label(label_text, "FormLabel")
    form_label.setProperty("vibGlobalFormContract", "step-40i-global-form-contract")
    lay.addWidget(form_label)
    field.setProperty("vibGlobalFormContract", "step-40i-global-form-contract")
    field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    lay.addWidget(field)
    if help_text:
        help_label = elide_label(help_text, "HelpText")
        help_label.setProperty("vibGlobalFormContract", "step-40i-global-form-contract")
        lay.addWidget(help_label)
    if validation_text:
        msg = label(validation_text, "ValidationText")
        msg.setProperty("vibGlobalFormContract", "step-40i-global-form-contract")
        color = {
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "error": COLORS["danger"],
        }.get(validation_tone, COLORS["secondary_text"])
        msg.setStyleSheet(f"color:{color}; font-size:{TYPE['caption']}px;")
        lay.addWidget(msg)
    return box


def _apply_input_state(w: QLineEdit, state: str = "default") -> QLineEdit:
    """Apply frozen form state markers without page-level styles."""
    if state == "error":
        w.setObjectName("ErrorInput")
    elif state == "valid":
        w.setObjectName("ValidInput")
    elif state == "readonly":
        w.setObjectName("ReadOnlyInput")
        w.setReadOnly(True)
    elif state == "disabled":
        w.setEnabled(False)
    return w


def line_input(placeholder: str = "", text: str = "", state: str = "default") -> QLineEdit:
    w = QLineEdit()
    w.setProperty("vibFormField", "flat-v1")
    apply_state_contract(w, "input")
    w.setPlaceholderText(placeholder)
    apply_accessibility(w, placeholder or text or "Text input", "Text input field. Keyboard: type to edit; Tab moves to next control.")
    if text:
        w.setText(text)
    w.setMinimumHeight(CONST.input_height)
    w.setMaximumHeight(CONST.input_height)
    return _apply_input_state(w, state)


def search_input(placeholder: str = "Search...", text: str = "", state: str = "default") -> QLineEdit:
    """Frozen search field: 32px input with leading 16px search icon."""
    w = line_input(placeholder, text, state)
    if not w.objectName():
        w.setObjectName("SearchInput")
    w.setProperty("vibSearchInput", "leading-icon-v1")
    action = w.addAction(icon("search"), QLineEdit.LeadingPosition)
    action.setToolTip("Search")
    w.setAccessibleName(placeholder or "Search")
    w.setAccessibleDescription("Search input with leading search icon.")
    return w


def password_input(text: str = "") -> QLineEdit:
    """Frozen password field with trailing show/hide action."""
    w = line_input("Enter Password", text)
    if not w.objectName():
        w.setObjectName("PasswordInput")
    w.setProperty("vibPasswordInput", "show-hide-v1")
    w.setEchoMode(QLineEdit.Password)
    w.setAccessibleName("Password")
    w.setAccessibleDescription("Password input with show and hide control.")
    toggle_action = w.addAction(icon("eye"), QLineEdit.TrailingPosition)
    toggle_action.setToolTip("Show password")

    def _toggle_password_visibility() -> None:
        showing = w.echoMode() == QLineEdit.Normal
        w.setEchoMode(QLineEdit.Password if showing else QLineEdit.Normal)
        toggle_action.setIcon(icon("eye" if showing else "eye_off"))
        toggle_action.setToolTip("Show password" if showing else "Hide password")

    toggle_action.triggered.connect(_toggle_password_visibility)
    return w





def clear_action_tooltips(widget: QWidget) -> None:
    """Remove native hover overlays from embedded actions without changing accessibility."""
    for action in widget.actions():
        action.setToolTip("")
        action.setStatusTip("")
        action.setWhatsThis("")

def auth_login_options_row(stay_signed: QCheckBox, forgot: QPushButton) -> QWidget:
    """Central compact login options row.

    Step-40J keeps the 400px login card and approved 32px/28px controls, but
    locks the checkbox and forgot-link into a true space-between row. The row
    has zero internal margins, zero inter-item spacing, a 20px fixed height,
    and a stretch between the two controls so their left/right edges align with
    the input field without increasing card size.
    """
    host = QWidget()
    host.setObjectName("AuthOptionsRow")
    host.setProperty("vibGlobalFormContract", "step-40j-auth-options-row")
    host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    host.setMinimumHeight(CONST.form_login_options_row_height)
    host.setMaximumHeight(CONST.form_login_options_row_height)
    row = hbox(host, margins=(0, 0, 0, 0), spacing=0)
    row.setAlignment(Qt.AlignVCenter)
    stay_signed.setContentsMargins(0, 0, 0, 0)
    stay_signed.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    stay_signed.setMinimumHeight(CONST.form_login_options_row_height)
    stay_signed.setMaximumHeight(CONST.form_login_options_row_height)
    forgot.setContentsMargins(0, 0, 0, 0)
    forgot.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    forgot.setMinimumHeight(CONST.link_button_height)
    forgot.setMaximumHeight(CONST.link_button_height)
    row.addWidget(stay_signed, 0, Qt.AlignLeft | Qt.AlignVCenter)
    row.addStretch(1)
    row.addWidget(forgot, 0, Qt.AlignRight | Qt.AlignVCenter)
    return host


def auth_login_card(on_login: Callable[[], None] | None = None) -> QFrame:
    """Reusable Authentication/Login section built from the global form contract.

    This is the single construction point for the Login form so future pages do
    not duplicate Email/Password/options/action geometry. Step-40J preserves
    the existing 400px width, 14px card padding, 32px inputs, 28px primary
    action and flat focus states while enforcing exact options-row space-between
    alignment, 8px password/options breathing gap, 8px options/submit gap and
    unmounted auth hover overlays.
    """
    auth = card("Login", "400px card, 14px padding, global 4px field rhythm and no-clipping options row.")
    auth.setObjectName("AuthCard")
    auth.setProperty("vibGlobalFormContract", "step-40j-global-form-contract")
    auth.setFixedWidth(CONST.form_login_card_width)
    auth.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
    auth.layout().setSizeConstraint(QVBoxLayout.SetMinimumSize)
    auth.layout().setContentsMargins(
        CONST.form_login_card_padding,
        CONST.form_login_card_padding,
        CONST.form_login_card_padding,
        CONST.form_login_card_padding,
    )
    auth.layout().setSpacing(0)

    email_field = line_input("name@company.com", "admin@vibtools.com")
    email_field.setAccessibleName("Email")
    email_field.setAccessibleDescription("Login email input. Keyboard: type the email address; Tab moves to password.")
    if not CONST.form_login_tooltips_enabled:
        email_field.setToolTip("")
    auth.layout().addWidget(form_group("Email", email_field, spacing=CONST.form_login_field_gap))
    auth.layout().addSpacing(CONST.form_login_field_gap)

    password_field = password_input("demo-password")
    password_field.setAccessibleDescription("Password input with trailing show and hide action. No visible helper row is rendered below the field, preventing layout collision.")
    if not CONST.form_login_tooltips_enabled:
        password_field.setToolTip("")
        clear_action_tooltips(password_field)
    auth.layout().addWidget(form_group("Password", password_field, spacing=CONST.form_login_field_gap))
    auth.layout().addSpacing(CONST.form_login_password_options_gap)

    stay_signed = checkbox("Keep me signed in", True)
    stay_signed.setContentsMargins(0, 0, 0, 0)
    stay_signed.setAccessibleDescription("Keep me signed in option. Keyboard: Space toggles the checkbox.")
    if not CONST.form_login_tooltips_enabled:
        stay_signed.setToolTip("")

    forgot = button("Forgot Password", "link")
    forgot.setAccessibleDescription("Forgot password link action. Keyboard: Enter or Space activates.")
    if not CONST.form_login_tooltips_enabled:
        forgot.setToolTip("")
    auth.layout().addWidget(auth_login_options_row(stay_signed, forgot))
    auth.layout().addSpacing(CONST.form_login_action_top_gap)

    actions_host = QWidget()
    actions_host.setObjectName("AuthSubmitRow")
    actions_host.setProperty("vibGlobalFormContract", "step-40j-global-form-contract")
    actions_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    actions = hbox(actions_host, margins=(0, 0, 0, 0), spacing=0)
    actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    login = button("Login", "primary")
    login.setAccessibleDescription("Login primary action. Keyboard: Enter or Space activates.")
    if not CONST.form_login_tooltips_enabled:
        login.setToolTip("")
    if on_login is not None:
        login.clicked.connect(on_login)
    actions.addStretch(1)
    actions.addWidget(login, 0, Qt.AlignRight | Qt.AlignVCenter)
    auth.layout().addWidget(actions_host)
    return auth


def text_area(placeholder: str = "", text: str = "") -> QTextEdit:
    w = QTextEdit()
    apply_state_contract(w, "textarea")
    w.setPlaceholderText(placeholder)
    apply_accessibility(w, placeholder or text or "Text input", "Text input field. Keyboard: type to edit; Tab moves to next control.")
    if text:
        w.setPlainText(text)
    w.setMinimumHeight(84)
    w.setMaximumHeight(116)
    return w


def combo_box(items: Sequence[str], current: int = 0) -> QComboBox:
    w = QComboBox()
    apply_state_contract(w, "select")
    apply_accessibility(w, "Select option", "Combo box. Keyboard: Arrow keys change selection; Enter confirms.")
    w.addItems(list(items))
    if items:
        w.setCurrentIndex(max(0, min(current, len(items) - 1)))
    w.setMinimumHeight(CONST.input_height)
    w.setMaximumHeight(CONST.input_height)
    return w


def number_input(value: int = 1, low: int = 0, high: int = 9999) -> QSpinBox:
    w = QSpinBox()
    apply_state_contract(w, "number-input")
    apply_accessibility(w, "Number input", "Numeric input. Keyboard: Arrow keys adjust value.")
    w.setRange(low, high)
    w.setValue(value)
    w.setMinimumHeight(CONST.input_height)
    w.setMaximumHeight(CONST.input_height)
    return w


def date_input() -> QDateEdit:
    w = QDateEdit()
    apply_state_contract(w, "date-input")
    apply_accessibility(w, "Date input", "Date input. Keyboard: Arrow keys adjust date.")
    w.setDate(QDate.currentDate())
    w.setCalendarPopup(True)
    w.setMinimumHeight(CONST.input_height)
    w.setMaximumHeight(CONST.input_height)
    return w


def time_input() -> QTimeEdit:
    w = QTimeEdit()
    apply_state_contract(w, "time-input")
    apply_accessibility(w, "Time input", "Time input. Keyboard: Arrow keys adjust time.")
    w.setTime(QTime.currentTime())
    w.setMinimumHeight(CONST.input_height)
    w.setMaximumHeight(CONST.input_height)
    return w


def checkbox(text: str, checked: bool = False) -> QCheckBox:
    w = QCheckBox(text)
    apply_state_contract(w, "checkbox")
    apply_accessibility(w, text or "Checkbox", "Checkbox. Keyboard: Space toggles checked state.")
    w.setProperty("vibSelectionControl", "checkbox-v1")
    w.setChecked(checked)
    return w


def radio(text: str, checked: bool = False) -> QRadioButton:
    w = QRadioButton(text)
    apply_state_contract(w, "radio")
    apply_accessibility(w, text or "Radio option", "Radio option. Keyboard: Space selects this option.")
    w.setProperty("vibSelectionControl", "radio-v1")
    w.setChecked(checked)
    return w


class ToggleSwitch(QCheckBox):
    """Flat 36×20 toggle using official Vib Tools tokens.

    The control paints its own track/knob to avoid native checkbox styling,
    glow, shadows, gradients, or raised effects. It remains keyboard-focusable
    and exposes the Step-14 keyboard-only focus ring through ``keyboardFocus``.
    """

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ToggleSwitch")
        apply_state_contract(self, "toggle")
        apply_accessibility(self, "Toggle switch", "Toggle switch. Keyboard: Space toggles on or off.")
        self.setProperty("vibToggleControl", "flat-v1")
        self.setChecked(checked)
        self.setText("")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(CONST.toggle_width, CONST.toggle_height)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(CONST.toggle_width, CONST.toggle_height)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        hovered = bool(self.underMouse())
        if not self.isEnabled():
            track_bg = QColor(COLORS.get("toggle_disabled_track", COLORS["surface"]))
            track_border = QColor(COLORS.get("button_disabled_border", COLORS["border"]))
            knob = QColor(COLORS.get("toggle_disabled_knob", COLORS["disabled"]))
        elif self.isChecked():
            track_bg = QColor(COLORS.get("toggle_checked_hover_background" if hovered else "toggle_checked_background", COLORS.get("toggle_on", COLORS["primary"])))
            track_border = QColor(COLORS.get("toggle_on_border", COLORS.get("toggle_on", COLORS["primary"])))
            knob = QColor(COLORS["primary_text"])
        else:
            track_bg = QColor(COLORS.get("toggle_unchecked_hover_background" if hovered else "toggle_off", COLORS["border"]))
            track_border = QColor(COLORS.get("input_hover_border" if hovered else "input_border", COLORS["border"]))
            knob = QColor(COLORS["secondary_text"])

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(track_border, 1))
        painter.setBrush(track_bg)
        painter.drawRoundedRect(rect, CONST.toggle_height // 2, CONST.toggle_height // 2)

        knob_d = CONST.toggle_knob
        x = self.width() - knob_d - 3 if self.isChecked() else 3
        y = (self.height() - knob_d) // 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(knob)
        painter.drawEllipse(x, y, knob_d, knob_d)

        if self.property("keyboardFocus") == "true":
            painter.setPen(QPen(QColor(COLORS["secondary_accent"]), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)


def toggle(text: str = "", checked: bool = False) -> QWidget:
    """Frozen toggle row using the central Step-31 component toggle contract."""
    row = QWidget()
    row.setObjectName("ToggleRow")
    lay = hbox(row, margins=(0, 0, 0, 0), spacing=CONST.action_gap)
    control = ToggleSwitch(checked)
    lay.addWidget(control)
    if text:
        lay.addWidget(label(text, "Description", False), 1)
    else:
        lay.addStretch(1)
    return row


def slider(value: int = 50) -> QSlider:
    w = QSlider(Qt.Horizontal)
    apply_accessibility(w, "Slider", "Slider. Keyboard: Arrow keys adjust value.")
    w.setRange(0, 100)
    w.setValue(value)
    return w


def _table_column_weights(headers: Sequence[str]) -> list[int]:
    """Frozen table columns: content-aware widths without broken/floating blocks."""
    profile = {
        "name": 26,
        "project": 26,
        "owner": 20,
        "status": 14,
        "priority": 14,
        "updated": 16,
        "files": 8,
        "action": 10,
        "state": 14,
        "background": 24,
        "border": 24,
        "text": 16,
        "behavior": 22,
    }
    return [profile.get(str(h).strip().lower(), 16) for h in headers]


def _table_cell_alignment(header: str, index: int, last_index: int) -> Qt.AlignmentFlag:
    h = header.strip().lower()
    if h in {"files", "count", "queue"}:
        return Qt.AlignRight | Qt.AlignVCenter
    if h in {"status"}:
        return Qt.AlignCenter
    if index == last_index and h in {"action", "actions"}:
        return Qt.AlignRight | Qt.AlignVCenter
    return Qt.AlignLeft | Qt.AlignVCenter



class KeyboardTableRow(QFrame):
    """Focusable compact table row for Step-36 keyboard QA.

    The row keeps the frozen 32px height; Space/Enter activate the first
    checkbox or action button inside the row so keyboard users can operate
    the visual table without changing its layout.
    """

    def __init__(self, accessible_name: str = "Table row", parent: QWidget | None = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setProperty("vibAccessibilityContract", ACCESSIBILITY_CONTRACT_PROPERTY)
        self.setAccessibleName(accessible_name)
        self.setAccessibleDescription("Table row. Keyboard: Space or Enter activates the row control when available.")
        self.setToolTip(accessible_name)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            checkbox_child = self.findChild(QCheckBox)
            if checkbox_child and checkbox_child.isEnabled():
                checkbox_child.click()
                event.accept()
                return
            for button_child in self.findChildren(QPushButton):
                if button_child.isEnabled():
                    button_child.click()
                    event.accept()
                    return
        super().keyPressEvent(event)

def data_table(headers: Sequence[str], rows: Sequence[Sequence[str]], selected_index: int | None = None) -> QFrame:
    """Custom flat table visual; no native table widget, no native table-widget scrollbar.

    Step 12 keeps the frozen table contract and fixes the marked column breakage:
    one shared column-weight profile is applied to every row, header and cell;
    the table itself has no rounded/bordered shell, vertical grid, shadow, glow or
    floating/elevated box.
    """
    table = QFrame()
    table.setObjectName("DataTable")
    apply_state_contract(table, "data-table")
    table.setFrameShape(QFrame.NoFrame)
    table.setLineWidth(0)
    table.setMinimumWidth(0)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    table.setProperty("vibResponsiveContract", "step-38-high-dpi-responsive-certification")
    apply_accessibility(table, "Data table", "Compact data table. Keyboard: Tab to rows/actions; Space or Enter activates focused row controls.")
    lay = vbox(table, margins=(0, 0, 0, 0), spacing=0)
    weights = _table_column_weights(headers)

    def add_cells(row_widget: QFrame, values: Sequence[str], header_row: bool = False) -> None:
        grid = QGridLayout(row_widget)
        grid.setContentsMargins(CONST.table_cell_padding_x, 0, CONST.table_cell_padding_x, 0)
        grid.setHorizontalSpacing(CONST.table_cell_gap)
        grid.setSizeConstraint(QGridLayout.SetNoConstraint)
        grid.setVerticalSpacing(0)
        last = len(headers) - 1
        for i, header_name in enumerate(headers):
            value = str(values[i]) if i < len(values) else ""
            align = _table_cell_alignment(str(header_name), i, last)
            if not header_row and str(header_name).strip().lower() == "status":
                holder = QWidget()
                holder.setMinimumWidth(0)
                holder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                holder_lay = hbox(holder, margins=(0, 0, 0, 0), spacing=0)
                holder_lay.addStretch(1)
                holder_lay.addWidget(status_badge(value, value.lower()))
                holder_lay.addStretch(1)
                grid.addWidget(holder, 0, i, align)
            else:
                cell_name = "TableHeaderCell" if header_row else ("TableCell" if i == 0 else "TableCellMuted")
                if not header_row and i == last and value.lower() in {"open", "view", "edit", "retry", "more"}:
                    cell_name = "TableActionCell"
                cell = elide_label(value, cell_name)
                cell.setAlignment(align)
                cell.setMinimumWidth(0)
                cell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                grid.addWidget(cell, 0, i, align)
            grid.setColumnStretch(i, weights[i] if i < len(weights) else 16)

    header = QFrame()
    header.setObjectName("TableHeaderRow")
    header.setProperty("vibResponsiveContract", "step-38-high-dpi-responsive-certification")
    header.setMinimumWidth(0)
    header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    header.setMinimumHeight(CONST.table_header_height)
    header.setMaximumHeight(CONST.table_header_height)
    add_cells(header, [str(h).upper() for h in headers], header_row=True)
    lay.addWidget(header)

    if not rows:
        row = KeyboardTableRow("No data entries available")
        row.setObjectName("TableRow")
        row.setMinimumHeight(CONST.data_table_row_height)
        row.setMaximumHeight(CONST.data_table_row_height)
        row.setAttribute(Qt.WA_Hover, True)
        empty_values = ["No data entries available"] + ["" for _ in range(max(0, len(headers) - 1))]
        add_cells(row, empty_values, header_row=False)
        lay.addWidget(row)
    else:
        for index, row_values in enumerate(rows):
            row = KeyboardTableRow(" | ".join(str(v) for v in row_values))
            row.setObjectName("TableRowSelected" if selected_index == index else "TableRow")
            row.setProperty("vibResponsiveContract", "step-38-high-dpi-responsive-certification")
            row.setMinimumWidth(0)
            row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.setMinimumHeight(CONST.data_table_row_height)
            row.setMaximumHeight(CONST.data_table_row_height)
            row.setAttribute(Qt.WA_Hover, True)
            add_cells(row, row_values, header_row=False)
            lay.addWidget(row)
    return table


class Toast(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._label = QLabel("")
        self._label.setWordWrap(True)
        layout = hbox(self, margins=(12, 8, 12, 8), spacing=CONST.action_gap)
        layout.addWidget(self._label)
        self.hide()

    def show_message(self, text: str, tone: str = "info", timeout_ms: int = 2200) -> None:
        colors = {"success": COLORS["success"], "error": COLORS["danger"], "warning": COLORS["warning"], "info": COLORS["secondary_accent"]}
        self._label.setText(text)
        self._label.setStyleSheet(f"color:{COLORS['primary_text']};")
        self.setStyleSheet(f"QWidget#Card{{background:{COLORS['surface']}; border:1px solid {colors.get(tone, COLORS['secondary_accent'])}; border-radius:8px;}}")
        self.adjustSize()
        if self.parentWidget():
            parent_geo = self.parentWidget().geometry()
            self.move(parent_geo.right() - self.width() - 24, parent_geo.bottom() - self.height() - 56)
        self.show()
        QTimer.singleShot(timeout_ms, self.hide)


class DropZone(QFrame):
    filesDropped = Signal(list)

    def __init__(self, text: str = "Drop files here"):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("DropZone")
        self.setProperty("dragActive", "false")
        self.setProperty("vibDropZoneContract", "step-37-dropzone-contract")
        self.setProperty("vibResponsiveContract", "step-38-high-dpi-responsive-certification")
        apply_state_contract(self, "drop-zone")
        apply_accessibility(self, text, "Compact drag and drop target. Drop demo files here; no backend upload is performed.")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(CONST.dropzone_height)
        self.setMaximumHeight(CONST.dropzone_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = vbox(
            self,
            margins=(CONST.dropzone_padding_x, CONST.dropzone_padding_y, CONST.dropzone_padding_x, CONST.dropzone_padding_y),
            spacing=CONST.dropzone_text_gap,
        )
        self.message = title(text, "DropZoneTitle")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setToolTip(text)
        self.help_text = label("Drag/drop highlight only. No backend upload.", "DropZoneHelp", False)
        self.help_text.setAlignment(Qt.AlignCenter)
        self.help_text.setToolTip("Drag/drop highlight only. No backend upload.")
        layout.addWidget(self.message, 0, Qt.AlignCenter)
        layout.addWidget(self.help_text, 0, Qt.AlignCenter)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        files = [u.toLocalFile() for u in urls if u.toLocalFile()]
        self.filesDropped.emit(files)
        dropped_text = f"{len(files)} file(s) dropped"
        self.message.setText(dropped_text)
        self.message.setToolTip(dropped_text)
        self._set_drag_active(False)
        event.acceptProposedAction()


class CommandPalette(QDialog):
    commandSelected = Signal(str)

    def __init__(self, parent: QWidget, commands: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.setMinimumSize(420, 240)
        self.resize(500, 300)
        apply_accessibility(self, "Command Palette", "Modal command palette. Keyboard: Tab through commands, Enter activates, Escape closes.")
        self._first_command_button: QPushButton | None = None
        layout = vbox(self, margins=(CONST.card_padding, CONST.card_padding, CONST.card_padding, CONST.card_padding), spacing=CONST.card_internal_gap)
        layout.addWidget(title("Command Palette", "PageTitle"))
        layout.addWidget(elide_label("Step-39B keeps 28px flat actions and completes responsive breakage repair with responsive bounds preserved; no glow/shadow/floating active state.", "Description"))
        for command in commands[:7]:
            b = button(command, "secondary")
            b.clicked.connect(lambda _=False, c=command: self._select(c))
            if self._first_command_button is None:
                self._first_command_button = b
            layout.addWidget(b)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        constrain_widget_to_available_screen(self)
        if self._first_command_button is not None:
            QTimer.singleShot(0, self._first_command_button.setFocus)

    def _select(self, command: str) -> None:
        self.commandSelected.emit(command)
        self.accept()


class MiniDialog(QDialog):
    def __init__(self, parent: QWidget, title_text: str, body_text: str, danger: bool = False):
        super().__init__(parent)
        self.setObjectName("ModalDialog")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(title_text)
        apply_accessibility(self, title_text, "Modal dialog. Keyboard: Tab through actions, Enter confirms, Escape cancels.")
        self._previous_focus = QApplication.focusWidget()
        self.setMinimumSize(360, 180)
        self.resize(420, 220)
        layout = vbox(self, margins=(CONST.card_padding, CONST.card_padding, CONST.card_padding, CONST.card_padding), spacing=CONST.card_internal_gap)
        layout.addWidget(title(title_text, "PageTitle"))
        layout.addWidget(label(body_text, "Description"))
        actions = hbox(spacing=CONST.modal_action_gap)
        actions.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        cancel = button("Cancel", "secondary")
        ok = button("Confirm" if danger else "Done", "danger" if danger else "primary")
        self.cancel_button = cancel
        self.ok_button = ok
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(ok)
        layout.addLayout(actions)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        constrain_widget_to_available_screen(self)
        QTimer.singleShot(0, self.ok_button.setFocus)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key_Escape:
            self.reject()
            event.accept()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.accept()
            event.accept()
            return
        super().keyPressEvent(event)

    def done(self, result: int) -> None:  # type: ignore[override]
        previous = getattr(self, "_previous_focus", None)
        super().done(result)
        if previous is not None:
            try:
                previous.setFocus(Qt.OtherFocusReason)
            except RuntimeError:
                pass


def add_shortcut(parent: QWidget, sequence: str, slot) -> QShortcut:
    shortcut = QShortcut(QKeySequence(sequence), parent)
    shortcut.activated.connect(slot)
    return shortcut
