import os
import sublime

_ST3 = int(sublime.version()) >= 3000
_PLUGIN_NAME = 'polymer-sublime-plugin'

class PolymerSettings:
  config = None

  @staticmethod
  def get(key):
    if PolymerSettings.config is None:
      PolymerSettings.config = sublime.load_settings('%s.sublime-settings' % _PLUGIN_NAME)
    return PolymerSettings.config.get(key)

  @staticmethod
  def get_node_path():
    return PolymerSettings.get('node_path')[sublime.platform()]

  @staticmethod
  def get_analyzer_path():
    return sublime.packages_path() + os.path.sep + _PLUGIN_NAME + \
        os.path.sep + PolymerSettings.get('polymer_analyzer')

  @staticmethod
  def get_warning_icon():
    if _ST3:
      return 'Packages' + os.path.sep + _PLUGIN_NAME + os.path.sep + 'warning.png'
    else:
      return '..' + os.path.sep + _PLUGIN_NAME + os.path.sep + 'warning'

  @staticmethod
  def get_debounce_delay():
    return PolymerSettings.get('debounce_delay')

  @staticmethod
  def get_static_completions():
    return PolymerSettings.get('static_completions')

  @staticmethod
  def debugging():
    return PolymerSettings.get('debugging')
