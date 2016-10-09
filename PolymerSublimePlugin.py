import os
import subprocess
import json

import sublime
import sublime_plugin

ST3 = int(sublime.version()) >= 3000
DEBUGGING = True
PLUGIN_NAME = 'Polymer Sublime Plugin'

try:
    MDPOPUPS_INSTALLED = True
    import mdpopups
    # to be sure check, that ST also support popups
    if int(sublime.version()) < 3080:
        MDPOPUPS_INSTALLED = False
except:
    MDPOPUPS_INSTALLED = False

class Settings:
  config = None

  @staticmethod
  def get(key):
    if Settings.config is None:
      Settings.config = sublime.load_settings('%s.sublime-settings' % PLUGIN_NAME.replace(' ', ''))
    return Settings.config.get(key)

  @staticmethod
  def get_node_path():
    return Settings.get('node_path')[sublime.platform()]

  @staticmethod
  def get_analyzer_path():
    return os.path.dirname(os.path.realpath(__file__)) + Settings.get('polymer_analyzer')
  
  @staticmethod
  def get_warning_icon():
    return 'Packages/%s/%s' % (PLUGIN_NAME, Settings.get('warning_icon'))

  @staticmethod
  def get_debounce_delay():
    return Settings.get('debounce_delay')


class Utils:
  debouncers = {}
  debouncer_id = 0

  @staticmethod
  def debounce(key, func, view=None):
    Utils.debouncer_id += 1
    current_debouncer_id = Utils.debouncer_id
    Utils.debouncers[key] = current_debouncer_id

    def callback():
      debouncer_id = Utils.debouncers.get(key, None)
      if debouncer_id == current_debouncer_id:
        func(view)

    if ST3:
        set_timeout = sublime.set_timeout_async
    else:
        set_timeout = sublime.set_timeout

    set_timeout(callback, Settings.get_debounce_delay())


class Bridge:
  processes = {}
  cmd_id = 0

  @staticmethod
  def get_active_projects():
    return list(Bridge.processes)

  @staticmethod
  def get_command():
    return [Settings.get_node_path(), Settings.get_analyzer_path()]

  @staticmethod
  def create_process():
    return subprocess.Popen(Bridge.get_command(),
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.STDOUT)

  @staticmethod
  def get_project_process(project_path):
    if project_path not in Bridge.processes:
      process = Bridge.create_process()
      out = Bridge.send_message(process, Bridge.init_project_command(project_path))
      Bridge.processes[project_path] = process
      if out['kind'] == 'resolution':
        Bridge.processes[project_path] = process
      else:
        return None
    return Bridge.processes[project_path]

  @staticmethod
  def make_project_processes(project_data):
    if project_data is None:
      return
    for folder in project_data['folders']:
      Bridge.get_project_process(folder['path'])

  @staticmethod
  def send_message(process, input):
    if DEBUGGING: print('send_message: ', input)
    process.stdin.write((input + '\n').encode('utf8'))
    process.stdin.flush()
    out = process.stdout.readline()
    return json.loads(out.decode())['value']

  @staticmethod
  def encode_command(value):
    Bridge.cmd_id+=1
    return json.dumps({'id': Bridge.cmd_id, 'value': value})

  @staticmethod
  def init_project_command(basedir):
    return Bridge.encode_command({'kind': 'init', 'basedir': basedir})

  @staticmethod
  def get_warnings_command(local_path):
    return Bridge.encode_command({'kind': 'getWarningsFor', 'localPath': local_path})

  @staticmethod
  def file_changed_command(local_path, contents):
    return Bridge.encode_command({'kind': 'fileChanged', 'localPath': local_path, 'contents': contents})

  @staticmethod
  def get_project_path_from(file_name):
    for path in Bridge.processes:
      if file_name.find(path) == 0:
        return path
    return None

  @staticmethod
  def get_warnings(file_name):
    if file_name is None:
      return
    project_path = Bridge.get_project_path_from(file_name)
    if project_path is None:
      return
    process = Bridge.processes[project_path]
    relative_file_name = os.path.relpath(file_name, project_path)
    out = Bridge.send_message(process, Bridge.get_warnings_command(relative_file_name))
    if out['kind'] == 'resolution':
      return out['resolution']
    else:
      return {}

  @staticmethod
  def notify_file_changed(file_name, contents):
    if file_name is None:
      return False
    project_path = Bridge.get_project_path_from(file_name)
    if project_path is None:
      return False
    process = Bridge.processes[project_path]
    relative_file_name = os.path.relpath(file_name, project_path)
    out = Bridge.send_message(process, Bridge.file_changed_command(relative_file_name, contents))
    return out['kind'] == 'resolution'

  @staticmethod
  def kill(project_path):
    if project_path not in Bridge.processes:
      return
    Bridge.processes[project_path].kill()
    del Bridge.processes[project_path]


