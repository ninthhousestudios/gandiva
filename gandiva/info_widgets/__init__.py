"""Info widget registry.

Each entry is (widget_class, kwargs_dict) so one class can appear
multiple times with different configuration.
"""

INFO_WIDGETS: dict[str, tuple] = {}

from gandiva.info_widgets.panchanga import PanchangaWidget  # noqa: E402

INFO_WIDGETS["Panchanga"] = (PanchangaWidget, {})

from gandiva.info_widgets.dasha import DashaWidget  # noqa: E402

INFO_WIDGETS["Dasha Periods"] = (DashaWidget, {})
