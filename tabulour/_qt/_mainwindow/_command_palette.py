from __future__ import annotations

from typing import  Any, Callable
import logging
from qt_command_palette import get_palette
from tabulour import commands as cmds
from tabulour._utils import get_config
from ._mainwidgets import QMainWindow, QMainWidget

from ._base import _QtMainWidgetBase
from ...widgets import TableViewerBase

logger = logging.getLogger("tabulour")


def _command_to_viewer_function(
    f: Callable[[TableViewerBase], Any]
) -> Callable[[_QtMainWidgetBase], Any]:
    def wrapper(self: _QtMainWidgetBase):
        logger.debug(f"Command: {f.__module__.split('.')[-1]}.{f.__name__}")
        return f(self._table_viewer)

    wrapper.__doc__ = f.__doc__
    return wrapper


def load_all_commands():

    palette = get_palette("tabulour")

    window_group = palette.add_group("Window")
    file_group = palette.add_group("File")
    table_group = palette.add_group("Table")
    tab_group = palette.add_group("Tab")
    analysis_group = palette.add_group("Analysis")
    view_group = palette.add_group("View")
    plot_group = palette.add_group("Plot")
    selection_group = palette.add_group("Selection")
    column_group = palette.add_group("Column")

    _groups = {
        "window": window_group,
        "file": file_group,
        "table": table_group,
        "tab": tab_group,
        "analysis": analysis_group,
        "view": view_group,
        "plot": plot_group,
        "selection": selection_group,
        "column": column_group,
    }

    kb = get_config().keybindings.copy()

    for mod, cmd in cmds.iter_commands():
        group = _groups[mod]
        group.register(_command_to_viewer_function(cmd), desc=cmd.__doc__)
        if seq := kb.pop(f"{mod}.{cmd.__name__}", None):
            # register to main widgets
            f = _command_to_viewer_function(cmd)
            if isinstance(seq, str):
                QMainWidget._keymap.bind(seq)(f)
                QMainWindow._keymap.bind(seq)(f)
            elif isinstance(seq, list):
                for s in seq:
                    QMainWidget._keymap.bind(s)(f)
                    QMainWindow._keymap.bind(s)(f)

    if kb:
        import warnings

        keys = ", ".join(kb.keys())
        warnings.warn(f"Unrecognized commands: {keys}")


load_all_commands()
