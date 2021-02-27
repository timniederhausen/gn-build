#!/usr/bin/env python
import subprocess
import sys
from toolchain import GetEnv


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
