#!/usr/bin/env python
import os
import re
import subprocess
import sys

# A regex matching an argument corresponding to the output filename passed to
# link.exe.
_LINK_EXE_OUT_ARG = re.compile('/OUT:(?P<out>.+)$', re.IGNORECASE)

def GetEnv(arch):
  """Gets the saved environment from a file for a given architecture."""
  # The environment is saved as an "environment block" (see CreateProcess
  # and msvs_emulation for details). We convert to a dict here.
  # Drop last 2 NULs, one for list terminator, one for trailing vs. separator.
  pairs = open(arch).read()[:-2].split('\0')
  kvs = [item.split('=', 1) for item in pairs]
  return dict(kvs)

def UseSeparateMspdbsrv(env, args):
  """Allows to use a unique instance of mspdbsrv.exe per linker instead of a
  shared one."""
  if len(args) < 1:
    raise Exception("Not enough arguments")

  if args[0] != 'link.exe':
    return

  # Use the output filename passed to the linker to generate an endpoint name
  # for mspdbsrv.exe.
  endpoint_name = None
  for arg in args:
    m = _LINK_EXE_OUT_ARG.match(arg)
    if m:
      endpoint_name = re.sub(r'\W+', '',
          '%s_%d' % (m.group('out'), os.getpid()))
      break

  if endpoint_name is None:
    return

  # Adds the appropriate environment variable. This will be read by link.exe
  # to know which instance of mspdbsrv.exe it should connect to (if it's
  # not set then the default endpoint is used).
  env['_MSPDBSRV_ENDPOINT_'] = endpoint_name

def main(arch, use_separate_mspdbsrv, *args):
  """Filter diagnostic output from link that looks like:
  '   Creating library ui.dll.lib and object ui.dll.exp'
  This happens when there are exports from the dll or exe.
  """
  env = GetEnv(arch)
  if use_separate_mspdbsrv == 'True':
    UseSeparateMspdbsrv(env, args)
  link = subprocess.Popen([args[0].replace('/', '\\')] + list(args[1:]),
                          shell=True,
                          env=env,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          universal_newlines=True)
  out, _ = link.communicate()
  for line in out.splitlines():
    if not line.startswith('   Creating library '):
      print(line)
  return link.returncode

if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
