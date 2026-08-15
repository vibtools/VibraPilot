"""Qt stylesheet for Step-39B Visible Compact Density Repair.

Step-39B keeps the Step-38/Step-39 responsive/accessibility baseline and makes
compact density visible by tightening whitespace, padding, large empty areas and density-safe gaps. Core control
heights, colors and visual language are preserved.
"""
from __future__ import annotations

from pathlib import Path

from .tokens import COLORS, TYPE, TYPOGRAPHY, TYPO_RUNTIME, CONST, BORDER

FONT_FAMILY = TYPOGRAPHY.get("primary_ui_font", "Segoe UI Variable")
FALLBACK_FONT = TYPOGRAPHY.get("fallback_ui_font", "Segoe UI")
ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def _rgba_from_hex(hex_color: str, alpha: float) -> str:
    """Return Qt-compatible rgba() with integer alpha.

    Qt Style Sheets are most reliable with alpha expressed as 0–255. The
    previous decimal alpha could render inconsistently on Windows and made
    selected/button states look louder than intended.
    """
    h = hex_color.strip().lstrip("#")
    if len(h) != 6:
        return hex_color
    a = max(0, min(255, int(round(alpha * 255))))
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def app_qss(theme: str = "dark") -> str:
    c = COLORS
    radius = CONST.common_radius
    border = BORDER.get("common_width_px", 1)
    font = f'"{FONT_FAMILY}", "{FALLBACK_FONT}", sans-serif'
    page_title_weight = TYPO_RUNTIME.get("page_title_weight", 600)
    section_title_weight = TYPO_RUNTIME.get("section_title_weight", 600)
    card_title_weight = TYPO_RUNTIME.get("card_title_weight", 600)
    body_weight = TYPO_RUNTIME.get("body_weight", 400)
    small_label_weight = TYPO_RUNTIME.get("small_label_weight", 500)
    table_header_weight = TYPO_RUNTIME.get("table_header_weight", 600)
    page_title_line_height = TYPO_RUNTIME.get("page_title_line_height", 18)
    section_title_line_height = TYPO_RUNTIME.get("section_title_line_height", 16)
    card_title_line_height = TYPO_RUNTIME.get("card_title_line_height", 16)
    body_line_height = TYPO_RUNTIME.get("body_line_height", 15)
    caption_line_height = TYPO_RUNTIME.get("caption_line_height", 14)
    focus_ring_color = c.get("focus_ring_color", c["secondary_accent"])
    hover_primary = c.get("button_primary_hover_background", c.get("primary_hover", c["primary"]))
    pressed_primary = c.get("button_primary_pressed_background", c["primary"])
    danger_hover = c.get("danger_hover", c["danger"])
    danger_pressed = c.get("danger_pressed", c.get("danger_hover", c["danger"]))
    selected_subtle = c.get("button_active_background", c.get("selected_row_bg", c.get("selection", _rgba_from_hex(c["primary"], 0.15))))
    nav_selected_bg = c.get("nav_selected_bg", selected_subtle)
    subtle_primary = _rgba_from_hex(c["primary"], 0.10)
    subtle_accent = _rgba_from_hex(c["secondary_accent"], 0.10)
    hover_overlay = c.get("button_hover_overlay", c["hover_overlay"])
    row_hover_overlay = c["row_hover_overlay"]
    button_primary_border = c.get("button_primary_border", c["primary"])
    button_secondary_bg = c.get("button_secondary_background", c["nested_surface"])
    button_secondary_hover_bg = c.get("button_secondary_hover_background", c.get("surface_hover", button_secondary_bg))
    button_secondary_pressed_bg = c.get("button_secondary_pressed_background", button_secondary_bg)
    button_disabled_bg = c.get("button_disabled_background", "transparent")
    button_disabled_border = c.get("button_disabled_border", c["border"])
    button_disabled_text = c.get("button_disabled_text", c["disabled"])
    button_primary_disabled_bg = c.get("button_primary_disabled_background", c["surface"])
    ghost_hover_bg = c.get("button_ghost_hover_background", hover_overlay)
    ghost_pressed_bg = c.get("button_ghost_pressed_background", c["nested_surface"])
    button_secondary_border = c.get("button_secondary_border", c.get("button_outline_border", c["border"]))
    outline_border = c.get("button_outline_border", button_secondary_border)
    nested_border = c["nested_border"]
    input_bg = c.get("input_background", c["window_background"])
    input_border = c["input_border"]
    input_focus_border = c.get("input_focus_border", c["secondary_accent"])
    input_hover_border = c.get("input_hover_border", input_border)
    input_disabled_bg = c.get("input_disabled_background", c["surface"])
    input_disabled_border = c.get("input_disabled_border", nested_border)
    input_disabled_text = c.get("input_disabled_text", c["disabled"])
    table_header_bg = c["table_header_background"]
    table_header_text = c.get("table_header_text", c["secondary_text"])
    title_text = c.get("title_text", c["primary_text"])
    card_title_text = c.get("card_title_text", title_text)
    section_title_text = c.get("section_title_text", title_text)
    field_label = c.get("form_label", c.get("field_label", c["secondary_text"]))
    muted_text = c.get("muted_text", c["secondary_text"])
    placeholder_text = c.get("placeholder_text", c["secondary_text"])
    breadcrumb_text = c.get("breadcrumb_text", c["secondary_text"])
    checkbox_border = c.get("selection_control_border", c.get("checkbox_border", c["border"]))
    selection_control_hover_border = c.get("selection_control_hover_border", c["secondary_text"])
    selection_control_checked_bg = c.get("selection_control_checked_background", c["primary"])
    selection_control_checked_hover_bg = c.get("selection_control_checked_hover_background", hover_primary)
    selection_control_disabled_bg = c.get("selection_control_disabled_background", c["surface"])
    selection_control_disabled_border = c.get("selection_control_disabled_border", c["border"])
    selected_row_indicator = c.get("selected_row_indicator", c["secondary_accent"])
    selected_row_hover_bg = c.get("table_row_selected_hover_bg", selected_subtle)
    plugin_chip_background = c.get("plugin_chip_background", subtle_accent)
    plugin_chip_border = c.get("plugin_chip_border", _rgba_from_hex(c["secondary_accent"], 0.24))
    plugin_chip_text = c.get("plugin_chip_text", c["secondary_text"])
    plugin_title_text = c.get("plugin_title_text", card_title_text)
    plugin_body_text = c.get("plugin_body_text", c.get("body_text", c["secondary_text"]))
    file_tree_selected_bg = c.get("file_tree_selected_bg", selected_subtle)
    file_tree_hover_bg = c.get("file_tree_hover_bg", row_hover_overlay)
    file_tree_header_bg = c.get("file_tree_header_bg", table_header_bg)
    folder_icon_color = c.get("folder_icon_color", c["warning"])
    file_icon_color = c.get("file_icon_color", c["secondary_text"])
    tree_guide = c["tree_guide"]
    node_top_highlight = c["node_top_highlight"]
    modal_background = c.get("modal_background", c["nested_surface"])
    modal_border = c.get("modal_border", c["border"])
    empty_state_text = c.get("empty_state_text", c["secondary_text"])
    table_action_text = c.get("table_action_text", c["secondary_accent"])
    table_row_border = c.get("table_row_border", c["border"])
    tooltip_background = c.get("tooltip_background", c["surface"])
    tooltip_border = c.get("tooltip_border", c["border"])
    tooltip_text = c.get("tooltip_text", c["primary_text"])
    dropzone_background = c.get("dropzone_background", c["surface"])
    dropzone_border = c.get("dropzone_border", c["border"])
    dropzone_hover_background = c.get("dropzone_hover_background", c["nested_surface"])
    dropzone_hover_border = c.get("dropzone_hover_border", c["secondary_accent"])
    dropzone_title_text = c.get("dropzone_title_text", card_title_text)
    dropzone_helper_text = c.get("dropzone_helper_text", c["secondary_text"])
    plugin_card_hover_background = c.get("plugin_card_hover_background", c["surface"])
    plugin_card_hover_border = c.get("plugin_card_hover_border", _rgba_from_hex(c["secondary_accent"], 0.40))
    workflow_control_hover_bg = c.get("workflow_control_hover_background", button_secondary_hover_bg)
    workflow_control_pressed_bg = c.get("workflow_control_pressed_background", button_secondary_pressed_bg)
    menu_item_hover_bg = c.get("menu_item_hover_background", hover_overlay)
    chevron_right = (ICON_DIR / "chevron-right.svg").as_posix()
    chevron_down = (ICON_DIR / "chevron-down.svg").as_posix()
    check_icon = (ICON_DIR / "check.svg").as_posix()
    minus_icon = (ICON_DIR / "minus.svg").as_posix()
    return f"""
    * {{
        font-family: {font};
        font-size: {TYPE['body']}px;
        color: {c['primary_text']};
        outline: 0;
    }}

    QMainWindow, QDialog {{ background: {c['window_background']}; color: {c['primary_text']}; }}
    QWidget#AppRoot, QWidget#PageViewport, QWidget#PageContent, QWidget#PageInner {{ background: {c['page_background']}; border: none; }}
    QScrollArea#HiddenScrollArea, QScrollArea#MinimalScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea#HiddenScrollArea > QWidget, QScrollArea#HiddenScrollArea > QWidget > QWidget,
    QScrollArea#MinimalScrollArea > QWidget, QScrollArea#MinimalScrollArea > QWidget > QWidget {{
        background: {c['page_background']};
        border: none;
    }}

    QMenuBar {{
        background: {c['window_background']};
        color: {c['secondary_text']};
        border-bottom: {border}px solid {c['border']};
        font-size: {TYPE['body']}px;
        min-height: 28px;
        max-height: 28px;
    }}
    QMenuBar::item {{ padding: 5px 10px; background: transparent; border-radius: 0px; }}
    QMenuBar::item:selected {{ background: {hover_overlay}; color: {c['primary_text']}; }}
    QMenuBar::item:pressed {{ background: {c['nested_surface']}; color: {c['primary_text']}; }}

    QWidget#WindowHeader, QFrame#WindowHeader {{
        background: {c['window_background']};
        border-bottom: {border}px solid {c['border']};
        min-height: {CONST.header_height}px;
        max-height: {CONST.header_height}px;
    }}
    QWidget#HeaderActionCluster {{
        background: transparent;
        border: none;
        min-height: {CONST.header_height}px;
        max-height: {CONST.header_height}px;
    }}

    QLabel {{ color: {c['primary_text']}; background: transparent; }}
    QLabel#AppTitle, QLabel#WindowTitle {{ font-size: 14px; font-weight: 500; color: {title_text}; line-height: 17px; }}
    QLabel#SidebarTitle {{ font-size: {CONST.sidebar_title_font_size}px; font-weight: 600; color: {title_text}; line-height: 16px; }}
    QLabel#PageTitle {{ font-size: {TYPE['page_title']}px; font-weight: {page_title_weight}; color: {title_text}; line-height: {page_title_line_height}px; }}
    QLabel#SectionTitle {{ font-size: {TYPE['section_title']}px; font-weight: {section_title_weight}; color: {section_title_text}; line-height: {section_title_line_height}px; }}
    QLabel#CardTitle {{ font-size: {CONST.card_title_font_size}px; font-weight: {card_title_weight}; color: {card_title_text}; line-height: {card_title_line_height}px; }}
    QLabel#FormLabel {{ font-size: 11px; font-weight: {small_label_weight}; color: {field_label}; line-height: {caption_line_height}px; }}
    QLabel#Description {{ color: {c.get('card_description_text', c.get('body_text', c['secondary_text']))}; }}
    QLabel#Caption, QLabel#Muted, QLabel#HelpText {{ color: {muted_text}; }}
    QLabel#Description {{ font-size: {TYPE['body']}px; font-weight: {body_weight}; line-height: {body_line_height}px; }}
    QLabel#HelpText, QLabel#ValidationText {{ font-size: {TYPE['caption']}px; font-weight: 400; line-height: {caption_line_height}px; }}
    QLabel#ValidationText {{ color: {muted_text}; }}
    QLabel#Caption {{ font-size: {TYPE['caption']}px; line-height: {caption_line_height}px; }}
    QLabel#StatusText {{ font-size: {TYPE['status']}px; color: {c.get('shell_caption_text', c['secondary_text'])}; }}
    QLabel#Breadcrumb {{ font-size: {TYPE['caption']}px; color: {breadcrumb_text}; line-height: {caption_line_height}px; }}
    QLabel#EmptyState {{ font-size: {TYPE['body']}px; font-weight: 400; color: {empty_state_text}; line-height: {body_line_height}px; }}
    QLabel#TableHeaderCell {{ font-size: {TYPE['table_header']}px; font-weight: {table_header_weight}; color: {table_header_text}; text-transform: uppercase; }}
    QLabel#TableCell {{ font-size: {TYPE['table_data']}px; font-weight: 400; color: {c['primary_text']}; }}
    QLabel#TableCellMuted {{ font-size: {TYPE['table_data']}px; font-weight: 400; color: {c['secondary_text']}; }}

    QScrollArea#HiddenScrollArea::viewport, QScrollArea#MinimalScrollArea::viewport {{
        background: {c['page_background']};
        border: none;
    }}
    QWidget#Sidebar QScrollArea#MinimalScrollArea,
    QWidget#Sidebar QScrollArea#MinimalScrollArea::viewport,
    QWidget#Sidebar QWidget#SidebarNavHost {{
        background: {c['window_background']};
        border: none;
    }}
    QWidget#Sidebar QScrollArea#MinimalScrollArea {{
        padding-right: 0px;
    }}

    QWidget#Sidebar, QFrame#Sidebar {{
        background: {c['window_background']};
        border-right: {border}px solid {c['border']};
        min-width: {CONST.sidebar_width}px;
        max-width: {CONST.sidebar_width}px;
    }}

    QFrame#PageHeader {{ background: transparent; border: none; border-bottom: {border}px solid {c['border']}; border-radius: 0px; }}
    QWidget#CardHeader {{ background: transparent; border: none; }}
    QFrame#Section {{ background: transparent; border: none; border-radius: 0px; }}

    QFrame#Card, QWidget#Card, QFrame#AuthCard, QFrame#Panel, QWidget#Panel, QGroupBox {{
        background: {c['surface']};
        border: {border}px solid {c['border']};
        border-radius: {radius}px;
    }}
    QFrame#WorkflowCard {{
        background: {c['surface']};
        border: 2px solid {c['border']};
        border-radius: {radius}px;
    }}
    QFrame#NestedCard, QWidget#NestedCard, QFrame#Box {{
        background: {c['nested_surface']};
        border: {border}px solid {nested_border};
        border-radius: {radius}px;
    }}
    QFrame#Metric {{ background: {c['surface']}; border: {border}px solid {c['border']}; border-radius: {radius}px; }}
    QFrame#DropZone {{
        background: {dropzone_background};
        border: {border}px dashed {dropzone_border};
        border-radius: {radius}px;
        min-height: {CONST.dropzone_height}px;
        max-height: {CONST.dropzone_height}px;
    }}
    QFrame#DropZone[dragActive="true"] {{
        background: {dropzone_hover_background};
        border: {border}px dashed {dropzone_hover_border};
    }}
    QFrame#DropZone:focus {{
        border: {CONST.focus_ring}px solid {focus_ring_color};
        background: {dropzone_hover_background};
    }}
    QLabel#DropZoneTitle {{
        font-size: {CONST.card_title_font_size}px;
        font-weight: {card_title_weight};
        color: {dropzone_title_text};
        line-height: {card_title_line_height}px;
    }}
    QLabel#DropZoneHelp {{
        font-size: {TYPE['caption']}px;
        font-weight: 400;
        color: {dropzone_helper_text};
        line-height: {caption_line_height}px;
    }}
    QFrame#AuthCard QLabel#Description {{
        font-size: 12px;
        color: {c.get('body_text', c['secondary_text'])};
        line-height: {body_line_height}px;
        margin-bottom: 0px;
    }}
    QFrame#AuthCard QLabel#CardTitle {{
        font-size: {CONST.card_title_font_size}px;
        font-weight: {card_title_weight};
        line-height: {card_title_line_height}px;
    }}

    QWidget#AuthOptionsRow {{
        background: transparent;
        border: none;
        min-height: {CONST.form_login_options_row_height}px;
        max-height: {CONST.form_login_options_row_height}px;
    }}
    QWidget#AuthSubmitRow {{
        background: transparent;
        border: none;
        min-height: {CONST.button_height}px;
        max-height: {CONST.button_height}px;
    }}
    QWidget#AuthOptionsRow QCheckBox {{
        min-height: {CONST.form_login_options_row_height}px;
        max-height: {CONST.form_login_options_row_height}px;
        margin: 0px;
    }}
    QWidget#AuthOptionsRow QPushButton#LinkButton {{
        min-height: {CONST.link_button_height}px;
        max-height: {CONST.link_button_height}px;
        margin: 0px;
        padding: 0px 0px 0px 4px;
    }}

    QGroupBox::title {{
        font-size: {CONST.card_title_font_size}px;
        font-weight: {card_title_weight};
        color: {card_title_text};
        subcontrol-origin: margin;
        left: 12px;
        padding: 0px 4px;
    }}
    QFrame#FlatRow {{ background: transparent; border-bottom: {border}px solid {c['border']}; }}
    QFrame#Divider {{ min-height: 1px; max-height: 1px; background: {c['border']}; border: none; }}

    /* Step 31 central hard rule: every QPushButton is a flat VibButton.
       One reusable button contract drives page, hero, form, card, toolbar,
       pagination, screenshot and dialog actions. States use color changes only:
       no shadow, no glow, no native default border halo and no geometry jump.
       Step 39B: 2px flat focus ring is keyboard-only; action buttons stay 28px high with tighter 0px/{CONST.button_padding_x}px padding; nav stays 28px. */
    QPushButton {{
        height: {CONST.button_height}px;
        min-height: {CONST.button_height}px;
        max-height: {CONST.button_height}px;
        min-width: 0px;
        padding: 0px {CONST.button_padding_x}px;
        margin: 0px;
        border-radius: {radius}px;
        font-size: {CONST.button_font_size}px;
        font-weight: 500;
        border: {border}px solid {button_secondary_border};
        border-style: solid;
        background: {button_secondary_bg};
        color: {c['primary_text']};
        text-align: center;
    }}
    QPushButton:hover {{ background: {button_secondary_hover_bg}; color: {c['primary_text']}; border: {border}px solid {button_secondary_border}; }}
    QPushButton:pressed {{ background: {button_secondary_pressed_bg}; color: {c['primary_text']}; border: {border}px solid {button_secondary_border}; }}
    QPushButton[keyboardFocus="true"] {{ background: {button_secondary_bg}; color: {c['primary_text']}; border: 2px solid {focus_ring_color}; padding: 0px {CONST.button_focus_padding_x}px; }}
    QPushButton:default {{ border: {border}px solid {button_secondary_border}; }}
    QPushButton:disabled {{ color: {button_disabled_text}; background: {button_disabled_bg}; border: {border}px solid {button_disabled_border}; }}

    QPushButton#PrimaryButton {{
        background: {c['primary']};
        border: {border}px solid {button_primary_border};
        color: {c['primary_text']};
        padding: 0px {CONST.button_padding_x}px;
    }}
    QPushButton#PrimaryButton:hover {{ background: {hover_primary}; border: {border}px solid {button_primary_border}; color: {c['primary_text']}; }}
    QPushButton#PrimaryButton:pressed {{ background: {pressed_primary}; border: {border}px solid {button_primary_border}; color: {c['primary_text']}; }}
    QPushButton#PrimaryButton[keyboardFocus="true"] {{ background: {c['primary']}; border: 2px solid {focus_ring_color}; color: {c['primary_text']}; padding: 0px {CONST.button_focus_padding_x}px; }}
    QPushButton#PrimaryButton:default {{ border: {border}px solid {button_primary_border}; }}
    QPushButton#PrimaryButton:disabled {{ background: {button_primary_disabled_bg}; color: {button_disabled_text}; border: {border}px solid {button_disabled_border}; }}

    QPushButton#SecondaryButton {{ background: {button_secondary_bg}; border: {border}px solid {button_secondary_border}; color: {c['primary_text']}; padding: 0px {CONST.button_padding_x}px; }}
    QPushButton#SecondaryButton:hover {{ background: {button_secondary_hover_bg}; border: {border}px solid {button_secondary_border}; color: {c['primary_text']}; }}
    QPushButton#SecondaryButton:pressed {{ background: {button_secondary_pressed_bg}; border: {border}px solid {button_secondary_border}; color: {c['primary_text']}; }}
    QPushButton#SecondaryButton[keyboardFocus="true"] {{ background: {button_secondary_bg}; border: 2px solid {focus_ring_color}; padding: 0px {CONST.button_focus_padding_x}px; }}

    QPushButton#SelectedButton {{ background: {selected_subtle}; border: {border}px solid {button_secondary_border}; color: {c['primary_text']}; padding: 0px {CONST.button_padding_x}px; }}
    QPushButton#SelectedButton:hover {{ background: {selected_subtle}; border: {border}px solid {button_secondary_border}; color: {c['primary_text']}; }}
    QPushButton#SelectedButton:pressed {{ background: {selected_subtle}; border: {border}px solid {button_secondary_border}; color: {c['primary_text']}; }}
    QPushButton#SelectedButton[keyboardFocus="true"] {{ background: {selected_subtle}; border: 2px solid {focus_ring_color}; padding: 0px {CONST.button_focus_padding_x}px; }}

    QPushButton#GhostButton {{ background: transparent; border: {border}px solid transparent; color: {c['secondary_text']}; padding: 0px {CONST.button_padding_x}px; }}
    QPushButton#GhostButton:hover {{ background: {ghost_hover_bg}; border: {border}px solid transparent; color: {c['primary_text']}; }}
    QPushButton#GhostButton:pressed {{ background: {ghost_pressed_bg}; border: {border}px solid transparent; color: {c['primary_text']}; }}
    QPushButton#GhostButton[keyboardFocus="true"] {{ background: transparent; border: 2px solid {focus_ring_color}; color: {c['primary_text']}; padding: 0px {CONST.button_focus_padding_x}px; }}

    QPushButton#DangerButton {{ background: {c['danger']}; border: {border}px solid {c['danger']}; color: {c['primary_text']}; padding: 0px {CONST.button_padding_x}px; }}
    QPushButton#DangerButton:hover {{ background: {danger_hover}; border: {border}px solid {danger_hover}; color: {c['primary_text']}; }}
    QPushButton#DangerButton:pressed {{ background: {danger_pressed}; border: {border}px solid {danger_pressed}; color: {c['primary_text']}; }}
    QPushButton#DangerButton[keyboardFocus="true"] {{ background: {c['danger']}; border: 2px solid {focus_ring_color}; padding: 0px {CONST.button_focus_padding_x}px; }}

    QPushButton#SuccessButton {{ background: {c['success']}; border: {border}px solid {c['success']}; color: {c['primary_text']}; padding: 0px {CONST.button_padding_x}px; }}
    QPushButton#SuccessButton:hover, QPushButton#SuccessButton:pressed {{ background: {c['success']}; border: {border}px solid {c['success']}; color: {c['primary_text']}; }}
    QPushButton#SuccessButton[keyboardFocus="true"] {{ background: {c['success']}; border: 2px solid {focus_ring_color}; padding: 0px {CONST.button_focus_padding_x}px; }}

    QPushButton#WarningButton {{ background: {c['warning']}; border: {border}px solid {c['warning']}; color: {c['window_background']}; padding: 0px {CONST.button_padding_x}px; }}
    QPushButton#WarningButton:hover, QPushButton#WarningButton:pressed {{ background: {c['warning']}; border: {border}px solid {c['warning']}; color: {c['window_background']}; }}
    QPushButton#WarningButton[keyboardFocus="true"] {{ background: {c['warning']}; border: 2px solid {focus_ring_color}; padding: 0px {CONST.button_focus_padding_x}px; }}

    QPushButton#IconButton {{
        min-width: {CONST.icon_button_size}px; max-width: {CONST.icon_button_size}px; width: {CONST.icon_button_size}px;
        min-height: {CONST.icon_button_size}px; max-height: {CONST.icon_button_size}px; height: {CONST.icon_button_size}px;
        padding: 0px;
        border-radius: {radius}px;
        border: {border}px solid transparent;
        background: transparent;
        color: {c['secondary_text']};
    }}
    QPushButton#IconButton:hover {{ background: {hover_overlay}; border: {border}px solid transparent; color: {c['primary_text']}; }}
    QPushButton#IconButton:pressed {{ background: {c['nested_surface']}; border: {border}px solid transparent; color: {c['primary_text']}; }}
    QPushButton#IconButton[keyboardFocus="true"] {{ background: transparent; border: 2px solid {focus_ring_color}; padding: 0px; }}

    QPushButton#LinkButton {{
        background: transparent;
        border: {border}px solid transparent;
        color: {c['secondary_accent']};
        padding: 0px 4px;
        min-height: {CONST.link_button_height}px;
        max-height: {CONST.link_button_height}px;
        height: {CONST.link_button_height}px;
        font-size: {CONST.button_font_size}px;
    }}
    QPushButton#LinkButton:hover {{ background: transparent; border: {border}px solid transparent; color: {c['secondary_accent']}; text-decoration: underline; }}
    QPushButton#LinkButton:pressed {{ background: transparent; border: {border}px solid transparent; color: {c['secondary_accent']}; }}
    QPushButton#LinkButton[keyboardFocus="true"] {{ background: transparent; border: 2px solid {focus_ring_color}; padding: 0px 3px; }}

    QPushButton#NavItem {{
        height: {CONST.sidebar_item_height}px;
        min-height: {CONST.sidebar_item_height}px;
        max-height: {CONST.sidebar_item_height}px;
        padding: 2px 8px;
        margin: 0px {CONST.sidebar_scrollbar_gutter}px 0px 0px;
        text-align: left;
        border-radius: {radius}px;
        border: {border}px solid transparent;
        background: transparent;
        font-size: {CONST.sidebar_font_size}px;
        font-weight: 500;
        color: {c['secondary_text']};
        qproperty-iconSize: 16px 16px;
    }}
    QPushButton#NavItem:hover {{ background: {hover_overlay}; color: {c['primary_text']}; border: {border}px solid transparent; padding: 2px 8px; }}
    QPushButton#NavItem:pressed {{ background: {c['nested_surface']}; color: {c['primary_text']}; border: {border}px solid transparent; padding: 2px 8px; }}
    QPushButton#NavItem:checked {{ background: {nav_selected_bg}; color: {c['primary_text']}; border-left: 2px solid {c['secondary_accent']}; border-top: {border}px solid transparent; border-right: {border}px solid transparent; border-bottom: {border}px solid transparent; padding: 2px 8px 2px 6px; font-weight: 600; }}
    QPushButton#NavItem:checked:hover {{ background: {nav_selected_bg}; color: {c['primary_text']}; border-left: 2px solid {c['secondary_accent']}; border-top: {border}px solid transparent; border-right: {border}px solid transparent; border-bottom: {border}px solid transparent; padding: 2px 8px 2px 6px; font-weight: 600; }}
    QPushButton#NavItem[keyboardFocus="true"] {{ border: 2px solid {focus_ring_color}; padding: 1px 7px; }}
    QPushButton#NavItem:checked[keyboardFocus="true"] {{ background: {nav_selected_bg}; color: {c['primary_text']}; border: 2px solid {focus_ring_color}; padding: 1px 7px; font-weight: 600; }}

    QPushButton::menu-indicator {{ subcontrol-origin: padding; subcontrol-position: center right; width: 8px; right: 6px; }}

    QLineEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {{
        min-height: {CONST.input_height}px;
        max-height: {CONST.input_height}px;
        height: {CONST.input_height}px;
        border-radius: {radius}px;
        border: {border}px solid {input_border};
        border-style: solid;
        margin: 0px;
        background: {input_bg};
        color: {c['primary_text']};
        padding-left: {CONST.input_padding_x}px;
        padding-right: {CONST.input_padding_x}px;
        font-size: {TYPE['input']}px;
        font-weight: 400;
        selection-background-color: {c['selection']};
        selection-color: {c['primary_text']};
        placeholder-text-color: {placeholder_text};
    }}
    QTextEdit, QPlainTextEdit {{
        min-height: 96px;
        border-radius: {radius}px;
        border: {border}px solid {input_border};
        border-style: solid;
        margin: 0px;
        background: {input_bg};
        color: {c['primary_text']};
        padding: {CONST.text_area_padding_y}px {CONST.text_area_padding_x}px;
        font-size: {TYPE['input']}px;
        font-weight: 400;
        selection-background-color: {c['selection']};
        selection-color: {c['primary_text']};
        placeholder-text-color: {placeholder_text};
    }}
    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDateEdit:hover, QTimeEdit:hover {{
        border: {border}px solid {input_hover_border};
        background: {input_bg};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
        border: 1px solid {input_focus_border};
        background: {input_bg};
    }}
    QLineEdit[keyboardFocus="true"], QComboBox[keyboardFocus="true"], QSpinBox[keyboardFocus="true"], QDateEdit[keyboardFocus="true"], QTimeEdit[keyboardFocus="true"] {{
        border: 2px solid {input_focus_border};
        background: {input_bg};
        padding-left: {CONST.input_focus_padding_x}px;
        padding-right: {CONST.input_focus_padding_x}px;
    }}
    QTextEdit[keyboardFocus="true"], QPlainTextEdit[keyboardFocus="true"] {{
        border: 2px solid {input_focus_border};
        background: {input_bg};
        padding: {CONST.text_area_padding_y - 1}px {CONST.text_area_padding_x - 1}px;
    }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled {{
        color: {input_disabled_text};
        background: {input_disabled_bg};
        border-color: {input_disabled_border};
    }}
    QLineEdit#SearchInput {{
        padding-left: {CONST.search_padding_left}px;
        padding-right: {CONST.search_padding_right}px;
    }}
    QLineEdit#SearchInput[keyboardFocus="true"] {{
        border: 2px solid {input_focus_border};
        padding-left: {CONST.search_padding_left - 1}px;
        padding-right: {CONST.search_padding_right - 1}px;
    }}
    QLineEdit#PasswordInput {{
        padding-left: {CONST.password_padding_left}px;
        padding-right: {CONST.password_padding_right}px;
    }}
    QLineEdit#PasswordInput[keyboardFocus="true"] {{
        border: 2px solid {input_focus_border};
        padding-left: {CONST.password_padding_left - 1}px;
        padding-right: {CONST.password_padding_right - 1}px;
    }}
    QLineEdit#ErrorInput, QTextEdit#ErrorInput {{ border: 1px solid {c['danger']}; }}
    QLineEdit#ValidInput {{ border: 1px solid {c['success']}; }}
    QLineEdit#ReadOnlyInput {{ color: {c['secondary_text']}; background: {c['surface']}; }}
    QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{ width: 28px; border: none; background: transparent; }}
    QSpinBox::up-button, QSpinBox::down-button, QDateEdit::up-button, QDateEdit::down-button, QTimeEdit::up-button, QTimeEdit::down-button {{ width: 18px; border: none; background: transparent; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {hover_overlay}; }}
    QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['primary_text']}; border: 1px solid {input_border}; selection-background-color: {c['selection']}; selection-color: {c['primary_text']}; }}
    QAbstractItemView {{ background: {c['surface']}; color: {c['primary_text']}; border: 1px solid {input_border}; selection-background-color: {c['selection']}; selection-color: {c['primary_text']}; outline: 0; }}

    QCheckBox, QRadioButton {{
        color: {c['primary_text']};
        font-size: {TYPE['body']}px;
        spacing: 8px;
    }}
    QCheckBox::indicator {{ width: {CONST.selection_indicator_size}px; height: {CONST.selection_indicator_size}px; border-radius: 4px; border: 1px solid {checkbox_border}; background: {c['window_background']}; }}
    QCheckBox::indicator:hover {{ border: 1px solid {selection_control_hover_border}; background: {c['window_background']}; }}
    QCheckBox::indicator:checked {{ background: {selection_control_checked_bg}; border: 1px solid {selection_control_checked_bg}; image: url("{check_icon}"); }}
    QCheckBox::indicator:checked:hover {{ background: {selection_control_checked_hover_bg}; border: 1px solid {selection_control_checked_hover_bg}; image: url("{check_icon}"); }}
    QCheckBox::indicator:indeterminate {{ background: {selection_control_checked_bg}; border: 1px solid {selection_control_checked_bg}; image: url("{minus_icon}"); }}
    QCheckBox::indicator:disabled {{ background: {selection_control_disabled_bg}; border-color: {selection_control_disabled_border}; }}
    QRadioButton::indicator {{ width: {CONST.selection_indicator_size}px; height: {CONST.selection_indicator_size}px; border-radius: {CONST.selection_indicator_size // 2}px; border: 1px solid {checkbox_border}; background: {c['window_background']}; }}
    QRadioButton::indicator:hover {{ border: 1px solid {selection_control_hover_border}; background: {c['window_background']}; }}
    QRadioButton::indicator:checked {{ background: {selection_control_checked_bg}; border: 3px solid {c['window_background']}; outline: 1px solid {selection_control_checked_bg}; }}
    QCheckBox[keyboardFocus="true"], QRadioButton[keyboardFocus="true"] {{ color: {c['primary_text']}; }}
    QCheckBox[keyboardFocus="true"]::indicator {{ border: 2px solid {focus_ring_color}; }}
    QRadioButton[keyboardFocus="true"]::indicator {{ border: 2px solid {focus_ring_color}; }}

    QWidget#ToggleRow {{
        background: transparent;
        border: none;
        min-height: {CONST.toggle_height}px;
        max-height: {CONST.toggle_height + 6}px;
    }}
    QCheckBox#ToggleSwitch {{
        min-width: {CONST.toggle_width}px;
        max-width: {CONST.toggle_width}px;
        min-height: {CONST.toggle_height}px;
        max-height: {CONST.toggle_height}px;
        background: transparent;
        border: none;
        padding: 0px;
        margin: 0px;
        spacing: 0px;
    }}
    QCheckBox#ToggleSwitch::indicator {{ width: 0px; height: 0px; }}

    QSlider::groove:horizontal {{ height: 4px; background: {c['border']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ width: 14px; margin: -5px 0; border-radius: 7px; background: {c['primary']}; }}
    QSlider[keyboardFocus="true"]::handle:horizontal {{ border: 2px solid {focus_ring_color}; }}

    QFrame#DataToolbar {{ background: transparent; border: none; min-height: {CONST.data_toolbar_height}px; max-height: {CONST.data_toolbar_height}px; }}
    QFrame#DataTable {{ background: transparent; border: none; border-radius: 0px; }}
    QFrame#TableHeaderRow {{ background: {table_header_bg}; border-top: 1px solid {table_row_border}; border-bottom: 1px solid {table_row_border}; min-height: {CONST.table_header_height}px; max-height: {CONST.table_header_height}px; }}
    QFrame#TableRow {{ background: transparent; border-bottom: 1px solid {table_row_border}; min-height: {CONST.data_table_row_height}px; max-height: {CONST.data_table_row_height}px; }}
    QFrame#TableRow:hover {{ background: {row_hover_overlay}; }}
    QFrame#TableRowSelected {{ background: {selected_subtle}; border-left: 2px solid {selected_row_indicator}; border-bottom: 1px solid {table_row_border}; min-height: {CONST.data_table_row_height}px; max-height: {CONST.data_table_row_height}px; }}
    QFrame#TableRowSelected:hover {{ background: {selected_row_hover_bg}; border-left: 2px solid {selected_row_indicator}; border-bottom: 1px solid {table_row_border}; }}
    QFrame#TableRowSelected QLabel#TableCell {{ color: {c['primary_text']}; }}
    QFrame#TableRowSelected QLabel#TableCellMuted {{ color: {c['secondary_text']}; }}
    QFrame#TableRowSelected QLabel#TableActionCell {{ color: {table_action_text}; }}
    QLabel#TableActionCell {{ font-size: {TYPE['table_data']}px; font-weight: {TYPO_RUNTIME.get("action_text_weight", 500)}; color: {table_action_text}; }}

    QTableWidget#InvoiceProductGrid {{
        background: transparent;
        border: none;
        gridline-color: transparent;
        color: {c['primary_text']};
        selection-background-color: {selected_subtle};
        selection-color: {c['primary_text']};
        outline: 0;
        font-size: {TYPE['table_data']}px;
    }}
    QTableWidget#InvoiceProductGrid::item {{
        min-height: {CONST.data_table_row_height}px;
        max-height: {CONST.data_table_row_height}px;
        padding: 0px {CONST.table_cell_padding_x}px;
        border-bottom: 1px solid {table_row_border};
        color: {c['primary_text']};
    }}
    QTableWidget#InvoiceProductGrid::item:hover {{ background: {row_hover_overlay}; }}
    QTableWidget#InvoiceProductGrid::item:selected {{
        background: {selected_subtle};
        color: {c['primary_text']};
    }}
    QHeaderView::section {{
        background: {table_header_bg};
        color: {table_header_text};
        border: none;
        border-top: 1px solid {table_row_border};
        border-bottom: 1px solid {table_row_border};
        padding: 0px {CONST.table_cell_padding_x}px;
        min-height: {CONST.table_header_height}px;
        max-height: {CONST.table_header_height}px;
        font-size: {TYPE['table_header']}px;
        font-weight: {table_header_weight};
    }}



    QPlainTextEdit#LogViewer {{
        min-height: 128px;
        border-radius: 8px;
        border: 1px solid {c['border']};
        background: {c['window_background']};
        color: {c['primary_text']};
        padding: {CONST.text_area_padding_y}px {CONST.text_area_padding_x}px;
        font-size: {TYPE['table_data']}px;
        font-weight: 400;
        line-height: 18px;
        selection-background-color: {c['selection']};
        selection-color: {c['primary_text']};
    }}
    QPlainTextEdit#LogViewer:focus {{
        border: 1px solid {c['secondary_accent']};
        background: {c['window_background']};
    }}
    QPlainTextEdit#LogViewer[keyboardFocus="true"] {{
        border: 2px solid {focus_ring_color};
        background: {c['window_background']};
        padding: {CONST.text_area_padding_y - 1}px {CONST.text_area_padding_x - 1}px;
    }}

    QTreeWidget#FileTree {{
        background: transparent;
        border: none;
        border-radius: 0px;
        color: {c['primary_text']};
        outline: 0;
        show-decoration-selected: 0;
        font-size: {TYPE['table_data']}px;
    }}
    QTreeWidget#FileTree::item {{
        min-height: {CONST.file_row_height}px;
        height: {CONST.file_row_height}px;
        padding: 0px 8px;
        border-left: 1px dotted {tree_guide};
        border-bottom: 1px solid {nested_border};
        color: {c.get('file_tree_file_text', c['secondary_text'])};
        background: transparent;
    }}
    QTreeWidget#FileTree::item:hover {{
        background: {file_tree_hover_bg};
    }}
    QTreeWidget#FileTree::item:selected {{
        background: {file_tree_selected_bg};
        color: {c['primary_text']};
        border-left: 2px solid {selected_row_indicator};
        border-bottom: 1px solid {nested_border};
    }}
    QTreeWidget#FileTree::branch {{
        background: transparent;
        border-left: 1px dotted {tree_guide};
        width: 14px;
    }}
    QTreeWidget#FileTree::branch:has-children:closed {{ image: url("{chevron_right}"); }}
    QTreeWidget#FileTree::branch:has-children:open {{ image: url("{chevron_down}"); }}
    QTreeWidget#FileTree::branch:!has-children {{ image: none; }}
    QTreeWidget#FileTree[keyboardFocus="true"] {{
        border: 2px solid {focus_ring_color};
        border-radius: {radius}px;
    }}
    QHeaderView::section {{
        background: {table_header_bg};
        color: {table_header_text};
        font-size: {TYPE['table_header']}px;
        font-weight: 600;
        min-height: {CONST.table_header_height}px;
        max-height: {CONST.table_header_height}px;
        padding: 0px {CONST.button_padding_x}px;
        border: none;
        border-top: 1px solid {c['border']};
        border-bottom: 1px solid {c['border']};
        font-size: {TYPE['table_header']}px;
        font-weight: 600;
    }}
    QTreeWidget#FileTree QHeaderView::section {{
        background: {file_tree_header_bg};
        color: {muted_text};
        border-top: none;
        border-bottom: 1px solid {nested_border};
        font-size: {TYPE['table_header']}px;
        font-weight: 500;
    }}

    QProgressBar {{
        background: {c['border']};
        border: none;
        border-radius: 3px;
        min-height: 6px;
        max-height: 10px;
        text-align: center;
        color: {c['primary_text']};
    }}
    QProgressBar::chunk {{ background: {c['primary']}; border-radius: 3px; }}

    QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: {radius}px; background: {c['surface']}; }}
    QTabBar::tab {{ background: transparent; color: {c['secondary_text']}; padding: 6px 12px; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {c['primary_text']}; border-bottom: 2px solid {c['primary']}; }}
    QTabBar::tab:hover {{ color: {c['primary_text']}; }}
    QTabBar[keyboardFocus="true"]::tab:selected {{ border-bottom: 2px solid {focus_ring_color}; }}



    /* Step-31 scoped demo navigation: internal examples must never inherit the
       real Sidebar NavItem active/scrollbar contract. */
    QFrame#DemoNavigationPanel {{
        background: {c['surface']};
        border: {border}px solid {c['border']};
        border-radius: {radius}px;
    }}
    QFrame#DemoTabRail {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {c['border']};
        min-height: 30px;
        max-height: 30px;
    }}
    QLabel#DemoTabActive {{
        color: {c['primary_text']};
        font-size: {TYPE['body']}px;
        font-weight: 500;
        padding: 0px 2px 7px 2px;
        border-bottom: 2px solid {c['primary']};
    }}
    QLabel#DemoTab {{
        color: {c['secondary_text']};
        font-size: {TYPE['body']}px;
        font-weight: 400;
        padding: 0px 2px 7px 2px;
        border-bottom: 2px solid transparent;
    }}
    QLabel#DemoTab:hover {{
        color: {c['primary_text']};
    }}
    QPushButton#DemoTabActiveButton, QPushButton#DemoTabButton {{
        background: transparent;
        border: none;
        border-radius: 0px;
        min-height: 30px;
        max-height: 30px;
        padding: 0px 2px 7px 2px;
        text-align: left;
        font-size: {TYPE['body']}px;
    }}
    QPushButton#DemoTabActiveButton {{
        color: {c['primary_text']};
        font-weight: 500;
        border-bottom: 2px solid {c['primary']};
    }}
    QPushButton#DemoTabButton {{
        color: {c['secondary_text']};
        font-weight: 400;
        border-bottom: 2px solid transparent;
    }}
    QPushButton#DemoTabButton:hover, QPushButton#DemoTabActiveButton:hover {{
        color: {c['primary_text']};
        background: transparent;
        border-top: none;
        border-left: none;
        border-right: none;
    }}
    QPushButton#DemoTabActiveButton[keyboardFocus="true"], QPushButton#DemoTabButton[keyboardFocus="true"] {{
        border-bottom: 2px solid {focus_ring_color};
    }}
    QWidget#FlatPreviewTabGroup, QStackedWidget#FlatPreviewStack {{
        background: transparent;
        border: none;
    }}
    QWidget#ActionRow, QWidget#ButtonRow {{
        background: transparent;
        border: none;
    }}



    /* Step-31 compact Workflow Canvas workspace.
       Full-page primary canvas, clean top workflow bar, popup node library,
       hidden-by-default inspector, floating bottom toolbar, zoom/minimap and
       node selection toolbar. No panel/card shell around the canvas. */
    QFrame#WorkflowTopBar {{
        background: {c['surface']};
        border: none;
        border-bottom: {border}px solid {c['border']};
        border-radius: 0px;
        min-height: {CONST.workflow_topbar_height}px;
        max-height: {CONST.workflow_topbar_height}px;
    }}
    QFrame#WorkflowToolbar {{
        background: {c['surface']};
        border: {border}px solid {c['border']};
        border-radius: {radius}px;
    }}
    QFrame#WorkflowWorkspace {{
        background: {c['window_background']};
        border: none;
        border-radius: 0px;
    }}
    QFrame#WorkflowPalette {{
        background: {c['surface']};
        border: none;
        border-right: {border}px solid {c['border']};
        border-radius: 0px;
    }}
    QWidget#WorkflowPaletteContent, QWidget#WorkflowPaletteBody {{
        background: transparent;
        border: none;
    }}
    QFrame#WorkflowPaletteSection {{
        background: transparent;
        border: none;
    }}
    QFrame#WorkflowNodeLibraryPopup {{
        background: {_rgba_from_hex(c['surface'], 0.98)};
        border: {border}px solid {outline_border};
        border-radius: {radius}px;
    }}
    QPushButton#WorkflowPaletteItem {{
        height: {CONST.workflow_palette_item_height}px;
        min-height: {CONST.workflow_palette_item_height}px;
        max-height: {CONST.workflow_palette_item_height}px;
        padding: 0px 8px;
        text-align: left;
        background: transparent;
        border: {border}px solid transparent;
        border-radius: {radius}px;
        color: {c['secondary_text']};
        font-size: {CONST.button_font_size}px;
    }}
    QPushButton#WorkflowPaletteItem:hover {{
        background: {hover_overlay};
        border: {border}px solid {outline_border};
        color: {c['primary_text']};
    }}
    QFrame#WorkflowCanvasColumn {{
        background: {c['window_background']};
        border: none;
    }}
    QFrame#WorkflowCanvas {{
        background: {c['window_background']};
        border: none;
        border-radius: 0px;
    }}
    QFrame#WorkflowCanvas:hover {{
        border: none;
    }}
    QFrame#WorkflowFloatingControls,
    QFrame#WorkflowZoomPanel,
    QFrame#WorkflowNodeToolbar {{
        background: {_rgba_from_hex(c['surface'], 0.96)};
        border: {border}px solid {c['border']};
        border-radius: {radius}px;
    }}
    QFrame#WorkflowFloatingControls QPushButton,
    QFrame#WorkflowZoomPanel QPushButton,
    QFrame#WorkflowNodeToolbar QPushButton {{
        min-height: 26px;
        max-height: 26px;
        height: 26px;
        padding: 0px 7px;
        font-size: {CONST.button_font_size}px;
    }}
    QFrame#WorkflowFloatingControls QPushButton:hover,
    QFrame#WorkflowZoomPanel QPushButton:hover,
    QFrame#WorkflowNodeToolbar QPushButton:hover {{
        background: {workflow_control_hover_bg};
    }}
    QFrame#WorkflowFloatingControls QPushButton:pressed,
    QFrame#WorkflowZoomPanel QPushButton:pressed,
    QFrame#WorkflowNodeToolbar QPushButton:pressed {{
        background: {workflow_control_pressed_bg};
    }}
    QPushButton#WorkflowInspectorHandle {{
        min-width: 34px;
        max-width: 34px;
        border-radius: 0px;
        border-left: {border}px solid {c['border']};
        border-right: {border}px solid {c['border']};
        background: {c['surface']};
        color: {c['secondary_text']};
        padding: 0px 4px;
    }}
    QPushButton#WorkflowInspectorHandle:hover {{
        background: {hover_overlay};
        color: {c['primary_text']};
    }}
    QFrame#WorkflowStatusBar {{
        background: {c['surface']};
        border: none;
        border-top: {border}px solid {c['border']};
        border-radius: 0px;
        min-height: 28px;
        max-height: 28px;
    }}
    QFrame#WorkflowMiniMap {{
        background: {_rgba_from_hex(c['window_background'], 0.94)};
        border: {border}px solid {c['border']};
        border-radius: {radius}px;
    }}
    QFrame#WorkflowInspector {{
        background: {c['surface']};
        border: none;
        border-left: {border}px solid {c['border']};
        border-radius: 0px;
    }}
    QFrame#WorkflowNode QLabel#WorkflowNodeIcon,
    QFrame#WorkflowNodeSelected QLabel#WorkflowNodeIcon,
    QFrame#WorkflowNodeRunning QLabel#WorkflowNodeIcon,
    QFrame#WorkflowNodeSuccess QLabel#WorkflowNodeIcon,
    QFrame#WorkflowNodeError QLabel#WorkflowNodeIcon,
    QFrame#WorkflowNodeDisabled QLabel#WorkflowNodeIcon {{
        font-size: {CONST.workflow_node_icon_size}px;
        font-weight: 600;
        color: {c['secondary_accent']};
        min-width: {CONST.workflow_node_icon_size}px;
        max-width: {CONST.workflow_node_icon_size}px;
    }}
    QFrame#WorkflowNode QLabel#WorkflowNodeTitle,
    QFrame#WorkflowNodeSelected QLabel#WorkflowNodeTitle,
    QFrame#WorkflowNodeRunning QLabel#WorkflowNodeTitle,
    QFrame#WorkflowNodeSuccess QLabel#WorkflowNodeTitle,
    QFrame#WorkflowNodeError QLabel#WorkflowNodeTitle,
    QFrame#WorkflowNodeDisabled QLabel#WorkflowNodeTitle {{
        font-size: {CONST.workflow_node_title_font_size}px;
        font-weight: 600;
        color: {c.get('workflow_node_text', c['primary_text'])};
    }}

    QFrame#WorkflowNode, QFrame#WorkflowNodeSelected,
    QFrame#WorkflowNodeRunning, QFrame#WorkflowNodeSuccess,
    QFrame#WorkflowNodeError, QFrame#WorkflowNodeDisabled {{
        background: {c['surface']};
        border: {border}px solid {outline_border};
        border-top: {border}px solid {node_top_highlight};
        border-radius: {radius}px;
    }}
    QFrame#WorkflowNode:hover {{
        background: {c['nested_surface']};
        border: {border}px solid {outline_border};
        border-top: {border}px solid {node_top_highlight};
    }}
    QFrame#WorkflowNodeSelected {{
        background: {selected_subtle};
        border: 2px solid {c['secondary_accent']};
    }}
    QFrame#WorkflowNodeRunning {{
        background: {subtle_primary};
        border: 2px solid {c['primary']};
    }}
    QFrame#WorkflowNodeSuccess {{
        background: {_rgba_from_hex(c['success'], 0.10)};
        border: {border}px solid {c['success']};
    }}
    QFrame#WorkflowNodeError {{
        background: {_rgba_from_hex(c['danger'], 0.10)};
        border: {border}px solid {c['danger']};
    }}
    QFrame#WorkflowNodeDisabled {{
        background: {c['surface']};
        border: {border}px solid {c['border']};
    }}
    QFrame#PluginCard {{
        background: {c['surface']};
        border: {border}px solid {nested_border};
        border-radius: {radius}px;
    }}
    QFrame#PluginCard:hover {{
        border: {border}px solid {plugin_card_hover_border};
        background: {plugin_card_hover_background};
    }}
    QLabel#PluginCardTitle {{
        font-size: 13px;
        font-weight: {card_title_weight};
        color: {plugin_title_text};
        line-height: {card_title_line_height}px;
    }}
    QLabel#PluginCardDescription {{
        font-size: 11px;
        font-weight: 400;
        color: {plugin_body_text};
        line-height: {caption_line_height}px;
    }}
    QLabel#PluginCategoryChip {{
        background: {plugin_chip_background};
        color: {plugin_chip_text};
        border: 1px solid {plugin_chip_border};
        border-radius: {CONST.badge_radius}px;
        padding: {CONST.badge_padding_y}px {CONST.badge_padding_x}px;
        font-size: {CONST.badge_font_size}px;
        font-weight: 600;
    }}
    QPlainTextEdit#ChatTranscript {{
        min-height: {CONST.chat_transcript_min_height}px;
        border-radius: {radius}px;
        border: {border}px solid {c['border']};
        background: {c['window_background']};
        color: {c['primary_text']};
        padding: {CONST.text_area_padding_y}px {CONST.text_area_padding_x}px;
        font-size: {TYPE['table_data']}px;
        selection-background-color: {c['selection']};
        selection-color: {c['primary_text']};
    }}
    QPlainTextEdit#ChatTranscript:focus {{
        border: {border}px solid {c['secondary_accent']};
        background: {c['window_background']};
    }}
    QPlainTextEdit#ChatTranscript[keyboardFocus="true"] {{
        border: 2px solid {focus_ring_color};
        padding: {CONST.text_area_padding_y - 1}px {CONST.text_area_padding_x - 1}px;
    }}


    QDialog#ModalDialog {{
        background: {modal_background};
        border: 1px solid {modal_border};
    }}

    QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: {radius}px; padding: 4px; color: {c['primary_text']}; }}
    QToolTip {{ background: {tooltip_background}; color: {tooltip_text}; border: 1px solid {tooltip_border}; border-radius: 6px; padding: 4px 6px; }}
    QMenu::item {{ padding: 6px 18px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {menu_item_hover_bg}; color: {c['primary_text']}; }}

    QToolBar {{
        background: {c['window_background']};
        border: none;
        spacing: 8px;
        padding: 0px;
        min-height: {CONST.icon_button_size}px;
        max-height: {CONST.icon_button_size}px;
    }}
    QToolButton {{ background: transparent; color: {c['secondary_text']}; border: none; border-radius: {radius}px; padding: 0px; min-width: {CONST.icon_button_size}px; max-width: {CONST.icon_button_size}px; min-height: {CONST.icon_button_size}px; max-height: {CONST.icon_button_size}px; }}
    QToolButton:hover {{ background: {hover_overlay}; color: {c['primary_text']}; border: none; }}
    QToolButton:pressed {{ background: {c['nested_surface']}; color: {c['primary_text']}; border: none; }}
    QToolButton:focus {{ background: transparent; border: none; }}
    QToolButton[keyboardFocus="true"] {{ background: transparent; border: 2px solid {focus_ring_color}; }}

    QStatusBar {{ background: {c['window_background']}; border-top: 1px solid {c['border']}; min-height: {CONST.status_bar_height}px; max-height: {CONST.status_bar_height}px; color: {c.get('shell_caption_text', c['secondary_text'])}; }}
    QStatusBar QLabel {{ font-size: {TYPE['status']}px; color: {c.get('shell_caption_text', c['secondary_text'])}; }}

    QSplitter::handle {{ background: {c['border']}; }}
    QSplitter::handle:horizontal {{ width: 4px; }}
    QSplitter::handle:vertical {{ height: 4px; }}

    QDockWidget {{ background: {c['window_background']}; border: 1px solid {c['border']}; color: {c['primary_text']}; }}
    QDockWidget::title {{ background: {c['window_background']}; padding: 7px 10px; border-bottom: 1px solid {c['border']}; font-size: {CONST.card_title_font_size}px; font-weight: 600; }}

    /* Step 19 official scrollbar rule: thin-minimal, visible only when needed. */
    QScrollBar:vertical {{
        width: {CONST.scrollbar_thickness}px;
        background: transparent;
        margin: 2px 0px 2px 0px;
        border: none;
    }}
    QWidget#Sidebar QScrollBar:vertical {{
        width: {CONST.scrollbar_thickness}px;
        background: transparent;
        margin: 2px 0px 2px {CONST.sidebar_scrollbar_inner_gap}px;
        border: none;
    }}
    QScrollBar:horizontal {{
        height: {CONST.scrollbar_thickness}px;
        background: transparent;
        margin: 0px 2px 0px 2px;
        border: none;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {c['border']};
        border-radius: 3px;
        min-height: 28px;
        min-width: 28px;
    }}
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background: {c['secondary_text']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
        height: 0px;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    """
