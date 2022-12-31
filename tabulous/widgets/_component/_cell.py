from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Mapping,
    SupportsIndex,
    Tuple,
    TypeVar,
    overload,
    Any,
    Callable,
    Iterator,
)
import warnings

from magicgui.widgets import Widget
from tabulous.exceptions import TableImmutableError
from tabulous.types import EvalInfo
from tabulous._psygnal import InCellRangedSlot
from ._base import TableComponent

if TYPE_CHECKING:
    import pandas as pd

_F = TypeVar("_F", bound=Callable)


class CellInterface(TableComponent):
    """
    Interface with table cells.

    This object can be used to emulate editing cells in the table.

    >>> table.cell[i, j]  # get the (i, j) cell value shown in the table
    >>> table.cell[i, j] = value  # set the (i, j) cell value
    >>> table.cell[i, j] = "&=np.mean(df.iloc[:, 0]"  # in-cell evaluation
    >>> del table.cell[i, j]  # delete the (i, j) cell value

    Label texts in the cell can be accessed by the ``label`` attribute.

    >>> table.cell.label[i, j]  # get the (i, j) cell label text
    >>> table.cell.label[i, j] = value  # set the (i, j) cell label text
    >>> del table.cell.label[i, j]  # delete the (i, j) cell label text

    Use ``register_action`` to register a contextmenu function.

    >>> @table.cell.register_action("My Action")
    >>> def my_action(index):
    ...     # do something
    """

    def __getitem__(self, key: tuple[int | slice, int | slice]):
        return self.parent._qwidget.model().df.iloc[key]

    def __setitem__(self, key: tuple[int | slice, int | slice], value: Any) -> None:
        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")

        if isinstance(value, Widget):
            # add item widget
            r, c = key
            if isinstance(r, int) and isinstance(c, int):
                sheet = self._assert_spreadsheet()
                return sheet._qwidget._set_widget_at_index(*key, value)
            raise TypeError("Cannot set widget at slices.")

        import pandas as pd
        from tabulous._qt._table._base._line_edit import QCellLiteralEdit

        row, col = self._normalize_key(key)

        if isinstance(value, str) and QCellLiteralEdit._is_eval_like(value):
            if row.stop - row.start == 1 and col.stop - col.start == 1:
                expr, is_ref = QCellLiteralEdit._parse_ref(value)
                info = EvalInfo(
                    row=row.start,
                    column=col.start,
                    expr=expr,
                    is_ref=is_ref,
                )
                table.events.evaluated.emit(info)
                return None
            else:
                raise ValueError("Cannot evaluate a multi-cell selection.")

        if isinstance(value, str) or not hasattr(value, "__iter__"):
            _value = [[value]]
        else:
            _value = value
        try:
            df = pd.DataFrame(_value)
        except ValueError:
            raise ValueError(f"Could not convert value {_value!r} to DataFrame.")

        if 1 in df.shape and (col.stop - col.start, row.stop - row.start) == df.shape:
            # it is natural to set an 1-D array without thinking of the direction.
            df = df.T

        table._qwidget.setDataFrameValue(row, col, df)
        return None

    def __delitem__(self, key: tuple[int | slice, int | slice]) -> None:
        """Deleting cell, equivalent to pushing Delete key."""

        table = self.parent
        if not table.editable:
            raise TableImmutableError("Table is not editable.")
        row, col = key
        table._qwidget.setSelections([(row, col)])
        table._qwidget.deleteValues()
        return None

    def _normalize_key(
        self,
        key: tuple[int | slice, int | slice],
    ) -> tuple[slice, slice]:
        if len(key) == 1:
            key = (key, slice(None))
        row, col = key

        if isinstance(row, slice):
            row = _normalize_slice(row, self.parent._qwidget.model().df.shape[0])
        else:
            row = slice(row, row + 1)

        if isinstance(col, slice):
            col = _normalize_slice(col, self.parent._qwidget.model().df.shape[1])
        else:
            col = slice(col, col + 1)
        return row, col

    # fmt: off
    @overload
    def register_action(self, val: str) -> Callable[[_F], _F]: ...
    @overload
    def register_action(self, val: _F) -> _F: ...
    # fmt: on

    def register_action(self, val: str | Callable[[tuple[int, int]], Any]):
        """Register an contextmenu action to the tablelist."""
        table = self.parent.native
        if isinstance(val, str):
            return table.registerAction(val)
        elif callable(val):
            location = val.__name__.replace("_", " ")
            return table.registerAction(location)(val)
        else:
            raise TypeError("input must be a string or callable.")

    @property
    def label(self) -> CellLabelInterface:
        """Interface to the cell labels."""
        return CellLabelInterface(self.parent)

    @property
    def ref(self) -> CellReferenceInterface:
        """Interface to the cell references."""
        return CellReferenceInterface(self.parent)

    def get_label(self, r: int, c: int) -> str | None:
        """Get the label of a cell."""
        warnings.warn(
            "get_label is deprecated. Use `table.cell.label[r, c]` instead.",
            DeprecationWarning,
        )
        return self.label[r, c]

    def set_label(self, r: int, c: int, text: str):
        """Set the label of a cell."""
        warnings.warn(
            f"set_label is deprecated. Use `table.cell.label[r, c] = {text!r}` "
            "instead.",
            DeprecationWarning,
        )
        self.label[r, c] = text

    def set_labeled_data(
        self,
        r: int,
        c: int,
        data: dict[str, Any] | pd.Series | tuple,
        sep: str = "",
    ):
        """
        Set given data with cell labels.

        Parameters
        ----------
        r : int
            Starting row index.
        c : int
            Starting column index.
        data : dict[str, Any], pd.Series or (named) tuple
            Data to be set.
        sep : str, optional
            Separator added at the end of labels.
        """
        import pandas as pd

        ndata = len(data)
        if isinstance(data, dict):
            _data = pd.Series(data)
        elif isinstance(data, tuple):
            index = getattr(data, "_fields", range(ndata))
            _data = pd.Series(data, index=index)
        elif isinstance(data, pd.Series):
            _data = data.copy()
        else:
            raise TypeError(f"Cannot convert {data!r} to Series.")

        if sep:
            _data.index = [f"{idx}{sep}" for idx in _data.index]

        self.parent._qwidget.setLabeledData(slice(r, r + ndata), slice(c, c + 1), _data)
        return None


