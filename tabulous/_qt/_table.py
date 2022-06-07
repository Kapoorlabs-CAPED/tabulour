from __future__ import annotations
from typing import Any, Callable, NamedTuple, TYPE_CHECKING
import weakref
import numpy as np
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Signal, Qt

from ._utils import show_messagebox
from ..types import FilterType

if TYPE_CHECKING:
    import pandas as pd


class ItemInfo(NamedTuple):
    row: int
    column: int
    value: Any
    updated: bool

_EDITABLE = QtW.QAbstractItemView.EditTrigger.EditKeyPressed | QtW.QAbstractItemView.EditTrigger.DoubleClicked
_READ_ONLY = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
_SCROLL_PRE_PIXEL = QtW.QAbstractItemView.ScrollMode.ScrollPerPixel

class QTableLayer(QtW.QTableWidget):
    itemChangedSignal = Signal(ItemInfo)
    selectionChangedSignal = Signal(list)
    
    def __init__(self, parent: QtW.QWidget | None = None, data: pd.DataFrame | None = None):
        super().__init__(*data.shape, parent)
        self.updateDataFrame(data)
        self.setVerticalScrollMode(_SCROLL_PRE_PIXEL)
        self.setHorizontalScrollMode(_SCROLL_PRE_PIXEL)
        delegate = TableItemDelegate(parent=self)
        self.setItemDelegate(delegate)
        delegate.edited.connect(lambda x: self.itemChangedSignal.emit(self._update_data(*x)))
        self._editable = False
        self._zoom = 1.0
        self._initial_font_size = self.font().pointSize()
        self._default_h_size = self.horizontalHeader().defaultSectionSize()
        self._default_v_size = self.verticalHeader().defaultSectionSize()
        self._filter_slice: FilterType | None = None
        
    def zoom(self) -> float:
        """Get current zoom factor."""
        return self._zoom
    
    def setZoom(self, value: float) -> None:
        if not 0.25 <= value <= 2.0:
            raise ValueError("Zoom factor must between 0.25 and 2.0.")
        # To keep table at the same position.
        zoom_ratio = 1 / self._zoom * value
        pos = self.verticalScrollBar().sliderPosition()
        self.verticalScrollBar().setSliderPosition(pos * zoom_ratio)
        pos = self.horizontalScrollBar().sliderPosition()
        self.horizontalScrollBar().setSliderPosition(pos * zoom_ratio)
        
        # Zoom font size
        font = self.font()
        font.setPointSize(self._initial_font_size*value)
        self.setFont(font)
        
        # Zoom section size of headers
        self.horizontalHeader().setDefaultSectionSize(self._default_h_size*value)
        self.verticalHeader().setDefaultSectionSize(self._default_v_size*value)
        
        # Update stuff
        self._zoom = value
        self.refreshTable()
    
    def indexUnderCursor(self) -> tuple[int, int]:
        pos = self.mapFromGlobal(QtGui.QCursor().pos())
        item = self.itemAt(pos)
        return item.row(), item.column()
    
    def getDataFrame(self) -> pd.DataFrame:
        data = self._data_ref()
        if data is None:
            raise ValueError("DataFrame is deleted.")
        
        if self._filter_slice is None:
            return data
        elif callable(self._filter_slice):
            sl = self._filter_slice(data)
        else:
            sl = self._filter_slice
        return data[sl]
    
    def updateDataFrame(self, value: pd.DataFrame):
        self._data_ref: weakref.ReferenceType[pd.DataFrame] = weakref.ref(value)
        nr = self.rowCount()
        nc = self.columnCount()
        
        nr_data, nc_data = value.shape
        
        # check shape mismatch between DataFrame and table widget.
        if nr > nr_data:
            [self.removeRow(nr_data) for _ in range(nr - nr_data)]
        elif nr < nr_data:
            [self.insertRow(i) for i in range(nr_data - nr)]
            
        if nc > nc_data:
            [self.removeColumn(nc_data) for _ in range(nc - nc_data)]
        elif nc < nc_data:
            [self.insertColumn(i) for i in range(nc_data - nc)]
        
        return None
    
    def setDataFrameValue(self, r, c, value: Any, absolute: bool = True) -> None:
        data = self._data_ref()
        if self._filter_slice is None:
            data.iloc[r, c] = value
            return
        elif callable(self._filter_slice):
            sl = self._filter_slice(data)
        else:
            sl = self._filter_slice
        
        cum = np.cumsum(sl)  # NOTE: this is not efficient if table is large
        if np.isscalar(r):
            r0 = np.where(cum == r + 1)[0]
            
        elif isinstance(r, slice):
            r_start, r_stop, r_step = r.indices(cum.shape[0])
            if r_step != 1:
                raise ValueError("step must not be >1.")
            start = np.where(cum == r_start + 1)[0][0]
            stop = np.where(cum == r_stop + 1)[0][0]
        
            r0 = np.array(sl, copy=True)
            r0[:start] = False
            r0[stop:] = False
            
        else:
            raise TypeError(type(r))
        
        data.iloc[r0, c] = value
        return None

    if TYPE_CHECKING:
        def itemDelegate(self) -> TableItemDelegate: ...
        
    def precision(self) -> int:
        """Return table value precision."""
        return self.itemDelegate().ndigits
    
    def setPrecision(self, ndigits: int) -> None:
        """Set table value precision."""
        ndigits = int(ndigits)
        if ndigits <= 0:
            raise ValueError("Cannot set negative precision.")
        self.itemDelegate().ndigits = ndigits
        self.refreshTable()
    
    def editability(self) -> bool:
        """Return the editability of the table."""
        return self._editable
    
    def setEditability(self, editable: bool):
        """Set the editability of the table."""
        if editable:
            self.setEditTriggers(_EDITABLE)
        else:
            self.setEditTriggers(_READ_ONLY)
        self._editable = editable
    
    def connectItemChangedSignal(self, slot):
        self.itemChangedSignal.connect(slot)
        return slot
    
    def connectSelectionChangedSignal(self, slot):
        self.selectionChangedSignal.connect(slot)
        return slot
    
    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        self.selectionChangedSignal.emit(self.selections())
        return super().selectionChanged(selected, deselected)
    
    def selections(self) -> list[tuple[slice, slice]]:
        """Get list of selections as slicable tuples"""
        selections = self.selectedRanges()
        out: list[tuple[slice, slice]] = []
        for sel in selections:
            r0 = sel.topRow()
            r1 = sel.bottomRow() + 1
            c0 = sel.leftColumn()
            c1 = sel.rightColumn() + 1
            out.append((slice(r0, r1), slice(c0, c1)))
        
        return out

    def setSelections(self, selections: list[tuple[slice, slice]]):
        """Set list of selections."""
        self.clearSelection()
        data = self.getDataFrame()
        nr, nc = data.shape
        try:
            for sel in selections:
                r, c = sel
                r0, r1, _ = r.indices(nr)
                c0, c1, _ = c.indices(nc)
                self.setRangeSelected(
                    QtW.QTableWidgetSelectionRange(r0, c0, r1 - 1, c1 - 1), 
                    True,
                )
        except Exception as e:
            self.clearSelection()
            raise e
        
    def _update_data(self, row: int, col: int):
        item = self.item(row, col)

        r = item.row()
        c = item.column()
        text = item.text()
        
        data = self.getDataFrame()
        dtype = data.dtypes[c]
        try:
            value = _DTYPE_KIND_TO_CONVERTER[dtype.kind](text)
        except Exception as e:
            self.refreshTable()
            updated = False
        else:
            self.setDataFrameValue(r, c, value)
            updated = True
        return ItemInfo(r, c, value, updated)
        
    
    def verticalScrollbarValueChanged(self, value: int) -> None:
        self.refreshTable()
        return super().verticalScrollbarValueChanged(value)

    def horizontalScrollbarValueChanged(self, value: int) -> None:
        self.refreshTable()
        return super().horizontalScrollbarValueChanged(value)
    
    def rowResized(self, row: int, oldHeight: int, newHeight: int) -> None:
        self.refreshTable()
        return super().rowResized(row, oldHeight, newHeight)
    
    def columnResized(self, column: int, oldWidth: int, newWidth: int) -> None:
        self.refreshTable()
        return super().columnResized(column, oldWidth, newWidth)
    
    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.refreshTable()
        return super().resizeEvent(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.modifiers() & Qt.ControlModifier and e.key() == Qt.Key_C:
            headers = e.modifiers() & Qt.ShiftModifier
            return self.copyToClipboard(headers)
        if e.modifiers() & Qt.ControlModifier and e.key() == Qt.Key_V:
            # TODO
            return self.pasteFromClipBoard()
        
        return super().keyPressEvent(e)

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        """Zoom in/out table."""
        if a0.modifiers() & Qt.ControlModifier:
            dt = a0.angleDelta().y() / 120
            zoom = self.zoom() + 0.15 * dt
            self.setZoom(min(max(zoom, 0.25), 2.0))
            return None
                
        return super().wheelEvent(a0)
    
    def copyToClipboard(self, headers: bool = True):
        import pandas as pd
        selections = self.selections()
        if len(selections) == 0:
            return
        r_ranges = set()
        c_ranges = set()
        for rsel, csel in selections:
            r_ranges.add((rsel.start, rsel.stop))
            c_ranges.add((csel.start, csel.stop))
        
        nr = len(r_ranges)
        nc = len(c_ranges)
        if nr > 1 and nc > 1:
            show_messagebox(
                mode="error", title="Error", text="Wrong selection range.", parent=self
            )
            return
        else:
            data = self.getDataFrame()
            if nr == 1:
                axis = 1
            else:
                axis = 0
            ref = pd.concat([data.iloc[sel] for sel in selections], axis=axis)
            ref.to_clipboard(index=headers, header=headers)
    
    def pasteFromClipBoard(self):
        """
        Paste data to table.
        
        This function supports many types of pasting.
        1. Single selection, single data in clipboard -> just paste
        2. Single selection, multiple data in clipboard -> paste starts from the selection position.
        3. Multiple selection, single data in clipboard -> paste the same value for all the selection.
        4. Multiple selection, multiple data in clipboard -> paste only if their shape is identical.
        
        Also, if data is filtrated, pasted data also follows the filtration.
        """
        selections = self.selections()
        n_selections = len(selections)
        if n_selections == 0:
            return
        elif n_selections > 1:
            show_messagebox(
                mode="error",
                title="Error",
                text="Cannot paste with multiple selections.", 
                parent=self,
            )
            return
        
        import pandas as pd
        df = pd.read_clipboard(header=None)
        
        # check size
        sel = selections[0]
        rrange, crange = sel
        rlen = rrange.stop - rrange.start
        clen = crange.stop - crange.start
        dr, dc = df.shape
        size = dr * dc
        if rlen * clen == 1 and size > 1:
            sel = (slice(rrange.start, rrange.start + dr), slice(crange.start, crange.start + dc))
        elif size > 1 and dc(rlen, clen) != (dr, dc):
            show_messagebox(
                mode="error",
                title="Error",
                text=f"Shape mismatch between data in clipboard {(rlen, clen)} and destination {(dr, dc)}.", 
                parent=self,
            )
            return
        try:
            self.setDataFrameValue(sel[0], sel[1], df.values, absolute=False)
        except Exception as e:
            show_messagebox(
                mode="error",
                title=e.__class__.__name__,
                text=str(e), 
                parent=self,
            )
            return
            
        self.refreshTable()
        return None
        
    def refreshTable(self):
        data = self.getDataFrame()
        r0, c0, r1, c1 = self._get_square()
        
        nr = self.rowCount()
        nc = self.columnCount()
        
        nr_data, nc_data = self.getDataFrame().shape
        
        # check shape mismatch between DataFrame and table widget.
        if nr > nr_data:
            [self.removeRow(nr_data) for _ in range(nr - nr_data)]
        elif nr < nr_data:
            [self.insertRow(i) for i in range(nr_data - nr)]
        
        if nc > nc_data:
            [self.removeColumn(nc_data) for _ in range(nc - nc_data)]
        elif nc < nc_data:
            [self.insertColumn(i) for i in range(nc_data - nc)]
            
        r1 = min(r1, nr_data)
        c1 = min(c1, nc_data)
            
        vindex = data.index
        hindex = data.columns
        for r in range(r0, r1):
            vitem = self.verticalHeaderItem(r)
            text = str(vindex[r])
            if vitem is not None:
                vitem.setText(text)
            else:
                self.setVerticalHeaderItem(r, QtW.QTableWidgetItem(text))
            for c in range(c0, c1):
                item = self.item(r, c)
                text = str(data.iloc[r, c])
                if item is not None:
                    self.item(r, c).setText(text)
                else:
                    item = QtW.QTableWidgetItem(text)
                    self.setItem(r, c, item)
                # item.setBackground()
        
        for c in range(c0, c1):
            hitem = self.horizontalHeaderItem(c)
            text = str(hindex[c])
            if hitem is not None:
                hitem.setText(text)
            else:
                self.setHorizontalHeaderItem(c, QtW.QTableWidgetItem(text))
    
    def _get_square(self) -> tuple[int, int, int, int]:
        """Get index range of (row_start, column_start, row_end, column_end)."""
        r0 = self.rowAt(0)
        c0 = self.columnAt(0)
        r1 = self.rowAt(self.height())
        c1 = self.columnAt(self.width())
        if r1 < 0:
            r1 = self.rowCount() - 1
        if c1 < 0:
            c1 = self.columnCount() - 1
        return r0, c0, r1 + 1, c1 + 1

    def filter(self) -> FilterType | None:
        return self._filter_slice

    def setFilter(self, sl: FilterType):
        self._filter_slice = sl
        self.refreshTable()
    
    # def addFinder(self, finder: Callable[]):
    #     self.findItems()


# modified from magicgui
class TableItemDelegate(QtW.QStyledItemDelegate):
    """Displays table widget items with properly formatted numbers."""
    
    edited = Signal(tuple)
    
    def __init__(self, parent: QtCore.QObject | None = None, ndigits: int = 4) -> None:
        super().__init__(parent)
        self.ndigits = ndigits

    def displayText(self, value, locale):
        return super().displayText(self._format_number(value), locale)

    def setEditorData(self, editor: QtW.QLineEdit, index: QtCore.QModelIndex) -> None:
        super().setEditorData(editor, index)
        # NOTE: This method is evoked when editing started and editing finished.
        # The editor widget has focus only when editing is finished.
        if editor.hasFocus():
            self.edited.emit((index.row(), index.column()))
    
    def paint(self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex) -> None:
        return super().paint(painter, option, index)
        
    def _format_number(self, text: str) -> str:
        """convert string to int or float if possible"""
        try:
            value: int | float | None = int(text)
        except ValueError:
            try:
                value = float(text)
            except ValueError:
                value = None
        
        ndigits = self.ndigits
        
        if isinstance(value, (int, float)):
            if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
                text = str(value) if isinstance(value, int) else f"{value:.{ndigits}f}"
            else:
                text = f"{value:.{ndigits-1}e}"

        return text

_DTYPE_KIND_TO_CONVERTER = {
    "i": int,
    "f": float,
    "u": int,
    "U": str,
    "O": str,
    "c": complex,
}
