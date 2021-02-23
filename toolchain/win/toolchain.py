#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re
import os
import subprocess
import itertools
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


def _Spawn(args, **kwargs):
  proc = subprocess.Popen(args, shell=True, universal_newlines=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          **kwargs)
  proc.args = args
  return proc


def _ProcessSpawnResult(proc):
  out, _ = proc.communicate()
  if proc.returncode != 0:
    raise Exception('"%s" failed with error %d' % (proc.args, popen.returncode))
  return out


def _BuildToolchainSetupCommand(vs_path, cpu, sdk_version, is_uwp=False):
  """Returns a dictionary with environment variables that must be set while
  running binaries from the toolchain (e.g. INCLUDE and PATH for cl.exe)."""
  # Check if we are running in the SDK command line environment and use
  # the setup script from the SDK if so. |cpu| should be either
  # 'x86' or 'x64' or 'arm' or 'arm64'.
  assert cpu in ('x86', 'x64', 'arm', 'arm64')

  script_path = os.path.join(vs_path, 'VC', 'vcvarsall.bat')
  if not os.path.exists(script_path):
    script_path = os.path.join(vs_path, 'VC', 'Auxiliary',
                               'Build', 'vcvarsall.bat')
    if not os.path.exists(script_path):
      raise Exception('%s doesn\'t exist. Does your VS have C++ support?' %
                      script_path)

  # We only support x64-hosted tools.
  # TODO(tim): change that?
  arch_name = "amd64"
  if (cpu != 'x64'):
    # x64 is default target CPU thus any other CPU requires a target set
    arch_name += '_' + cpu

  args = [script_path, arch_name]
  if sdk_version and sdk_version != 'default':
    args.append(sdk_version)
  if is_uwp:
    args.append('store')
  args.extend(('&&', 'set'))
  return args


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


def GetEnv(arch):
  """Gets the saved environment from a file for a given architecture."""
  # The environment is saved as an "environment block" (see CreateProcess
  # and msvs_emulation for details). We convert to a dict here.
  # Drop last 2 NULs, one for list terminator, one for trailing vs. separator.
  pairs = open(arch).read()[:-2].split('\0')
  kvs = [item.split('=', 1) for item in pairs]
  return dict(kvs)


def LoadEnvFromCache(name):
  if os.path.exists(name):
    return GetEnv(name)

  return None


def SaveEnv(name, env):
  env_block = _FormatAsEnvironmentBlock(env)
  with open(name, 'wb') as f:
    f.write(env_block)


def _ParseClVersion(out):
  for line in out.splitlines():
    m = re.search(r' ([0-9.]+)', line)
    if not m:
      continue

    version = m.group(1).split('.')
    if len(version) < 3 or len(version[0]) != 2 or len(version[1]) != 2 or \
            len(version[2]) != 5:
      raise Exception("Invalid MSVC version: " + str(version))

    return int(''.join(version[:3]))

  raise Exception("Failed to find MSVC version string in: " + out)


