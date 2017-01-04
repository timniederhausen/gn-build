#!/usr/bin/env python
from __future__ import print_function

import re
import subprocess
import sys
import os

def _get_compiler_version(path, major_define, minor_define, patchlevel_define):
  path = os.path.normpath(path)
  defines = subprocess.check_output('echo "" | "{}" -dM -E -'.format(path), shell=True,
                                    universal_newlines=True).split('\n')
  version = 0
  for define in defines:
    define = re.findall(r'#define ([a-zA-Z0-9_]+) (.*)', define)
    if not define:
      continue

    name, value = define[0]
    if name == major_define:
      version += 10000 * int(value)
    elif name == minor_define:
      version += 100 * int(value)
    elif name == patchlevel_define:
      value = int(value)
      if value < 100:
        version += int(value)

  return version


def get_gcc_version(path):
  print(_get_compiler_version(path, '__GNUC__', '__GNUC_MINOR__', '__GNUC_PATCHLEVEL__'))


def get_clang_version(path):
  print(_get_compiler_version(path, '__clang_major__', '__clang_minor__', '__clang_patchlevel__'))


def main():
  commands = {
      'get_gcc_version': get_gcc_version,
      'get_clang_version': get_clang_version,
  }

  if len(sys.argv) < 2 or sys.argv[1] not in commands:
    print('Expected one of: %s' % ', '.join(commands), file=sys.stderr)
    return 1

  return commands[sys.argv[1]](*sys.argv[2:])


if __name__ == '__main__':
  sys.exit(main())