class PolymerSublimePlugin:
  @staticmethod
  def show_warnings(view, warnings):
    if view is None or warnings is None:
      return
    key = 'polymer_analyzer_%s' % 'warnings'
    regions = []

    for warning in warnings:
      srange = warning['sourceRange']
      start_position = view.text_point(srange['start']['line'], 0)
      end_position = view.text_point(srange['end']['line'], 0)
      regions.append(sublime.Region(start_position + srange['start']['column'],
          end_position + srange['end']['column']))

    view.erase_regions(key)
    view.add_regions(key, regions, 'polymer_analyzer', Settings.get_warning_icon(),
        sublime.DRAW_EMPTY |
        sublime.DRAW_NO_FILL |
        sublime.DRAW_NO_OUTLINE |
        sublime.DRAW_SQUIGGLY_UNDERLINE)

  @staticmethod
  def plugin_loaded(self):
    if DEBUGGING:
      print('plugin_loaded')
    for window in sublime.windows():
      if window.project_data() is not None:
        Bridge.make_project_processes(window.project_data())
        if window.active_view() is not None:
          PolymerSublimePlugin.show_warnings(window.active_view(),
            Bridge.get_warnings(window.active_view().file_name()))

  @staticmethod
  def plugin_unloaded():
    if DEBUGGING:
      print('plugin_unloaded')
    for path in Bridge.get_active_projects():
      Bridge.kill(path)

  def on_activated(view):
    if DEBUGGING:
      print('on_activated')
    project_data = sublime.active_window().project_data()
    if project_data is None:
      return
    Bridge.make_project_processes(project_data)
    PolymerSublimePlugin.show_warnings(view, Bridge.get_warnings(view.file_name()))

  @staticmethod
  def on_modified(view):
    if DEBUGGING:
      print('on_modified')
    Bridge.notify_file_changed(view.file_name(),
        view.substr(sublime.Region(0, view.size())) if view.is_dirty() else None)
    PolymerSublimePlugin.show_warnings(view, Bridge.get_warnings(view.file_name()))

  @staticmethod
  def on_deactivated(view):
    if DEBUGGING:
      print('on_deactivated')
    process_project = Bridge.get_active_projects()
    active_projects = []

    for window in sublime.windows():
      if window.project_data() is not None:
        for folder in window.project_data()['folders']:
          active_projects.append(folder['path'])

    for path in process_project:
      if path not in active_projects:
        Bridge.kill(path)

  @staticmethod
  def show_popup(view, point):
    if not MDPOPUPS_INSTALLED:
      return
    if DEBUGGING:
      print('show_popup')

    location = view.line(point).a
    warnings = Bridge.get_warnings(view.file_name())
    warning_msg = ''

    for warning in warnings:
      start_position = view.text_point(warning['sourceRange']['start']['line'], 0)
      if location == start_position:
        warning_msg = warning['message']
        break
    
    if warning_msg != '':
      mdpopups.show_popup(
          view, '**Polymer**: ```%s```' % warning_msg, location=location, 
          flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=int(view.viewport_extent()[0]))


class PolymerAnalyzerEvents(sublime_plugin.EventListener):
  def on_activated_async(self, view):
    Utils.debounce('activated_%s' % view.file_name(), PolymerSublimePlugin.on_activated, view)

  def on_modified_async(self, view):
    Utils.debounce('modified_%s' % view.file_name(), PolymerSublimePlugin.on_modified, view)

  def on_deactivated_async(self, view):
    Utils.debounce('deactivated_%s' % view.file_name(), PolymerSublimePlugin.on_deactivated, view)

  def on_hover(self, view, point, hover_zone):
    if hover_zone == sublime.HOVER_GUTTER and not view.is_popup_visible():
      PolymerSublimePlugin.show_popup(view, point)


def plugin_loaded():
  Utils.debounce('plugin_loaded', PolymerSublimePlugin.plugin_loaded)

def plugin_unloaded():
  PolymerSublimePlugin.plugin_unloaded()

