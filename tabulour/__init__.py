__version__ = "0.0.1"

from tabulour.widgets import TableViewer, TableViewerWidget
from tabulour.core import (
    current_viewer,
    read_csv,
    read_excel,
    view_table,
    view_spreadsheet,
    open_sample,
)
from tabulour._magicgui import MagicTableViewer

__all__ = [
    "TableViewer",
    "TableViewerWidget",
    "MagicTableViewer",
    "current_viewer",
    "read_csv",
    "read_excel",
    "view_table",
    "view_spreadsheet",
    "open_sample",
]
