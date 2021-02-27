#!/usr/bin/env python
import os
import subprocess
import sys
from toolchain import GetEnv


def main(arch, outdir, tlb, h, dlldata, iid, proxy, idl, *flags):
  """Filter noisy filenames output from MIDL compile step that isn't
  quietable via command line flags.
  """
  args = ['midl', '/nologo'] + list(flags) + [
      '/out', outdir,
      '/tlb', tlb,
      '/h', h,
      '/dlldata', dlldata,
      '/iid', iid,
      '/proxy', proxy,
      idl]
  env = GetEnv(arch)
  popen = subprocess.Popen(args, shell=True, env=env, universal_newlines=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  out, _ = popen.communicate()
  # Filter junk out of stdout, and write filtered versions. Output we want
  # to filter is pairs of lines that look like this:
  # Processing C:\Program Files (x86)\Microsoft SDKs\...\include\objidl.idl
  # objidl.idl
  lines = out.splitlines()
  prefixes = ('Processing ', '64 bit Processing ')
  processing = set(os.path.basename(x)
                   for x in lines if x.startswith(prefixes))
  for line in lines:
    if not line.startswith(prefixes) and line not in processing:
      print(line)
  return popen.returncode

if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