class CellLabelInterface(TableComponent):
    def __getitem__(self, key: tuple[int, int]) -> str | None:
        """Get the label of a cell."""
        self._assert_integers(key)
        return self.parent.native.itemLabel(*key)

    def __setitem__(self, key: tuple[int, int], value: str):
        """Set the label of a cell."""
        self._assert_integers(key)
        return self.parent.native.setItemLabel(*key, value)

    def __delitem__(self, key: tuple[int, int]):
        """Delete the label of a cell."""
        self._assert_integers(key)
        return self.parent.native.setItemLabel(*key, None)

    def _assert_integers(self, key: tuple[int, int]):
        r, c = key
        if not (isinstance(r, SupportsIndex) and isinstance(c, SupportsIndex)):
            raise TypeError("Cell label must be accessed by integer indices.")


class CellReferenceInterface(
    TableComponent, Mapping[Tuple[int, int], InCellRangedSlot]
):
    """Interface to the cell references of a table."""

    def _table_map(self):
        return self.parent._qwidget._qtable_view._table_map

    def __getitem__(self, key: tuple[int, int]):
        return self._table_map()[key]

    def __iter__(self) -> Iterator[InCellRangedSlot]:
        return iter(self._table_map())

    def __len__(self) -> int:
        return len(self._table_map())

    def __repr__(self) -> str:
        slots = self._table_map()
        cname = type(self).__name__
        if len(slots) == 0:
            return f"{cname}()"
        s = ",\n\t".join(f"{k}: {slot!r}" for k, slot in slots.items())
        return f"{cname}(\n\t{s}\n)"


def _normalize_slice(sl: slice, size: int) -> slice:
    start = sl.start
    stop = sl.stop

    if sl.step not in (None, 1):
        raise ValueError("Row slice step must be 1.")

    if start is None:
        start = 0
    elif start < 0:
        start = size + start
    if stop is None:
        stop = size
    elif stop < 0:
        stop = size + stop
    return slice(start, stop)
