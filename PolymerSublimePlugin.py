import re
import sublime
from .PolymerSettings import PolymerSettings
from .PolymerBridge import PolymerBridge

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
    view.add_regions(key, regions, 'polymer_analyzer', PolymerSettings.get_warning_icon(),
        sublime.DRAW_EMPTY |
        sublime.DRAW_NO_FILL |
        sublime.DRAW_NO_OUTLINE |
        sublime.DRAW_SQUIGGLY_UNDERLINE)

  @staticmethod
  def plugin_loaded(self):
    if PolymerSettings.debugging():
      print('plugin_loaded')
    for window in sublime.windows():
      if window.project_data() is not None:
        PolymerBridge.make_project_processes(window.project_data())
        if window.active_view() is not None:
          PolymerSublimePlugin.show_warnings(window.active_view(),
            PolymerBridge.get_warnings(window.active_view().file_name()))

  @staticmethod
  def plugin_unloaded():
    if PolymerSettings.debugging():
      print('plugin_unloaded')
    for path in PolymerBridge.get_active_projects():
      PolymerBridge.kill(path)

  def on_activated(view):
    if PolymerSettings.debugging():
      print('on_activated')
    project_data = sublime.active_window().project_data()
    if project_data is None:
      return
    PolymerBridge.make_project_processes(project_data)
    PolymerSublimePlugin.show_warnings(view, PolymerBridge.get_warnings(view.file_name()))

  @staticmethod
  def on_modified(view):
    if PolymerSettings.debugging():
      print('on_modified')
    PolymerBridge.notify_file_changed(view.file_name(),
        view.substr(sublime.Region(0, view.size())) if view.is_dirty() else None)
    PolymerSublimePlugin.show_warnings(view, PolymerBridge.get_warnings(view.file_name()))

  @staticmethod
  def on_deactivated(view):
    if PolymerSettings.debugging():
      print('on_deactivated')
    process_project = PolymerBridge.get_active_projects()
    active_projects = []

    for window in sublime.windows():
      if window.project_data() is not None:
        for folder in window.project_data()['folders']:
          active_projects.append(folder['path'])

    for path in process_project:
      if path not in active_projects:
        PolymerBridge.kill(path)

  @staticmethod
  def show_popup(view, point):
    if PolymerSettings.debugging():
      print('show_popup')

    location = view.line(point).a
    warnings = PolymerBridge.get_warnings(view.file_name())
    warning_msg = ''

    for warning in warnings:
      start_position = view.text_point(warning['sourceRange']['start']['line'], 0)
      if location == start_position:
        warning_msg = warning['message']
        break

    if warning_msg != '':
      view.show_popup('Polymer Analyzer: %s' % warning_msg, location=location,
          flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, max_width=int(view.viewport_extent()[0]))

  @staticmethod
  def get_query_completions(view, prefix, locations):
    if not locations:
      return
    scope_name = view.scope_name(locations[0]).strip()
    line, column = view.rowcol(locations[0])
    completions = []

    if scope_name == 'text.html.basic':
      definition = PolymerBridge.get_definition(view.file_name(), line, column)
      begins_with_tag = view.substr(locations[0]-1) == '<'
      # Add static completions.
      if begins_with_tag:
        for static_completion in PolymerSettings.get_static_completions()['tags']:
          static_completion[1] = static_completion[1][1:]
          completions.append(static_completion)
      else:
        completions = completions + PolymerSettings.get_static_completions()['tags']

      if definition is not None:
        if 'elements' in definition:
          for el in definition['elements']:
            tagname = el['tagname']
            if tagname.startswith('dom-'):
              continue
            # Try to extract the snippet from the description.
            m_start = re.search(r'<%s(.*)>' % tagname, el['description'])
            m_end = re.search(r'</%s>' % tagname, el['description'])
            if m_start and m_end:
              expandTo = el['description'][m_start.start():m_end.end()]
            else:
              expandTo = el['expandTo']
            completions.append([tagname, expandTo[1:] if begins_with_tag else expandTo])
    elif 'text.html.basic meta.tag.custom.html' in scope_name:
      definition = PolymerBridge.get_definition(view.file_name(), line, column)

      if 'attributes' in definition:
        for attr in definition['attributes']:
          # If the type isn't a boolean then add `attr=""` otherwise add `attr`.
          completions.append([attr['name'],
              attr['name'] if attr['type'] == 'boolean'
              else '%s="${0:%s}"' % (attr['name'], attr['type'])])
    return completions
