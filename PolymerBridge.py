import os
import subprocess
import json
import sublime
from functools import partial

_ST3 = int(sublime.version()) >= 3000

if _ST3:
  from .PolymerSettings import PolymerSettings
else:
  from PolymerSettings import *

class PolymerBridge:
  processes = {}
  cmd_id = 0

  @staticmethod
  def get_active_projects():
    return list(PolymerBridge.processes)

  @staticmethod
  def get_command():
    return [PolymerSettings.get_node_path(), PolymerSettings.get_analyzer_path()]

  @staticmethod
  def create_process():
    return subprocess.Popen(PolymerBridge.get_command(),
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.STDOUT)

  @staticmethod
  def kill(folder):
    if folder not in PolymerBridge.processes:
      return
    PolymerBridge.processes[folder].kill()
    del PolymerBridge.processes[folder]

  @staticmethod
  def get_project_process(folder):
    if folder not in PolymerBridge.processes:
      process = PolymerBridge.create_process()
      out = PolymerBridge.send_message(process, PolymerBridge.init_project_command(folder))
      PolymerBridge.processes[folder] = process
      if out['kind'] == 'resolution':
        PolymerBridge.processes[folder] = process
      else:
        return None
    return PolymerBridge.processes[folder]

  @staticmethod
  def make_project_processes(folders):
    if folders is None:
      return
    for folder in folders:
      PolymerBridge.get_project_process(folder)

  @staticmethod
  def send_message(process, input):
    if PolymerSettings.debugging():
      print('send_message: ', input)
    process.stdin.write((input + '\n').encode('utf8'))
    process.stdin.flush()
    out = process.stdout.readline()
    return json.loads(out.decode())['value']
  
  @staticmethod
  def encode_command(value):
    PolymerBridge.cmd_id+=1
    return json.dumps({'id': PolymerBridge.cmd_id, 'value': value})

  @staticmethod
  def init_project_command(basedir):
    return PolymerBridge.encode_command({'kind': 'init', 'basedir': basedir})

  @staticmethod
  def get_warnings_command(local_path):
    return PolymerBridge.encode_command({'kind': 'getWarningsFor', 'localPath': local_path})

  @staticmethod
  def file_changed_command(contents, local_path):
    return PolymerBridge.encode_command({'kind': 'fileChanged', 'localPath': local_path,
        'contents': contents})

  @staticmethod
  def get_definition_command(line, column, local_path):
    return PolymerBridge.encode_command({'kind': 'getTypeaheadCompletionsFor', 'localPath': local_path,
        'position': {'line': line, 'column': column}})

  @staticmethod
  def get_project_path_from(file_name):
    for path in PolymerBridge.processes:
      if file_name.find(path) == 0:
        return path
    return None

  @staticmethod
  def execute_command(file_name, fn):
    if file_name is None:
      return
    project_path = PolymerBridge.get_project_path_from(file_name)
    if project_path is None:
      return
    process = PolymerBridge.processes[project_path]
    relative_file_name = os.path.relpath(file_name, project_path)
    out = PolymerBridge.send_message(process, fn(relative_file_name))
    if out['kind'] == 'resolution' and 'resolution' in out:
      return out['resolution']
    else:
      return {}

  @staticmethod
  def get_warnings(file_name):
    return PolymerBridge.execute_command(file_name, PolymerBridge.get_warnings_command)

  @staticmethod
  def notify_file_changed(file_name, contents):
    return PolymerBridge.execute_command(file_name, partial(PolymerBridge.file_changed_command, contents))

  @staticmethod
  def get_definition(file_name, line, column):
    return PolymerBridge.execute_command(file_name, partial(PolymerBridge.get_definition_command, line, column))
