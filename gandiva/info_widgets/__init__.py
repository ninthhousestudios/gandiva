"""Info widget registry.

Each entry is (widget_class, kwargs_dict) so one class can appear
multiple times with different configuration.
"""

INFO_WIDGETS: dict[str, tuple] = {}

from gandiva.info_widgets.panchanga import PanchangaWidget  # noqa: E402

INFO_WIDGETS["Panchanga"] = (PanchangaWidget, {})

from gandiva.info_widgets.nakshatra_dasha import NakshatraDashaWidget  # noqa: E402

INFO_WIDGETS["Nakshatra Dashas"] = (NakshatraDashaWidget, {})

from gandiva.info_widgets.mini_varga import MiniVargaWidget  # noqa: E402

INFO_WIDGETS["Mini Hora"] = (MiniVargaWidget, {"varga": -2})
INFO_WIDGETS["Varga"] = (MiniVargaWidget, {"varga": 9})

from gandiva.info_widgets.dignity import DignityWidget  # noqa: E402

INFO_WIDGETS["Dignity"] = (DignityWidget, {})