def _GetClangMscVersionFromYear(version_as_year):
  # Corresponds to the _MSC_VER value listed here:
  # https://docs.microsoft.com/en-us/cpp/preprocessor/predefined-macros
  year_to_version = {
    '2013': '1800',
    '2015': '1900',
    '2017': '1910',
    '2019': '1920',
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


# https://github.com/Microsoft/vswhere/blob/4b16c6302889506e2d49ff24cfa39234753412b2/README.md
_VSWHERE_PATH = r'%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe'


def DetectVisualStudioPath(version_as_year):
  """Return path to the version_as_year of Visual Studio.
  """

  year_to_version = {
    '2013': '12.0',
    '2015': '14.0',
    '2017': '15.0',
    '2019': '16.0',
  }

  if version_as_year not in year_to_version:
    raise Exception(('Visual Studio version %s (from version_as_year)'
                     ' not supported. Supported versions are: %s') % (
                      version_as_year, ', '.join(year_to_version.keys())))

  if version_as_year in ('2017', '2019'):
    # The VC++ 2017+ install location needs to be located using COM instead of
    # the registry. For details see:
    # https://blogs.msdn.microsoft.com/heaths/2016/09/15/changes-to-visual-studio-15-setup/
    vswhere_path = os.path.expandvars(_VSWHERE_PATH)
    if os.path.exists(vswhere_path):
      version = year_to_version[version_as_year]
      try:
        out = json.loads(subprocess.check_output([
          vswhere_path, '-version',
          '[{},{})'.format(float(version), float(version) + 1),
          '-legacy', '-format', 'json', '-utf8',
        ]))
        if out:
          return out[0]['installationPath']
      except subprocess.CalledProcessError:
        pass

    root_path = r'C:\Program Files (x86)\Microsoft Visual Studio\\' + version_as_year
    for edition in ['Professional', 'Community', 'Enterprise', 'BuildTools']:
      path = os.environ.get('vs{}_install'.format(version_as_year), os.path.join(root_path, edition))
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


def FindLatestVisualStudio():
  for version_as_year in ['2019', '2017', '2015', '2013']:
    try:
      return version_as_year, DetectVisualStudioPath(version_as_year)
    except Exception:
      pass
  raise Exception('No suitable Visual Studio version installed')


def GetVsPath(version_as_year):
  """Gets location information about the current toolchain. This is used for the GN build."""
  print(DetectVisualStudioPath(version_as_year))


def SetupToolchain(version_as_year, vs_path, sdk_version=None,
                   clang_base_path=None, clang_msc_ver=None):
  cpus = ('x86', 'x64', 'arm', 'arm64')

  # vcvarsall.bat for VS 2017 fails if run after running vcvarsall.bat from
  # VS 2013 or VS 2015. Fix this by clearing the vsinstalldir environment
  # variable.
  # Since vcvarsall.bat appends to the INCLUDE, LIB, and LIBPATH
  # environment variables we need to clear those to avoid getting double
  # entries when vcvarsall.bat has been run before gn gen. vcvarsall.bat
  # also adds to PATH, but there is no clean way of clearing that and it
  # doesn't seem to cause problems.
  if 'VSINSTALLDIR' in os.environ:
    del os.environ['VSINSTALLDIR']
    del os.environ['INCLUDE']
    del os.environ['LIB']
    del os.environ['LIBPATH']

  if version_as_year == 'latest':
    version_as_year, vs_path = FindLatestVisualStudio()
  elif not vs_path or vs_path == 'default':
    vs_path = DetectVisualStudioPath(version_as_year)

  # TODO(tim): We now launch all processes at once, but this still takes too long
  processes = {}
  for (cpu, is_uwp) in itertools.product(cpus, (False, True)):
    name = cpu + ('_uwp' if is_uwp else '')
    env_filename = 'environment_{}'.format(name)
    if not os.path.exists(env_filename):
      processes[name] = _Spawn(_BuildToolchainSetupCommand(vs_path, cpu, sdk_version, is_uwp))

  windows_sdk_paths = {}
  envs = {}
  for (cpu, is_uwp) in itertools.product(cpus, (False, True)):
    name = cpu + ('_uwp' if is_uwp else '')
    env_filename = 'environment_{}'.format(name)
    # Load environment variables.
    env = LoadEnvFromCache(env_filename)
    if env is None:
      # Extract environment variables for subprocesses.
      env = _ExtractImportantEnvironment(_ProcessSpawnResult(processes[name]))
      SaveEnv(env_filename, env)
    envs[name] = env

    vc_bin_dir = ''
    vc_lib_path = ''
    vc_lib_atlmfc_path = ''
    vc_lib_um_path = ''
    for path in env['PATH'].split(os.pathsep):
      if os.path.exists(os.path.join(path, 'cl.exe')):
        vc_bin_dir = os.path.realpath(path)
        break

    if not vc_bin_dir:
      continue

    for path in env['LIB'].split(os.pathsep):
      if os.path.exists(os.path.join(path, 'msvcrt.lib')):
        vc_lib_path = os.path.realpath(path)
        break

    for path in env['LIB'].split(os.pathsep):
      if os.path.exists(os.path.join(path, 'atls.lib')):
        vc_lib_atlmfc_path = os.path.realpath(path)
        break

    for path in env['LIB'].split(os.pathsep):
      if os.path.exists(os.path.join(path, 'User32.Lib')):
        vc_lib_um_path = os.path.realpath(path)
        break

    # Ignore incomplete installations.
    # e.g. VS supports ARM64, but the Windows SDK does not.
    if not vc_lib_path or not vc_lib_um_path:
      continue

    windows_sdk_paths[name] = os.path.realpath(env['WINDOWSSDKDIR'])

    # The separator for INCLUDE here must match the one used in
    # _LoadToolchainEnv() above.
    include = [p.replace('"', r'\"') for p in env['INCLUDE'].split(';') if p]

    # Make include path relative to builddir when cwd and sdk in same drive.
    try:
      include = list(map(os.path.relpath, include))
    except ValueError:
      pass

    lib = [p.replace('"', r'\"') for p in env['LIB'].split(';') if p]
    # Make lib path relative to builddir when cwd and sdk in same drive.
    try:
      lib = list(map(os.path.relpath, lib))
    except ValueError:
      pass

    def q(s):  # Quote s if it contains spaces or other weird characters.
      return s if re.match(r'^[a-zA-Z0-9._/\\:-]*$', s) else '"' + s + '"'

    include_I = ' '.join([q('/I' + i) for i in include])
    include_imsvc = ' '.join([q('-imsvc' + i) for i in include])
    libpath_flags = ' '.join([q('-libpath:' + i) for i in lib])

    print(name + ' = {')

    print('env_filename = ' + gn_helpers.ToGNString(env_filename))
    assert vc_bin_dir
    print('vc_bin_dir = ' + gn_helpers.ToGNString(vc_bin_dir))
    assert include_I
    print('include_flags_I = ' + gn_helpers.ToGNString(include_I))
    assert include_imsvc
    print('include_flags_imsvc = ' + gn_helpers.ToGNString(include_imsvc))
    assert vc_lib_path
    print('vc_lib_path = ' + gn_helpers.ToGNString(vc_lib_path))
    # Possible atlmfc library path gets introduced in the future for store thus
    # output result if a result exists.
    if vc_lib_atlmfc_path != '':
      print('vc_lib_atlmfc_path = ' + gn_helpers.ToGNString(vc_lib_atlmfc_path))
    assert vc_lib_um_path
    print('vc_lib_um_path = ' + gn_helpers.ToGNString(vc_lib_um_path))
    print('paths = ' + gn_helpers.ToGNString(env['PATH']))
    assert libpath_flags
    print('libpath_flags = ' + gn_helpers.ToGNString(libpath_flags))
    print('}')

  if not windows_sdk_paths:
    raise Exception("No usable Windows SDK found")

  if len(set(windows_sdk_paths.values())) != 1:
    raise Exception("Different WINDOWSSDKDIR values for different CPUs are unsupported")

  print('visual_studio_version = ' + gn_helpers.ToGNString(version_as_year))
  print('visual_studio_path = ' + gn_helpers.ToGNString(vs_path))

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
    # TODO(tim): Do we want to support different toolchain versions for
    # different architectures?
    msc_full_ver = _ParseClVersion(_ProcessSpawnResult(_Spawn(['cl'], env=envs['x86'])))
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
