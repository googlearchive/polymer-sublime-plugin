import sublime
import sublime_plugin
from .PolymerUtils import debounce
from .PolymerSublimePlugin import PolymerSublimePlugin

class PolymerEvents(sublime_plugin.EventListener):
  def on_activated_async(self, view):
    debounce('activated_%s' % view.file_name(), PolymerSublimePlugin.on_activated, view)

  def on_modified_async(self, view):
    debounce('modified_%s' % view.file_name(), PolymerSublimePlugin.on_modified, view)

  def on_deactivated_async(self, view):
    debounce('deactivated_%s' % view.file_name(), PolymerSublimePlugin.on_deactivated, view)

  def on_hover(self, view, point, hover_zone):
    if hover_zone == sublime.HOVER_GUTTER and not view.is_popup_visible():
      PolymerSublimePlugin.show_popup(view, point)

  def on_query_completions(self, view, prefix, locations):
    return PolymerSublimePlugin.get_query_completions(view, prefix, locations)

def plugin_loaded():
  debounce('plugin_loaded', PolymerSublimePlugin.plugin_loaded)

def plugin_unloaded():
  PolymerSublimePlugin.plugin_unloaded()