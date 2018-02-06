#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
import gn_helpers

def _RegistryGetValueUsingWinReg(key, value):
  """Use the _winreg module to obtain the value of a registry key.

  Args:
    key: The registry key.
    value: The particular registry value to read.
  Return:
    contents of the registry key's value, or None on failure.  Throws
    ImportError if _winreg is unavailable.
  """
  try:
    import _winreg
  except ImportError:
    import winreg as _winreg
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
      'windowssdkdir',
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


def _Call(args, **kwargs):
  popen = subprocess.Popen(args, shell=True, universal_newlines=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           **kwargs)
  out, _ = popen.communicate()
  if popen.returncode != 0:
    raise Exception('"%s" failed with error %d' % (args, popen.returncode))
  return out


def _LoadEnvFromBat(args):
  """Given a bat command, runs it and returns env vars set by it."""
  args = args[:]
  args.extend(('&&', 'set'))
  return _Call(args)


def _LoadToolchainEnv(vs_path, cpu, sdk_version):
  """Returns a dictionary with environment variables that must be set while
  running binaries from the toolchain (e.g. INCLUDE and PATH for cl.exe)."""
  # Check if we are running in the SDK command line environment and use
  # the setup script from the SDK if so. |cpu| should be either
  # 'x86' or 'x64'.
  assert cpu in ('x86', 'x64')

  script_path = os.path.join(vs_path, 'VC', 'vcvarsall.bat')
  if not os.path.exists(script_path):
    script_path = os.path.join(vs_path, 'VC', 'Auxiliary',
                               'Build', 'vcvarsall.bat')
    if not os.path.exists(script_path):
      raise Exception('%s doesn\'t exist. Does your VS have C++ support?' %
                      script_path)

  # We only support x64-hosted tools.
  # TODO(tim): change that?
  arch_name = 'amd64_x86' if cpu == 'x86' else 'amd64'

  args = [script_path, arch_name]
  if sdk_version and sdk_version != 'default':
    args.append(sdk_version)
  variables = _LoadEnvFromBat(args)
  return _ExtractImportantEnvironment(variables)


def _FormatAsEnvironmentBlock(envvar_dict):
  """Format as an 'environment block' directly suitable for CreateProcess.
  Briefly this is a list of key=value\0, terminated by an additional \0. See
  CreateProcess documentation for more details."""
  encoding = sys.getfilesystemencoding()
  block = b''
  nul = b'\0'
  for key, value in envvar_dict.items():
    block += key.encode(encoding) + b'=' + value.encode(encoding) + nul
  block += nul
  return block


def _ParseClVersion(out):
  for line in out.splitlines():
    m = re.search(r'Version ([0-9.]+)', line)
    if not m:
      continue

    version = m.group(1).split('.')
    if len(version) < 3 or len(version[0]) != 2 or len(version[1]) != 2 or \
       len(version[2]) != 5:
      raise Exception("Invalid MSVC version: " + str(version))

    return int(''.join(version[:3]))

  raise Exception("Failed to find MSVC version string in: " + out)


def _GetClangMscVersionFromYear(version_as_year):
  year_to_version = {
      '2013': '1800',
      '2015': '1900',
      '2017': '1910',
  }
  if version_as_year not in year_to_version:
    raise Exception(('Visual Studio version %s (from version_as_year)'
                     ' not supported. Supported versions are: %s') % (
                       version_as_year, ', '.join(year_to_version.keys())))
  return year_to_version[version_as_year]


def _GetClangVersion(clang_base_path, msc_ver):
  clang_version = 0
  msc_full_ver = 0

  path = os.path.join(clang_base_path, 'bin', 'clang-cl')
  cmd = 'echo "" | "{}" -fmsc-version={} -Xclang -dM -E -'.format(path, msc_ver)
  output = subprocess.check_output(cmd, shell=True, universal_newlines=True)

  for define in output.splitlines():
    define = re.findall(r'#define ([a-zA-Z0-9_]+) (.*)', define)
    if not define:
      continue

    name, value = define[0]
    if name == '__clang_major__':
      clang_version += 10000 * int(value)
    elif name == '__clang_minor__':
      clang_version += 100 * int(value)
    elif name == '__clang_patchlevel__':
      clang_version += int(value)
    elif name == '_MSC_FULL_VER':
      msc_full_ver = int(value)

  return clang_version, msc_full_ver


