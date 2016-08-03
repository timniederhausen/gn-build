#!/usr/bin/env python
import subprocess
import sys

def GetEnv(arch):
  """Gets the saved environment from a file for a given architecture."""
  # The environment is saved as an "environment block" (see CreateProcess
  # and msvs_emulation for details). We convert to a dict here.
  # Drop last 2 NULs, one for list terminator, one for trailing vs. separator.
  pairs = open(arch).read()[:-2].split('\0')
  kvs = [item.split('=', 1) for item in pairs]
  return dict(kvs)

def main(arch, *args):
  """Filter logo banner from invocations of asm.exe."""
  env = GetEnv(arch)
  popen = subprocess.Popen(args, shell=True, env=env, universal_newlines=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  out, _ = popen.communicate()
  for line in out.splitlines():
    if (not line.startswith('Copyright (C) Microsoft Corporation') and
        not line.startswith('Microsoft (R) Macro Assembler') and
        not line.startswith(' Assembling: ') and
        line):
      print(line)
  return popen.returncode

if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
