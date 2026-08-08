"""Central Vib Tools Desktop UI design contract.

Step-40B keeps the Step-39B/Step-40 Invoice baseline and applies only the
scope-locked Text Spacing Breathing Repair layer. The contract preserves all
approved colors, component heights, accessibility, responsive guardrails and
Invoice Details functionality while centralizing the global login form contract
rhythm after the over-compact density pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "frozen_design_source"
TOKENS_FILE = SOURCE_ROOT / "CURRENT_FOUNDATION_TOKENS.json"

DEFAULT_TOKENS = {
    "brand_identity": {
        "logo_blue": "#0053FC",
        "logo_cyan": "#00BFFD",
        "usage": "Brand identity only: logo, splash, welcome, about dialog, installer, website/brand material. Not general UI background.",
    },
    "theme": {"name": "Vib Tools / Vibrix Dark", "mode": "dark_first", "strategy": "token_driven"},
    "colors": {
        "window_background": "#090D14",
        "page_background": "#090D14",
        "surface": "#111722",
        "nested_surface": "#1A212E",
        "surface_hover": "#1A212E",
        "border": "#1E2633",
        "nested_border": "#1E2633",
        "input_background": "#161D2A",
        "input_border": "#2D3748",
        "input_border_emphasis": "#2D3748",
        "input_focus_border": "#38BDF8",
        "button_primary_border": "rgba(255,255,255,38)",
        "button_secondary_background": "#1A212E",
        "button_secondary_border": "#283345",
        "button_outline_border": "#283345",
        "table_header_background": "#111620",
        "table_header_text": "#64748B",
        "field_label": "#E2E8F0",
        "muted_text": "#64748B",
        "checkbox_border": "#30363D",
        "selected_row_bg": "rgba(47,111,235,38)",
        "selected_row_indicator": "#38BDF8",
        "button_hover_overlay": "rgba(255,255,255,13)",
        "primary_hover": "#3B82F6",
        "plugin_chip_background": "rgba(56,189,248,20)",
        "plugin_chip_border": "rgba(56,189,248,61)",
        "primary": "#2F6FEB",
        "secondary_accent": "#38BDF8",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "primary_text": "#F8FAFC",
        "secondary_text": "#94A3B8",
        "selection": "rgba(47,111,235,38)",
        "selection_overlay_alpha": 0.15,
        "selection_human_readable": "rgba(47,111,235,0.15)",
        "nav_selected_bg": "rgba(47,111,235,31)",
        "disabled": "#484F58",
        "hover_overlay": "rgba(255,255,255,13)",
        "row_hover_overlay": "rgba(255,255,255,8)",
        "tree_guide": "rgba(35,43,56,102)",
        "toggle_off": "#1E2633",
        "node_top_highlight": "rgba(255,255,255,0.08)",
    },
    "typography": {
        "primary_ui_font": "Segoe UI Variable",
        "fallback_ui_font": "Segoe UI",
        "font_priority": ["Segoe UI Variable", "Segoe UI", "System Default"],
        "weights": {"regular": 400, "medium": 500, "semibold": 600},
    },
    "font_size_compact_px": {
        "app_title": 20,
        "page_title": 16,
        "section_title": 14,
        "card_title": 14,
        "body": 13,
        "button": 12,
        "input": 13,
        "sidebar": 12,
        "table_header": 11,
        "table_data": 12,
        "status": 11,
        "caption": 11,
    },
    "spacing": {
        "base_grid_px": 8,
        "allowed_scale_px": [4, 8, 16, 24, 32, 40, 48],
        "rule": "Use tokenized spacing only; do not invent random padding/margin.",
    },
    "radius": {"common_component_radius_px": 8, "approved_tokens": ["XS", "SM", "MD", "LG", "XL"]},
    "border": {"default_color": "#1E2633", "common_width_px": 1, "rule": "Use subtle tokenized border."},
    "shadow": {"default": "none", "heavy_shadow": "prohibited", "allowed_only_for": ["dialog", "popup", "menu", "floating_panel"]},
    "iconography": {
        "recommended_sizes_px": [16, 20, 24, 32],
        "component_common_sizes_px": [12, 14, 16, 18, 20, 24, 32],
        "rule": "Use one consistent icon library; status icon color must follow semantic tokens.",
    },
}


STEP31_RUNTIME_OVERRIDES = {
    "colors": {
        "nested_surface": "#1A212E",
        "surface_hover": "#1A212E",
        "selection": "rgba(47,111,235,31)",
        "disabled": "#484F58",
    },
    "font_size_compact_px": {
        "page_title": 16,
        "section_title": 14,
        "card_title": 14,
        "table_header": 11,
    },
}
STEP32_RUNTIME_OVERRIDES = {
    "colors": {
        "window_background": "#090D14",
        "page_background": "#0D121C",
        "surface": "#131923",
        "nested_surface": "#1A212E",
        "surface_hover": "#1A212E",
        "border": "#232B38",
        "nested_border": "#1D2430",
        "input_border": "#232B38",
        "input_border_emphasis": "#283242",
        "button_outline_border": "rgba(255,255,255,26)",
        "table_header_background": "#111620",
        "table_header_text": "#64748B",
        "field_label": "#E2E8F0",
        "muted_text": "#64748B",
        "checkbox_border": "#30363D",
        "selected_row_bg": "rgba(47,111,235,38)",
        "selected_row_indicator": "#38BDF8",
        "button_hover_overlay": "rgba(255,255,255,13)",
        "primary_hover": "#3B82F6",
        "plugin_chip_background": "rgba(56,189,248,20)",
        "plugin_chip_border": "rgba(56,189,248,61)",
        "primary": "#2F6FEB",
        "secondary_text": "#94A3B8",
        "selection": "rgba(47,111,235,38)",
        "selection_overlay_alpha": 0.15,
        "selection_human_readable": "rgba(47,111,235,0.15)",
        "nav_selected_bg": "rgba(47,111,235,31)",
        "hover_overlay": "rgba(255,255,255,13)",
        "row_hover_overlay": "rgba(255,255,255,8)",
        "tree_guide": "rgba(35,43,56,102)",
        "toggle_off": "#232B38",
        "node_top_highlight": "rgba(255,255,255,0.08)",
    },
    "border": {"default_color": "#232B38"},
}

STEP32A_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-32A: component state + text hierarchy polish.
        # Color-only/state-only patch; dimensions/features/pages remain Step-32.
        "selection": "rgba(47,111,235,38)",
        "selection_overlay_alpha": 0.15,
        "selection_human_readable": "rgba(47,111,235,0.15)",
        "selected_row_bg": "rgba(47,111,235,38)",
        "selected_row_indicator": "#38BDF8",
        "table_header_text": "#64748B",
        "muted_text": "#64748B",
        "field_label": "#E2E8F0",
        "input_border": "#232B38",
        "input_border_emphasis": "#283242",
        "checkbox_border": "#30363D",
        "button_outline_border": "rgba(255,255,255,26)",
        "button_hover_overlay": "rgba(255,255,255,13)",
        "primary_hover": "#3B82F6",
        "plugin_chip_background": "rgba(56,189,248,20)",
        "plugin_chip_border": "rgba(56,189,248,61)",
    }
}

STEP32B_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-32B scope lock: color-only polish for buttons, forms/inputs,
        # cards/sections and plugin internals. No feature removal and no size
        # growth; global button height tightens to 28px via CONST.
        "window_background": "#090D14",
        "page_background": "#090D14",
        "surface": "#111722",
        "form_card_background": "#111722",
        "nested_surface": "#1A212E",
        "surface_hover": "#1A212E",
        "border": "#1E2633",
        "nested_border": "#1E2633",
        "input_background": "#161D2A",
        "input_border": "#2D3748",
        "input_border_emphasis": "#2D3748",
        "input_focus_border": "#38BDF8",
        "button_primary_border": "rgba(255,255,255,38)",
        "button_secondary_background": "#1A212E",
        "button_secondary_border": "#283345",
        "button_outline_border": "#283345",
        "plugin_chip_background": "rgba(56,189,248,20)",
        "plugin_chip_border": "rgba(56,189,248,61)",
    },
    "border": {"default_color": "#1E2633"},
}

STEP32C_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-32C scope lock: desaturated button/action colors, muted
        # form/control typography, softer plugin pills and no size growth.
        "primary": "#2563EB",
        "primary_hover": "#3B82F6",
        "button_primary_border": "rgba(255,255,255,31)",
        "button_active_background": "rgba(37,99,235,31)",
        "selection": "rgba(37,99,235,38)",
        "selected_row_bg": "rgba(37,99,235,38)",
        "nav_selected_bg": "rgba(37,99,235,31)",
        "danger": "#B91C1C",
        "danger_hover": "#991B1B",
        "danger_soft": "rgba(185,28,28,31)",
        "title_text": "#F1F5F9",
        "card_title_text": "#F1F5F9",
        "section_title_text": "#F1F5F9",
        "body_text": "#94A3B8",
        "field_label": "#94A3B8",
        "form_label": "#94A3B8",
        "toggle_on": "#2563EB",
        "toggle_on_border": "#3B82F6",
        "plugin_chip_background": "#1E293B",
        "plugin_chip_border": "#1E293B",
        "plugin_chip_text": "#94A3B8",
        "plugin_status_available_bg": "#1E293B",
        "plugin_status_available_border": "#263244",
        "plugin_status_available_text": "#94A3B8",
        "plugin_status_installed_bg": "rgba(22,101,52,64)",
        "plugin_status_installed_border": "rgba(34,197,94,76)",
        "plugin_status_installed_text": "#86EFAC",
    }
}

STEP32D_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-32D scope lock: no geometry growth. Typography is made lighter,
        # file-tree selection becomes IDE-style, and plugin/auth micro-copy uses
        # one centralized color hierarchy.
        "title_text": "#F1F5F9",
        "card_title_text": "#F1F5F9",
        "section_title_text": "#F1F5F9",
        "body_text": "#94A3B8",
        "form_label": "#94A3B8",
        "plugin_title_text": "#F1F5F9",
        "plugin_body_text": "#94A3B8",
        "file_tree_selected_bg": "rgba(37,99,235,26)",
        "file_tree_hover_bg": "rgba(255,255,255,8)",
        "file_tree_header_bg": "transparent",
        "folder_icon_color": "#D6B46A",
        "file_icon_color": "#7A879A",
    },
    "font_size_compact_px": {
        "page_title": 15,
        "section_title": 13,
        "body": 12,
    },
}

STEP32E_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-32E scope lock: final readability polish only. No new component
        # size, feature, page, structural or palette-family change is introduced.
        # Secondary/supporting copy becomes clearer on dark surfaces while the
        # Step-32D primary/card/background tokens remain intact.
        "secondary_text": "#CBD5E1",
        "body_text": "#CBD5E1",
        "muted_text": "#CBD5E1",
        "field_label": "#CBD5E1",
        "form_label": "#CBD5E1",
        "placeholder_text": "#CBD5E1",
        "breadcrumb_text": "#CBD5E1",
        "plugin_body_text": "#CBD5E1",
    },
    "typography_runtime": {
        "page_title_weight": 600,
        "section_title_weight": 600,
        "card_title_weight": 600,
        "body_weight": 400,
        "small_label_weight": 500,
        "page_title_line_height": 18,
        "section_title_line_height": 16,
        "card_title_line_height": 16,
        "body_line_height": 15,
        "caption_line_height": 14,
    },
}


STEP32F_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-32F scope lock: color-only/readability polish over Step-32E.
        # No geometry, font-size, layout, grid, page or feature changes.
        "secondary_text": "#CBD5E1",
        "body_text": "#CBD5E1",
        "muted_text": "#CBD5E1",
        "field_label": "#CBD5E1",
        "form_label": "#CBD5E1",
        "placeholder_text": "#CBD5E1",
        "breadcrumb_text": "#CBD5E1",
        "plugin_body_text": "#CBD5E1",
        "table_header_text": "#CBD5E1",
        "plugin_status_available_text": "#CBD5E1",
        "plugin_status_available_bg": "#1E293B",
        "plugin_status_available_border": "#334155",
        "status_badge_offline_text": "#CBD5E1",
        "status_badge_offline_bg": "#1E293B",
        "status_badge_offline_border": "#334155",
        "modal_background": "#1A212E",
        "modal_border": "#1E2633",
        "selection_human_readable": "rgba(37,99,235,0.15)",
    },
    "font_size_compact_px": {
        "card_title": 13,
    },
    "typography_runtime": {
        "table_header_weight": 600,
    },
}

STEP33_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-33: no palette redesign. Preserve Step-32F tokens and expose a
        # centralized empty-state token for table/tree/canvas placeholders.
        "empty_state_text": "#CBD5E1",
    },
}

STEP34_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-34: final UI design consistency polish only. Palette family and
        # Step-32F dark baseline stay intact; these tokens centralize visual
        # state balance so pages do not hand-style buttons, rows, cards or shell
        # chrome independently.
        "button_secondary_hover_background": "#1A212E",
        "button_secondary_pressed_background": "#111722",
        "button_disabled_background": "transparent",
        "table_action_text": "#38BDF8",
        "table_row_border": "#1E2633",
        "card_header_text": "#F1F5F9",
        "card_description_text": "#CBD5E1",
        "shell_caption_text": "#CBD5E1",
        "modal_action_surface": "#1A212E",
        "tooltip_background": "#111722",
        "tooltip_border": "#1E2633",
        "file_tree_folder_text": "#F1F5F9",
        "file_tree_file_text": "#CBD5E1",
        "workflow_node_text": "#F8FAFC",
    },
    "typography_runtime": {
        "page_title_weight": 600,
        "section_title_weight": 600,
        "card_title_weight": 600,
        "body_weight": 400,
        "small_label_weight": 500,
        "table_header_weight": 600,
        "table_data_weight": 400,
        "action_text_weight": 500,
        "page_title_line_height": 18,
        "section_title_line_height": 16,
        "card_title_line_height": 16,
        "body_line_height": 15,
        "caption_line_height": 14,
    },
}


STEP35_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-35: final UI state consistency + design contract. No palette
        # redesign, geometry growth, page removal or feature change. These
        # tokens are consumed by styles/widgets/pages so interactive states are
        # not hand-styled per page.
        "focus_ring_color": "#38BDF8",
        "focus_ring_background": "transparent",
        "button_primary_hover_background": "#3B82F6",
        "button_primary_pressed_background": "#1D4ED8",
        "button_primary_disabled_background": "#111722",
        "button_secondary_hover_background": "#202938",
        "button_secondary_pressed_background": "#151B26",
        "button_ghost_hover_background": "rgba(255,255,255,13)",
        "button_ghost_pressed_background": "#1A212E",
        "button_disabled_background": "transparent",
        "button_disabled_border": "#1E2633",
        "button_disabled_text": "#64748B",
        "button_loading_background": "#1A212E",
        "input_hover_border": "#334155",
        "input_disabled_background": "#111722",
        "input_disabled_border": "#1E2633",
        "input_disabled_text": "#64748B",
        "selection_control_border": "#30363D",
        "selection_control_hover_border": "#CBD5E1",
        "selection_control_checked_background": "#2563EB",
        "selection_control_checked_hover_background": "#3B82F6",
        "selection_control_disabled_background": "#111722",
        "selection_control_disabled_border": "#1E2633",
        "selection_control_disabled_text": "#64748B",
        "toggle_checked_background": "#2563EB",
        "toggle_checked_hover_background": "#3B82F6",
        "toggle_unchecked_hover_background": "#202938",
        "toggle_disabled_track": "#111722",
        "toggle_disabled_knob": "#64748B",
        "table_row_selected_hover_bg": "rgba(37,99,235,48)",
        "table_header_hover_bg": "#111620",
        "pagination_active_bg": "rgba(37,99,235,31)",
        "badge_muted_text": "#CBD5E1",
        "badge_muted_background": "#1E293B",
        "badge_muted_border": "#334155",
        "plugin_card_hover_background": "#111722",
        "plugin_card_hover_border": "rgba(56,189,248,102)",
        "plugin_action_secondary_background": "#1A212E",
        "plugin_action_secondary_border": "#283345",
        "workflow_control_hover_background": "#202938",
        "workflow_control_pressed_background": "#151B26",
        "modal_close_hover_background": "#202938",
        "menu_item_hover_background": "rgba(255,255,255,13)",
        "tooltip_text": "#F8FAFC",
    },
    "typography_runtime": {
        "state_text_weight": 500,
        "disabled_text_weight": 400,
    },
}

def _deep_merge(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_tokens() -> dict:
    if TOKENS_FILE.exists():
        try:
            with TOKENS_FILE.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return DEFAULT_TOKENS
    return DEFAULT_TOKENS

# App-side source of truth carried forward from Step-36. Step-37 is app-only:
# frozen documents are not rewritten by this patch until user approval.
TOKENS = _deep_merge(
    _deep_merge(
        _deep_merge(
            _deep_merge(
                _deep_merge(
                    _deep_merge(
                        _deep_merge(
                            _deep_merge(
                                _deep_merge(load_tokens(), STEP31_RUNTIME_OVERRIDES),
                                STEP32_RUNTIME_OVERRIDES,
                            ),
                            STEP32A_RUNTIME_OVERRIDES,
                        ),
                        STEP32B_RUNTIME_OVERRIDES,
                    ),
                    STEP32C_RUNTIME_OVERRIDES,
                ),
                STEP32D_RUNTIME_OVERRIDES,
            ),
            STEP32E_RUNTIME_OVERRIDES,
        ),
        STEP32F_RUNTIME_OVERRIDES,
    ),
    STEP33_RUNTIME_OVERRIDES,
)
TOKENS = _deep_merge(TOKENS, STEP34_RUNTIME_OVERRIDES)


STEP36_RUNTIME_OVERRIDES = {
    "interaction_runtime": {
        "accessibility_contract": "step-36-accessibility-contract",
        "state_contract": "step-36-state-contract",
        "keyboard_focus_rule": "keyboard-only 2px flat focus ring; no glow or size increase",
        "tooltip_focus_rule": "existing hover tooltips are also exposed on keyboard focus",
        "modal_focus_rule": "focus moves into modal and returns to previous control on close",
    }
}


STEP37_RUNTIME_OVERRIDES = {
    "colors": {
        # Step-37: Desktop Interaction broken drop-zone/card repair only.
        # These tokens centralize the drop-zone visual contract instead of
        # hand-styling the page. Existing color palette and component sizes stay
        # unchanged; the affected drop-zone is tightened, not enlarged.
        "dropzone_background": "#111722",
        "dropzone_border": "#1E2633",
        "dropzone_hover_background": "#1A212E",
        "dropzone_hover_border": "#38BDF8",
        "dropzone_title_text": "#F1F5F9",
        "dropzone_helper_text": "#CBD5E1",
    },
    "interaction_runtime": {
        "layout_repair_contract": "step-37-desktop-interaction-layout-repair",
        "dropzone_contract": "step-37-dropzone-contract",
        "accessibility_contract": "step-36-accessibility-contract-preserved",
        "state_contract": "step-37-state-contract",
    },
}


STEP38_RUNTIME_OVERRIDES = {
    "responsive_runtime": {
        "certification_contract": "step-38-high-dpi-responsive-certification",
        "window_profiles": ["1120x720", "1366x768", "1440x900", "1600x900", "1920x1080"],
        "dpi_profiles": ["100%", "125%", "150%"],
        "text_overflow_rule": "no wrap in fixed-height zones; use Qt.ElideRight + tooltip",
        "bounds_rule": "modal, popup, workflow overlays and menus must remain inside available viewport",
        "size_rule": "no approved component height/width is increased by Step-38",
    },
    "interaction_runtime": {
        "responsive_contract": "step-38-high-dpi-responsive-certification",
        "state_contract": "step-38-responsive-safe-state-contract",
    },
}


STEP39_RUNTIME_OVERRIDES = {
    "density_runtime": {
        "contract": "step-39-final-compact-density-whitespace-optimization",
        "rule": "tighten whitespace/gaps/min-heights only; no control-height growth and no color redesign",
        "preserved_heights": {
            "button": 28,
            "input": 32,
            "table_header": 30,
            "table_row": 32,
            "sidebar_row": 28,
            "file_tree_row": 28,
            "workflow_node": "160x56",
        },
    },
    "interaction_runtime": {
        "responsive_contract": "step-38-high-dpi-responsive-certification-preserved",
        "density_contract": "step-39-final-compact-density-whitespace-optimization",
        "state_contract": "step-39-density-safe-state-contract",
    },
}


STEP39A_RUNTIME_OVERRIDES = {
    "density_runtime": {
        "contract": "step-39b-responsive-breakage-repair",
        "rule": "complete the visible compact density pass by strengthening spacing reductions, removing expansion-driven blank areas and cleaning stale visible UI copy; no approved control-height growth.",
        "preserved_heights": {
            "button": 28,
            "input": 32,
            "table_header": 30,
            "table_row": 32,
            "sidebar_row": 28,
            "file_tree_row": 28,
            "workflow_node": "160x56",
        },
    },
    "interaction_runtime": {
        "responsive_contract": "step-38-high-dpi-responsive-certification-preserved",
        "density_contract": "step-39b-responsive-breakage-repair",
        "state_contract": "step-39b-responsive-breakage-repair-state-contract",
    },
}



STEP40B_RUNTIME_OVERRIDES = {
    "typography_runtime": {
        # Step-40B: restore the readable text breathing from the pre-overcompact
        # baseline. Font sizes and component heights remain unchanged; only text
        # line-height/vertical rhythm is relaxed so labels, descriptions and
        # card copy do not visually collide.
        "page_title_line_height": 19,
        "section_title_line_height": 17,
        "card_title_line_height": 17,
        "body_line_height": 16,
        "caption_line_height": 15,
    },
    "density_runtime": {
        "contract": "step-40b-text-spacing-breathing-repair",
        "rule": "repair over-compressed text/card/page gaps while preserving all approved control heights, colors, pages and Step-40 invoice functionality",
        "preserved_heights": {
            "button": 28,
            "input": 32,
            "table_header": 30,
            "table_row": 32,
            "sidebar_row": 28,
            "file_tree_row": 28,
            "workflow_node": "160x56",
        },
    },
    "interaction_runtime": {
        "responsive_contract": "step-38-high-dpi-responsive-certification-preserved",
        "density_contract": "step-40b-text-spacing-breathing-repair",
        "state_contract": "step-39b-responsive-breakage-repair-state-contract",
        "invoice_contract": "step-40-invoice-details-page-preserved",
    },
}


STEP40C_RUNTIME_OVERRIDES = {
    "typography_runtime": {
        "page_title_line_height": 19,
        "section_title_line_height": 17,
        "card_title_line_height": 17,
        "body_line_height": 16,
        "caption_line_height": 15,
    },
    "density_runtime": {
        "contract": "step-40c-live-logs-full-page-text-stack-repair",
        "rule": "repair Live Logs full-page expansion and prevent word-wrapped labels/descriptions from vertically stretching inside cards while preserving approved component heights and Step-40 invoice functionality",
        "preserved_heights": {
            "button": 28,
            "input": 32,
            "table_header": 30,
            "table_row": 32,
            "sidebar_row": 28,
            "file_tree_row": 28,
            "workflow_node": "160x56",
        },
    },
    "interaction_runtime": {
        "responsive_contract": "step-38-high-dpi-responsive-certification-preserved",
        "density_contract": "step-40c-live-logs-full-page-text-stack-repair",
        "state_contract": "step-39b-responsive-breakage-repair-state-contract",
        "invoice_contract": "step-40-invoice-details-page-preserved",
    },
}

TOKENS = _deep_merge(TOKENS, STEP35_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP36_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP37_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP38_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP39_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP39A_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP40B_RUNTIME_OVERRIDES)
TOKENS = _deep_merge(TOKENS, STEP40C_RUNTIME_OVERRIDES)
COLORS = TOKENS.get("colors", DEFAULT_TOKENS["colors"])
TYPE = TOKENS.get("font_size_compact_px", DEFAULT_TOKENS["font_size_compact_px"])
TYPO_RUNTIME = TOKENS.get("typography_runtime", STEP32E_RUNTIME_OVERRIDES["typography_runtime"])
TYPOGRAPHY = TOKENS.get("typography", DEFAULT_TOKENS["typography"])
SPACING = TOKENS.get("spacing", DEFAULT_TOKENS["spacing"])
RADIUS = TOKENS.get("radius", DEFAULT_TOKENS["radius"])
BORDER = TOKENS.get("border", DEFAULT_TOKENS["border"])
ICONOGRAPHY = TOKENS.get("iconography", DEFAULT_TOKENS["iconography"])
BRAND = TOKENS.get("brand_identity", DEFAULT_TOKENS["brand_identity"])

@dataclass(frozen=True)
class ImplementationConstants:
    # Step-31 app-only global component contract: every page imports these values instead of hard-coding per-page variants.
    sidebar_width: int = 220
    sidebar_padding: int = 8
    sidebar_item_height: int = 28
    header_height: int = 44
    status_bar_height: int = 24
    button_height: int = 28
    button_padding_x: int = 9
    button_focus_padding_x: int = 8
    button_font_size: int = 12
    sidebar_font_size: int = 12
    link_button_height: int = 20
    icon_button_size: int = 28
    input_height: int = 32
    input_padding_x: int = 10
    input_focus_padding_x: int = 9
    text_area_padding_x: int = 10
    text_area_padding_y: int = 7
    data_table_row_height: int = 32
    table_row_height: int = 32
    file_row_height: int = 28
    page_padding_top: int = 14
    page_padding_right: int = 14
    page_padding_bottom: int = 14
    page_padding_left: int = 14
    page_padding: int = 14
    page_content_max_width: int = 0
    section_gap: int = 10
    content_gap: int = 12
    action_gap: int = 5
    card_padding: int = 14
    card_internal_gap: int = 7
    card_title_font_size: int = 13
    sidebar_title_font_size: int = 13
    page_header_min_height: int = 52
    page_header_max_height: int = 0
    page_header_padding_y: int = 5
    page_header_text_gap: int = 3
    page_header_action_top_padding: int = 2
    page_header_description_min_height: int = 16
    card_header_gap: int = 3
    card_header_content_gap: int = 7
    form_group_gap: int = 5
    # Step-40J global login/form section contract. These values are the single
    # source for Authentication login construction so pages do not hand-code
    # card/input/button geometry. Width is kept at the existing 400px to obey
    # the no-core-component-size-increase rule while bounding the form; the
    # password/options and options/submit gaps are locked to an 8px breathing
    # rhythm requested by the Step-40J forensic audit.
    form_login_card_width: int = 400
    form_login_card_padding: int = 14
    form_login_field_gap: int = 4
    form_login_password_options_gap: int = 8
    form_login_action_top_gap: int = 8
    form_login_options_row_height: int = 20
    form_login_options_row_gap: int = 0
    form_login_tooltips_enabled: bool = False
    form_validation_reserved_height: int = 0
    card_action_gap: int = 6
    table_cell_padding_x: int = 7
    table_cell_gap: int = 8
    data_toolbar_height: int = 36
    flat_row_padding_y: int = 5
    shell_header_gap: int = 4
    dock_padding: int = 8
    dock_gap: int = 6
    chip_gap: int = 5
    modal_action_gap: int = 5
    # Step-39B responsive breakage repair. Core control heights stay approved;
    # spacing, padding, expansion-driven blank areas and drop-zone whitespace are tightened more visibly
    # without feature/page removal, color redesign or architecture refactor.
    dropzone_height: int = 48
    dropzone_padding_x: int = 8
    dropzone_padding_y: int = 5
    dropzone_text_gap: int = 3
    large_panel_min_height: int = 460
    medium_panel_min_height: int = 380
    scan_panel_min_height: int = 500
    log_viewer_min_height: int = 340
    compact_log_min_height: int = 140
    chat_transcript_min_height: int = 260
    ai_side_panel_min_width: int = 220
    ai_side_panel_max_width: int = 280
    screenshot_preview_min_height: int = 280
    validation_text_min_height: int = 160
    responsive_safe_margin: int = 12
    responsive_dialog_margin: int = 20
    responsive_tooltip_margin: int = 8
    common_radius: int = 8
    focus_ring: int = 2
    min_window_width: int = 1120
    min_window_height: int = 720
    default_window_width: int = 1366
    default_window_height: int = 768
    compact_breakpoint: int = 1180
    medium_breakpoint: int = 1440
    large_breakpoint: int = 1680
    responsive_card_min_width: int = 270
    plugin_card_min_width: int = 240
    plugin_grid_max_columns: int = 3
    table_search_min_width: int = 180
    table_search_max_width: int = 260
    scrollbar_thickness: int = 6
    sidebar_scrollbar_gutter: int = 10
    sidebar_scrollbar_inner_gap: int = 4
    table_header_height: int = 30
    badge_radius: int = 4
    badge_padding_x: int = 6
    badge_padding_y: int = 2
    search_padding_left: int = 30
    search_padding_right: int = 9
    password_padding_left: int = 10
    password_padding_right: int = 34
    toggle_width: int = 36
    toggle_height: int = 20
    toggle_knob: int = 14
    workflow_topbar_height: int = 34
    workflow_node_width: int = 160
    workflow_node_height: int = 56
    workflow_node_padding_x: int = 8
    workflow_node_padding_y: int = 7
    workflow_node_popup_width: int = 220
    workflow_node_popup_min_height: int = 216
    workflow_palette_item_height: int = 28

    # Step-31 global component anatomy tokens.  These values are consumed by
    # widgets/styles/pages so each control uses one central design contract.
    selection_indicator_size: int = 14
    file_tree_indent: int = 16
    file_tree_icon_size: int = 14
    badge_font_size: int = 10
    workflow_badge_font_size: int = 10
    workflow_node_title_font_size: int = 12
    workflow_node_icon_size: int = 12
    workflow_node_internal_gap: int = 4

CONST = ImplementationConstants()

SECTION_NAMES = [
    "Overview",
    "Foundation",
    "Application Shell",
    "Page Structure",
    "Navigation",
    "Content & Containers",
    "Forms & Inputs",
    "Actions",
    "Data Display",
    "Live Logs",
    "Scan Page",
    "Workflow Canvas",
    "Plugin",
    "AI Chatbot",
    "Overlay & Popup",
    "Feedback & States",
    "File & Media",
    "File Tree View",
    "Desktop Interaction",
    "Application Pages",
    "Invoice Details",
    "Settings",
    "Authentication & Onboarding",
    "Reference Screenshots",
    "Validation Report",
]

OFFICIAL_STRUCTURE = {
    "01. FOUNDATION": ["Colors", "Typography", "Spacing", "Border", "Radius", "Shadow", "Iconography", "Light Theme", "Dark Theme", "System Theme", "Contrast", "Focus", "Keyboard Navigation"],
    "02. APPLICATION SHELL": ["Window Header", "Window Controls", "Sidebar", "Topbar", "Navbar", "Menubar", "Toolbar", "Breadcrumb", "Status Bar", "Connection Status", "System Status"],
    "03. PAGE STRUCTURE": ["Page Header", "Page Title", "Page Subtitle", "Page Actions", "Page Footer", "Hero", "Section Header", "Section Title", "Section Actions"],
    "04. NAVIGATION COMPONENTS": ["Navigation Item", "Sub Navigation", "Menu", "Menu Item", "Tabs", "Tab Panel", "Breadcrumb", "Pagination", "Stepper"],
    "05. CONTENT & CONTAINERS": ["Card", "Panel", "Box", "Widget", "Text", "Heading", "Description", "Divider", "Avatar", "Badge", "Tag", "Chip"],
    "06. FORM & INPUT": ["Form", "Form Group", "Label", "Help Text", "Validation Message", "Input", "Textarea", "Search", "Password", "Number Input", "Select", "Dropdown", "Combobox", "Checkbox", "Radio", "Toggle", "Slider", "Date Picker", "Time Picker", "File Upload", "Color Picker"],
    "07. ACTIONS": ["Primary Button", "Secondary Button", "Ghost Button", "Danger Button", "Icon Button", "Button Group", "Split Button", "Menu Button", "Link", "Shortcut", "Context Action"],
    "08. DATA DISPLAY": ["Data Table", "Table Header", "Table Row", "Table Cell", "Column", "List", "List Item", "Tree View", "Timeline", "Search", "Filter", "Sort", "Pagination", "Bulk Selection", "Bulk Actions"],
    "09. OVERLAY & POPUP": ["Modal", "Confirmation Dialog", "Alert Dialog", "Popover", "Tooltip", "Dropdown Menu", "Drawer", "Side Panel", "Command Palette"],
    "10. FEEDBACK & SYSTEM STATE": ["Alert", "Toast", "Snackbar", "Spinner", "Progress Bar", "Skeleton", "Empty State", "Success State", "Error State", "Warning State", "Offline State"],
    "11. FILE & MEDIA": ["File Browser", "Folder", "File", "File Picker", "Recent Files", "Upload", "Download", "Import", "Export", "Image Viewer", "Video Player", "Audio Player"],
    "12. DESKTOP INTERACTION": ["Resize", "Drag", "Split Pane", "Dock Panel", "Hover", "Focus", "Active", "Selected", "Disabled", "Drag & Drop", "Multi Select", "Right Click", "Keyboard Shortcut"],
    "13. APPLICATION PAGES": ["Home", "Dashboard", "Workspace", "Search", "Profile", "Account", "Preferences", "Settings", "Help", "About", "Updates"],
    "14. AUTHENTICATION & ONBOARDING": ["Login", "Register", "Forgot Password", "Reset Password", "Verification", "2FA", "Session", "Permission", "Welcome", "Setup", "Tutorial", "Completion"],
}
