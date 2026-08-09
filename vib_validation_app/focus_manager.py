"""Keyboard-only flat focus-ring and accessibility interaction manager — Step 36.

Qt Style Sheets do not provide a native ``:focus-visible`` selector like CSS.
This module implements that behavior for the validation app by tracking the
latest input modality at QApplication level and setting a dynamic
``keyboardFocus=\"true\"`` property only when focus arrives from keyboard
navigation.

Design intent:
- Tab / Backtab / keyboard shortcut focus => show frozen 2px flat focus ring.
- Mouse click / touchpad click focus => keep normal flat state, no ring.
- No glow, no shadow, no native raised/halo effect.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QEvent, Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QToolTip
from shiboken6 import isValid


_KEYBOARD_FOCUS_REASONS = {
    Qt.FocusReason.TabFocusReason,
    Qt.FocusReason.BacktabFocusReason,
    Qt.FocusReason.ShortcutFocusReason,
    Qt.FocusReason.MenuBarFocusReason,
}

_MOUSE_FOCUS_REASONS = {
    Qt.FocusReason.MouseFocusReason,
    Qt.FocusReason.PopupFocusReason,
}

_KEYBOARD_NAV_KEYS = {
    Qt.Key.Key_Tab,
    Qt.Key.Key_Backtab,
    Qt.Key.Key_Left,
    Qt.Key.Key_Right,
    Qt.Key.Key_Up,
    Qt.Key.Key_Down,
    Qt.Key.Key_Home,
    Qt.Key.Key_End,
    Qt.Key.Key_PageUp,
    Qt.Key.Key_PageDown,
    Qt.Key.Key_Return,
    Qt.Key.Key_Enter,
    Qt.Key.Key_Space,
    Qt.Key.Key_Escape,
}


class KeyboardFocusRingManager(QObject):
    """QApplication event filter that emulates CSS ``:focus-visible``.

    Step-36 also exposes existing hover tooltips during keyboard focus so
    truncated table/file/canvas labels have an accessible non-mouse path.
    """

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._last_input: str = "mouse"
        self._focused_widget: Optional[QWidget] = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API name
        event_type = event.type()

        if event_type == QEvent.Type.KeyPress:
            key = getattr(event, "key", lambda: None)()
            if key in _KEYBOARD_NAV_KEYS or self._is_plain_shortcut(event):
                self._last_input = "keyboard"
        elif event_type in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.TouchBegin,
        }:
            self._last_input = "mouse"
        elif event_type == QEvent.Type.FocusIn and isinstance(watched, QWidget):
            reason = getattr(event, "reason", lambda: Qt.FocusReason.OtherFocusReason)()
            keyboard_focus = reason in _KEYBOARD_FOCUS_REASONS or (
                self._last_input == "keyboard" and reason not in _MOUSE_FOCUS_REASONS
            )
            self._set_keyboard_focus(watched, keyboard_focus)
            if keyboard_focus and watched.toolTip():
                QTimer.singleShot(180, lambda w=watched: self._show_focus_tooltip(w))
        elif event_type == QEvent.Type.FocusOut and isinstance(watched, QWidget):
            if watched is self._focused_widget:
                self._set_keyboard_focus(watched, False)
            QToolTip.hideText()
        elif event_type in {QEvent.Type.Destroy, QEvent.Type.DeferredDelete}:
            if watched is self._focused_widget:
                # Never keep an actionable Python wrapper once Qt starts deleting
                # the underlying focused object.
                self._focused_widget = None
                QToolTip.hideText()

        return super().eventFilter(watched, event)

    @staticmethod
    def _is_plain_shortcut(event: QEvent) -> bool:
        modifiers = getattr(event, "modifiers", lambda: Qt.KeyboardModifier.NoModifier)()
        return bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier))

    @staticmethod
    def _is_live_widget(widget: Optional[QWidget]) -> bool:
        """Return whether a Python Qt wrapper still owns a live C++ QWidget."""
        return widget is not None and isValid(widget)

    def _set_keyboard_focus(self, widget: QWidget, enabled: bool) -> None:
        previous = self._focused_widget
        if previous is not None and previous is not widget:
            if self._is_live_widget(previous):
                self._apply_property(previous, False)
            self._focused_widget = None

        if not self._is_live_widget(widget):
            if self._focused_widget is widget:
                self._focused_widget = None
            return

        if enabled:
            if self._apply_property(widget, True):
                self._focused_widget = widget
            else:
                self._focused_widget = None
        else:
            self._apply_property(widget, False)
            if self._focused_widget is widget:
                self._focused_widget = None

    def _show_focus_tooltip(self, widget: QWidget) -> None:
        if not self._is_live_widget(widget):
            return
        try:
            if QApplication.focusWidget() is widget and widget.toolTip():
                QToolTip.showText(
                    widget.mapToGlobal(widget.rect().bottomLeft()),
                    widget.toolTip(),
                    widget,
                )
        except RuntimeError:
            # A queued tooltip callback can run after deleteLater() destroys the
            # C++ QWidget while the Python wrapper still exists. Only suppress
            # that exact lifetime race; unrelated RuntimeError failures propagate.
            if not self._is_live_widget(widget):
                return
            raise

    @classmethod
    def _apply_property(cls, widget: QWidget, enabled: bool) -> bool:
        if not cls._is_live_widget(widget):
            return False
        try:
            widget.setProperty("keyboardFocus", "true" if enabled else "false")
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()
            return True
        except RuntimeError:
            # The C++ object may be destroyed between the validity probe and the
            # property/style calls during a page transition. Do not hide unrelated
            # Qt errors on a still-live widget.
            if not cls._is_live_widget(widget):
                return False
            raise


def install_keyboard_focus_ring(app: QApplication) -> KeyboardFocusRingManager:
    """Install and retain the keyboard-only focus-ring manager on QApplication."""
    existing = getattr(app, "_vib_keyboard_focus_ring_manager", None)
    if isinstance(existing, KeyboardFocusRingManager):
        return existing
    manager = KeyboardFocusRingManager(app)
    app.installEventFilter(manager)
    setattr(app, "_vib_keyboard_focus_ring_manager", manager)
    return manager
