#!/usr/bin/env python
import sys
import os

def main(manifest_path, resource_path, resource_name):
  """Creates a resource file pointing a SxS assembly manifest.
  |args| is tuple containing path to resource file, path to manifest file
  and resource name which can be "1" (for executables) or "2" (for DLLs)."""
  with open(resource_path, 'wb') as output:
    line = '#include <windows.h>\n%s RT_MANIFEST "%s"' % (
      resource_name,
      os.path.abspath(manifest_path).replace('\\', '/'))
    output.write(line.encode('utf-8'))

  return 0

if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
