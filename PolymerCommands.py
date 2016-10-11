import sublime
import sublime_plugin

_ST3 = int(sublime.version()) >= 3000

if _ST3:
  from .PolymerSublimePlugin import PolymerSublimePlugin
  from .PolymerBridge import PolymerBridge
else:
  from PolymerSublimePlugin import *
  from PolymerBridge import *

class PolymerCommand(sublime_plugin.TextCommand):
  warnings = []

  def run(self, edit):
    view = sublime.active_window().active_view()
    self.warnings = PolymerBridge.get_warnings(view.file_name())
    items = []

    PolymerSublimePlugin.show_warnings(view, self.warnings)

    if self.warnings is not None:
      for warning in self.warnings:
        items.append(warning['message'])
      self.view.window().show_quick_panel(items, self.on_quick_panel_click)

  def on_quick_panel_click(self, index):
    if self.warnings is None or index == -1:
      return

    view = sublime.active_window().active_view()
    warning = self.warnings[index]
    srange = warning['sourceRange']
    start_position = view.text_point(srange['start']['line'], 0)
    end_position = view.text_point(srange['end']['line'], 0)
    region_cursor = sublime.Region(start_position + srange['start']['column'],
        end_position + srange['end']['column'])

    selection = view.sel()
    selection.clear()
    selection.add(region_cursor)
    self.view.show(region_cursor)
