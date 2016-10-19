import os
import sublime
import threading

_ST3 = int(sublime.version()) >= 3000
_debouncers = {}
_debouncer_id = 0

if _ST3:
  from .PolymerSettings import PolymerSettings
else:
  from PolymerSettings import *

### Async helpers

if _ST3:
  def run_async(cb, delay):
    sublime.set_timeout_async(cb, delay)
else:
  class RunAsync(threading.Thread):
    def __init__(self, cb, delay):
      self.cb = cb
      self.delay = delay
      threading.Thread.__init__(self)

    def run(self):
      sublime.set_timeout(self.cb, self.delay)

  def run_async(cb, delay):
    RunAsync(cb, delay).start()


#### Debounces a function

def debounce(key, func, view=None):
  global _debouncers, _debouncer_id
  _debouncer_id += 1
  current_debouncer_id = _debouncer_id
  _debouncers[key] = current_debouncer_id

  def callback():
    debouncer_id = _debouncers.get(key, None)
    if debouncer_id == current_debouncer_id:
      func(view)

  run_async(callback, PolymerSettings.get_debounce_delay())
