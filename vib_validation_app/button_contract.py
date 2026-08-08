"""Central frozen Vib Tools flat button contract — Step 39B visible compact density repair.

This module is the single construction/configuration point for every
QPushButton used by the validation app.  Pages should not style buttons
individually; they should create buttons through widgets.button() or configure
an existing button through apply_button_contract()/apply_nav_button_contract().

Frozen rules enforced here:
- 28px action button height, 28px sidebar nav height, 20px link height
- 8px radius through QSS object names
- 12px/500 compact button typography through QSS
- 16px glyph icon size, 28px icon button frame, 16px nav icon size
- no native/default elevation, no auto-default glow, no graphics effect
- fixed/content-based action width unless a caller explicitly sets another policy
- Step 39B responsive breakage repair: action buttons remain 28px high but horizontal padding is tightened to 9px; nav is 28px with 2px/8px padding and 6px icon-text gap; icon buttons are 28px; links are 20px
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QSizePolicy

from .tokens import CONST

ButtonKind = Literal[
    "primary",
    "secondary",
    "ghost",
    "danger",
    "selected",
    "icon",
    "link",
    "success",
    "warning",
]

BUTTON_OBJECT_NAMES: dict[str, str] = {
    "primary": "PrimaryButton",
    "secondary": "SecondaryButton",
    "ghost": "GhostButton",
    "danger": "DangerButton",
    "selected": "SelectedButton",
    "icon": "IconButton",
    "link": "LinkButton",
    "success": "SuccessButton",
    "warning": "WarningButton",
}


@dataclass(frozen=True)
class FrozenButtonContract:
    height: int = 28
    link_height: int = 20
    nav_height: int = 28
    radius: int = 8
    font_size: int = 12
    font_weight: int = 500
    padding_x: int = 9
    padding_y: int = 0
    icon_size: int = 16
    icon_button_size: int = 28
    nav_icon_size: int = 16
    icon_gap: int = 6
    nav_icon_gap: int = 6
    nav_padding_y: int = 2
    focus_ring: int = 2
    animation_ms: str = "120-150ms documented; Qt QSS keeps static flat states"


BUTTON_CONTRACT = FrozenButtonContract()

# Qt QPushButton does not expose an explicit icon/text gap property in QSS.
# The Step-23 compact nav trial requires an approximately 6px icon-to-label gap, so nav labels are
# centrally normalized with a small text spacer while icon size/padding remain
# controlled by BUTTON_CONTRACT + app_qss().  This keeps every sidebar item
# visually consistent without page-level per-button styling.
NAV_TEXT_GAP_PREFIX = " "


def _nav_label_with_gap(text: str) -> str:
    clean = text.lstrip()
    if clean.startswith(NAV_TEXT_GAP_PREFIX):
        return clean
    return f"{NAV_TEXT_GAP_PREFIX}{clean}"


def normalize_button_kind(kind: str | None) -> str:
    if not kind:
        return "secondary"
    return kind if kind in BUTTON_OBJECT_NAMES else "secondary"


def apply_button_contract(
    btn: QPushButton,
    kind: str = "secondary",
    *,
    icon_obj: QIcon | None = None,
    tooltip: str | None = None,
    fixed_width: bool = True,
) -> QPushButton:
    """Apply the frozen action-button contract to an existing QPushButton.

    Step-39B preserves accessible names/descriptions and 28px/20px geometry while
    tightening the action-button horizontal padding through the stylesheet.
    """
    normalized = normalize_button_kind(kind)
    btn.setObjectName(BUTTON_OBJECT_NAMES[normalized])
    btn.setProperty("vibButtonContract", "flat-v1")
    btn.setProperty("vibDesignStep", "step-39b")
    btn.setProperty("vibButtonKind", normalized)
    clean_text = btn.text().strip() or (tooltip or normalized.title())
    btn.setAccessibleName(clean_text)
    btn.setAccessibleDescription(f"{normalized.title()} action button. Keyboard: Tab to focus, Enter or Space to activate.")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFlat(True)
    btn.setAutoDefault(False)
    btn.setDefault(False)
    btn.setFocusPolicy(Qt.StrongFocus)
    btn.setGraphicsEffect(None)

    height = BUTTON_CONTRACT.link_height if normalized == "link" else BUTTON_CONTRACT.height
    btn.setMinimumHeight(height)
    btn.setMaximumHeight(height)
    btn.setMinimumWidth(0)

    if icon_obj is not None:
        btn.setIcon(icon_obj)
    btn.setIconSize(QSize(BUTTON_CONTRACT.icon_size, BUTTON_CONTRACT.icon_size))

    if normalized == "icon":
        accessible = tooltip or btn.text() or "Icon action"
        btn.setToolTip(accessible)
        btn.setAccessibleName(accessible)
        btn.setAccessibleDescription("Icon action button. Keyboard: Tab to focus, Enter or Space to activate.")
        btn.setText("")
        btn.setFixedSize(BUTTON_CONTRACT.icon_button_size, BUTTON_CONTRACT.icon_button_size)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    elif fixed_width:
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    else:
        btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    if normalized != "icon" and not btn.toolTip():
        btn.setToolTip(clean_text)
    return btn


def apply_nav_button_contract(btn: QPushButton, *, icon_obj: QIcon | None = None) -> QPushButton:
    """Apply the frozen sidebar navigation button contract.

    Step-39B keeps the 28px nav row, screen-reader labels and keyboard activation
    guidance while preserving visual size contracts.
    """
    btn.setObjectName("NavItem")
    btn.setProperty("vibButtonContract", "flat-v1")
    btn.setProperty("vibDesignStep", "step-39b")
    btn.setProperty("vibButtonKind", "nav")
    clean_text = btn.text().strip()
    btn.setAccessibleName(f"Navigate to {clean_text}")
    btn.setAccessibleDescription("Sidebar navigation item. Keyboard: Tab to focus, Enter or Space to open page.")
    btn.setToolTip(f"Navigate to {clean_text}")
    btn.setProperty("vibNavPaddingX", 8)  # Step-24 final freeze uses 8px horizontal nav padding
    btn.setProperty("vibNavPaddingY", BUTTON_CONTRACT.nav_padding_y)  # Step-24 final freeze: 2px vertical nav padding
    btn.setProperty("vibNavIconGapPx", BUTTON_CONTRACT.nav_icon_gap)
    btn.setCheckable(True)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFlat(True)
    btn.setAutoDefault(False)
    btn.setDefault(False)
    btn.setFocusPolicy(Qt.StrongFocus)
    btn.setGraphicsEffect(None)
    btn.setLayoutDirection(Qt.LeftToRight)
    btn.setMinimumHeight(BUTTON_CONTRACT.nav_height)
    btn.setMaximumHeight(BUTTON_CONTRACT.nav_height)
    btn.setFixedHeight(BUTTON_CONTRACT.nav_height)
    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    if icon_obj is not None:
        btn.setIcon(icon_obj)
    btn.setIconSize(QSize(BUTTON_CONTRACT.nav_icon_size, BUTTON_CONTRACT.nav_icon_size))
    btn.setText(_nav_label_with_gap(btn.text()))
    return btn


class VibButton(QPushButton):
    """Reusable frozen flat button component for all validation pages."""

    def __init__(self, text: str = "", kind: str = "secondary", icon_obj: QIcon | None = None, parent=None):
        super().__init__(text, parent)
        apply_button_contract(self, kind, icon_obj=icon_obj)
