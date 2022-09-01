from __future__ import annotations
from typing import TYPE_CHECKING
from contextlib import contextmanager

if TYPE_CHECKING:
    from ._enhanced_table import _QTableViewEnhanced
    from qtpy import QtCore


class HighlightModel:
    """Custom highlight model for efficient overlay handling on a large table."""

    def __init__(self):
        self._highlights: list[tuple[slice, slice]] = []
        self._blocked = False

    def __len__(self) -> int:
        return len(self._highlights)

    def add_dummy(self) -> None:
        self._highlights.append((slice(0, 0), slice(0, 0)))
        return None

    def append(self, highlight: tuple[slice, slice]) -> None:
        self._highlights.append(highlight)
        return None

    def update_last(self, highlight: tuple[slice, slice]) -> None:
        self._highlights[-1] = highlight
        return None

    def set_highlights(self, highlights: list[tuple[slice, slice]]) -> None:
        if self._blocked:
            return None
        self._highlights.clear()
        return self._highlights.extend(highlights)

    def clear(self) -> None:
        """Clear all the selections"""
        return self._highlights.clear()

    @contextmanager
    def blocked(self) -> None:
        """Block selection updates in this context."""
        self._blocked = True
        try:
            yield
        finally:
            self._blocked = False

    def highlightRectangles(self, qtable: _QTableViewEnhanced) -> list[QtCore.QRect]:
        model = qtable.model()
        _rects = []
        for rr, cc in self._highlights:
            top_left = model.index(rr.start, cc.start)
            bottom_right = model.index(rr.stop - 1, cc.stop - 1)
            rect = qtable.visualRect(top_left) | qtable.visualRect(bottom_right)
            _rects.append(rect)
        return _rects


class SelectionModel(HighlightModel):
    """A specialized highlight model with item-selection-like behavior."""

    def __init__(self):
        super().__init__()
        self._ctrl_on = False
        self._shift_on = False
        self._selection_start = None

    def set_ctrl(self, on: bool) -> None:
        """Equivalent to pressing Ctrl."""
        self._ctrl_on = on
        return None

    def set_shift(self, on: bool) -> None:
        """Equivalent to pressing Shift."""
        self._shift_on = on
        return None

    def shift_start(self, r: int, c: int) -> None:
        if self._selection_start is None and not self._blocked:
            self._selection_start = r, c
        self._shift_on = True

    def shift_end(self) -> None:
        self._selection_start = None
        self._shift_on = False

    def drag_start(self, r: int, c: int) -> None:
        """Start dragging selection at (r, c)."""
        if self._blocked:
            return None

        if not self._shift_on:
            self._selection_start = (r, c)

        if not self._ctrl_on:
            self.clear()
        else:
            self._highlights.append((slice(r, r + 1), slice(c, c + 1)))
        self.drag_to(r, c)
        return None

    def drag_end(self) -> None:
        """Finish dragging selection."""

    def set_highlights(self, selections: list[tuple[slice, slice]]) -> None:
        if self._blocked:
            return None
        self._highlights.clear()
        return self._highlights.extend(selections)

    def drag_to(self, r: int, c: int):
        """Drag to (r, c) to select cells."""
        if self._blocked:
            return None
        if self._selection_start is None:
            if not self._ctrl_on:
                self._highlights.clear()
            _r0 = _r1 = r
            _c0 = _c1 = c
        else:
            r0, c0 = self._selection_start
            _r0, _r1 = sorted([r0, r])
            _c0, _c1 = sorted([c0, c])

        if len(self._highlights) > 0:
            self._highlights[-1] = (slice(_r0, _r1 + 1), slice(_c0, _c1 + 1))
        else:
            self._highlights.append((slice(_r0, _r1 + 1), slice(_c0, _c1 + 1)))
        return None