def DetectVisualStudioPath(version_as_year):
  """Return path to the version_as_year of Visual Studio.
  """

  year_to_version = {
      '2013': '12.0',
      '2015': '14.0',
      '2017': '15.0',
  }

  if version_as_year not in year_to_version:
    raise Exception(('Visual Studio version %s (from version_as_year)'
                     ' not supported. Supported versions are: %s') % (
                       version_as_year, ', '.join(year_to_version.keys())))

  if version_as_year == '2017':
    # The VC++ 2017 install location needs to be located using COM instead of
    # the registry. For details see:
    # https://blogs.msdn.microsoft.com/heaths/2016/09/15/changes-to-visual-studio-15-setup/
    # For now we use a hardcoded default with an environment variable override.
    root_path = r'C:\Program Files (x86)\Microsoft Visual Studio\2017'
    for edition in ['Professional', 'Community']:
      path = os.environ.get('vs2017_install', os.path.join(root_path, edition))
      if os.path.exists(path):
        return path
  else:
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


def GetVsPath(version_as_year):
  """Gets location information about the current toolchain. This is used for the GN build."""
  print(DetectVisualStudioPath(version_as_year))


def SetupToolchain(version_as_year, vs_path, include_prefix, sdk_version=None, clang_base_path=None, clang_msc_ver=None):
  cpus = ('x86', 'x64')

  bin_dirs = {}
  windows_sdk_paths = {}
  include_flags = {}
  envs = {}

  for cpu in cpus:
    # Extract environment variables for subprocesses.
    env = _LoadToolchainEnv(vs_path, cpu, sdk_version)
    envs[cpu] = env

    windows_sdk_paths[cpu] = os.path.realpath(env['WINDOWSSDKDIR'])

    for path in env['PATH'].split(os.pathsep):
      if os.path.exists(os.path.join(path, 'cl.exe')):
        bin_dirs[cpu] = os.path.realpath(path)
        break

    # The separator for INCLUDE here must match the one used in
    # _LoadToolchainEnv() above.
    include = [include_prefix + p for p in env['INCLUDE'].split(';') if p]
    include = ' '.join(['"' + i.replace('"', r'\"') + '"' for i in include])
    include_flags[cpu] = include

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

  if len(set(windows_sdk_paths.values())) != 1:
    raise Exception("WINDOWSSDKDIR is different for x86/x64")

  print('x86_bin_dir = ' + gn_helpers.ToGNString(bin_dirs['x86']))
  print('x64_bin_dir = ' + gn_helpers.ToGNString(bin_dirs['x64']))

  print('x86_include_flags = ' + gn_helpers.ToGNString(include_flags['x86']))
  print('x64_include_flags = ' + gn_helpers.ToGNString(include_flags['x64']))

  # SDK is always the same
  print('windows_sdk_path = ' + gn_helpers.ToGNString(windows_sdk_paths['x86']))

  # TODO(tim): Check for mismatches between x86 and x64?
  if clang_base_path:
    msc_ver = clang_msc_ver or _GetClangMscVersionFromYear(version_as_year)
    clang_version, msc_full_ver = _GetClangVersion(clang_base_path, msc_ver)
    print('clang_version = ' + gn_helpers.ToGNString(clang_version))
    print('msc_ver = ' + gn_helpers.ToGNString(msc_full_ver // 100000))
    print('msc_full_ver = ' + gn_helpers.ToGNString(msc_full_ver))
  else:
    msc_full_ver = _ParseClVersion(_Call(['cl'], env=envs['x86']))
    print('msc_ver = ' + gn_helpers.ToGNString(msc_full_ver // 100000))
    print('msc_full_ver = ' + gn_helpers.ToGNString(msc_full_ver))


def main():
  commands = {
      'get_vs_dir': GetVsPath,
      'setup_toolchain': SetupToolchain,
  }
  if len(sys.argv) < 2 or sys.argv[1] not in commands:
    sys.stderr.write('Expected one of: %s\n' % ', '.join(commands))
    return 1
  return commands[sys.argv[1]](*sys.argv[2:])


if __name__ == '__main__':
  sys.exit(main())
