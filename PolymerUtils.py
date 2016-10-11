import os
import sublime
from .PolymerSettings import PolymerSettings

_debouncers = {}
_debouncer_id = 0

def debounce(key, func, view=None):
  global _debouncers, _debouncer_id
  _debouncer_id += 1
  current_debouncer_id = _debouncer_id
  _debouncers[key] = current_debouncer_id

  def callback():
    debouncer_id = +_debouncers.get(key, None)
    if debouncer_id == current_debouncer_id:
      func(view)

  if PolymerSettings.ST3:
      set_timeout = sublime.set_timeout_async
  else:
      set_timeout = sublime.set_timeout

  set_timeout(callback, PolymerSettings.get_debounce_delay())