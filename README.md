# //build directory for GN-based projects

This project provides a work-in-progress standalone version of the toolchains and configs used by the Chromium project.

## Supported platforms

The toolchains have been tested on the following platforms:

* Windows (MSVC 2013/2015/Clang 3.8)
* FreeBSD (GCC 5 / Clang 3.7)
* Linux (GCC 5 / Clang 3.7)

## Reference

### Basic variables:

* `is_debug` (default: true): Enable/disable debugging options.
* `is_clang` (default: false): Favor Clang over the platform default (GCC/MSVC).

### Windows toolchain

* `visual_studio_version` (default: 2013): The MSVC version to use.
* `visual_studio_path` (default: auto-detected): The path of your MSVC installation.
  Autodetected based on `visual_studio_version`.
* `windows_sdk_path` (default: C:\\Program Files (x86)\\Microsoft SDKs\\Windows\\v7.1A):
  Path of your Windows SDK installation.
* `win_clang_prefix` (default: ""): If `is_clang` is true, this is required to point to
  the directory containing the `clang-cl` executable.

### POSIX toolchain

* `gcc_cc` (default: gcc): Path of the GCC C compiler executable. Does not have to be absolute.
* `gcc_cxx` (default: g++): Path of the GCC C++ compiler executable. Does not have to be absolute.
* `gcc_version` (default: auto-detected): Version of the GCC compiler.
  Format: `major` * 10000 + `minor` * 100 + `patchlevel`
* `clang_cc` (default: gcc): Path of the Clang C compiler executable. Does not have to be absolute.
* `clang_cxx` (default: g++): Path of the Clang C++ compiler executable. Does not have to be absolute.
* `clang_version` (default: auto-detected): Version of the Clang compiler.
  Format: `major` * 10000 + `minor` * 100 + `patchlevel`

### Mac toolchain

TODO: Mac builds are currently unsupported.
