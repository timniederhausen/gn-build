#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import os
import subprocess
import sys

def _RegistryGetValueUsingWinReg(key, value):
  """Use the _winreg module to obtain the value of a registry key.

  Args:
    key: The registry key.
    value: The particular registry value to read.
  Return:
    contents of the registry key's value, or None on failure.  Throws
    ImportError if _winreg is unavailable.
  """
  import _winreg
  try:
    root, subkey = key.split('\\', 1)
    assert root == 'HKLM'  # Only need HKLM for now.
    with _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, subkey) as hkey:
      return _winreg.QueryValueEx(hkey, value)[0]
  except WindowsError:
    return None


def _RegistryGetValue(key, value):
  try:
    return _RegistryGetValueUsingWinReg(key, value)
  except ImportError:
    raise Exception('The python library _winreg not found.')


def _ExtractImportantEnvironment(output_of_set):
  """Extracts environment variables required for the toolchain to run from
  a textual dump output by the cmd.exe 'set' command."""
  envvars_to_save = (
      'include',
      'lib',
      'libpath',
      'path',
      'pathext',
      'systemroot',
      'temp',
      'tmp',
      )
  env = {}
  # This occasionally happens and leads to misleading SYSTEMROOT error messages
  # if not caught here.
  if output_of_set.count('=') == 0:
    raise Exception('Invalid output_of_set. Value is:\n%s' % output_of_set)
  for line in output_of_set.splitlines():
    for envvar in envvars_to_save:
      if re.match(envvar + '=', line.lower()):
        var, setting = line.split('=', 1)
        if envvar == 'path':
          # Our own rules (for running gyp-win-tool) and other actions in
          # Chromium rely on python being in the path. Add the path to this
          # python here so that if it's not in the path when ninja is run
          # later, python will still be found.
          setting = os.path.dirname(sys.executable) + os.pathsep + setting
        env[var.upper()] = setting
        break
  for required in ('SYSTEMROOT', 'TEMP', 'TMP'):
    if required not in env:
      raise Exception('Environment variable "%s" '
                      'required to be set to valid path' % required)
  return env


def _LoadEnvFromBat(args):
  """Given a bat command, runs it and returns env vars set by it."""
  args = args[:]
  args.extend(('&&', 'set'))
  popen = subprocess.Popen(
      args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  variables, _ = popen.communicate()
  if popen.returncode != 0:
    raise Exception('"%s" failed with error %d' % (args, popen.returncode))
  return variables


def _LoadToolchainEnv(vs_path, cpu):
  """Returns a dictionary with environment variables that must be set while
  running binaries from the toolchain (e.g. INCLUDE and PATH for cl.exe)."""
  # Check if we are running in the SDK command line environment and use
  # the setup script from the SDK if so. |cpu| should be either
  # 'x86' or 'x64'.
  assert cpu in ('x86', 'x64')

  # We only support x64-hosted tools.
  args = [os.path.normpath(os.path.join(vs_path,
                                        'VC/vcvarsall.bat')),
          'amd64_x86' if cpu == 'x86' else 'amd64']
  variables = _LoadEnvFromBat(args)
  return _ExtractImportantEnvironment(variables)


def _FormatAsEnvironmentBlock(envvar_dict):
  """Format as an 'environment block' directly suitable for CreateProcess.
  Briefly this is a list of key=value\0, terminated by an additional \0. See
  CreateProcess documentation for more details."""
  block = ''
  nul = '\0'
  for key, value in envvar_dict.iteritems():
    block += key + '=' + value + nul
  block += nul
  return block


def DetectVisualStudioPath(version_as_year):
  """Return path to the version_as_year of Visual Studio.
  """

  year_to_version = {
      '2013': '12.0',
      '2015': '14.0',
  }
  if version_as_year not in year_to_version:
    raise Exception(('Visual Studio version %s (from version_as_year)'
                     ' not supported. Supported versions are: %s') % (
                       version_as_year, ', '.join(year_to_version.keys())))
  version = year_to_version[version_as_year]
  keys = [r'HKLM\Software\Microsoft\VisualStudio\%s' % version,
          r'HKLM\Software\Wow6432Node\Microsoft\VisualStudio\%s' % version]
  for key in keys:
    path = _RegistryGetValue(key, 'InstallDir')
    if not path:
      continue
    path = os.path.normpath(os.path.join(path, '..', '..'))
    return path

  raise Exception(('Visual Studio Version %s (from version_as_year)'
                   ' not found.') % (version_as_year))


def YearToVersionNumber(version_as_year):
  """Gets the standard version number ('120', '140', etc.) based on
  version_as_year."""
  if version_as_year == '2013':
    return '120'
  elif version_as_year == '2015':
    return '140'
  else:
    raise ValueError('Unexpected version_as_year')


def GetVsPath(version_as_year):
  """Gets location information about the current toolchain. This is used for the GN build."""
  print DetectVisualStudioPath(version_as_year)


def SetupToolchain(vs_path):
  cpus = ('x86', 'x64')

  bin_dirs = {}
  for cpu in cpus:
    # Extract environment variables for subprocesses.
    env = _LoadToolchainEnv(vs_path, cpu)

    for path in env['PATH'].split(os.pathsep):
      if os.path.exists(os.path.join(path, 'cl.exe')):
        bin_dirs[cpu] = os.path.realpath(path)
        break

    env_block = _FormatAsEnvironmentBlock(env)
    with open('environment.' + cpu, 'wb') as f:
      f.write(env_block)

    # Create a store app version of the environment.
    if 'LIB' in env:
      env['LIB']     = env['LIB']    .replace(r'\VC\LIB', r'\VC\LIB\STORE')
    if 'LIBPATH' in env:
      env['LIBPATH'] = env['LIBPATH'].replace(r'\VC\LIB', r'\VC\LIB\STORE')
    env_block = _FormatAsEnvironmentBlock(env)
    with open('environment.winrt_' + cpu, 'wb') as f:
        f.write(env_block)

  print '''x86_bin_dir = "%s"
x64_bin_dir = "%s"''' % (bin_dirs['x86'], bin_dirs['x64'])

def main():
  commands = {
      'get_vs_dir': GetVsPath,
      'setup_toolchain': SetupToolchain,
  }
  if len(sys.argv) < 2 or sys.argv[1] not in commands:
    print >>sys.stderr, 'Expected one of: %s' % ', '.join(commands)
    return 1
  return commands[sys.argv[1]](*sys.argv[2:])


if __name__ == '__main__':
  sys.exit(main())
