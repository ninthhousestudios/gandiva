got this when i was stress testing:
Traceback (most recent call last):
  File "/home/josh/nhs/soft/astrology/gandiva/gandiva/renderers/western_wheel.py", line 128, in paint
    self._draw_sign_names(p, cx, cy, r, r_sign)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/home/josh/nhs/soft/astrology/gandiva/gandiva/renderers/western_wheel.py", line 166, in _draw_sign_names
    self._draw_arc_text(p, cx, cy, r_mid, mid_ecl, label, font)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/josh/nhs/soft/astrology/gandiva/gandiva/renderers/western_wheel.py", line 188, in _draw_arc_text
    half_span_rad = total_w / (2.0 * r_arc)
                    ~~~~~~~~^~~~~~~~~~~~~~~
ZeroDivisionError: float division by zero

