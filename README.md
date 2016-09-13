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
* `use_lld` (default: false): Use the new LLD linker.
  This requires `is_clang` to be true.
* `clang_base_path` (default: ""): The path of your Clang installation folder
  (without /bin). If you use Clang on Windows, you are required to set this,
  as the Clang installation isn't automatically detected.

### Windows toolchain

* `visual_studio_version` (default: 2013): The MSVC version to use.
* `visual_studio_path` (default: auto-detected): The path of your MSVC installation.
  Autodetected based on `visual_studio_version`.
* `windows_sdk_path` (default: auto-detected):
  Path of your Windows SDK installation.

### POSIX toolchain

* `gcc_cc` (default: gcc): Path of the GCC C compiler executable.
  Does not have to be absolute.
* `gcc_cxx` (default: g++): Path of the GCC C++ compiler executable.
  Does not have to be absolute.
* `gcc_version` (default: auto-detected): Version of the GCC compiler.
  Format: `major` * 10000 + `minor` * 100 + `patchlevel`
* `clang_cc` (default: gcc): Path of the Clang C compiler executable.
  Does not have to be absolute.
* `clang_cxx` (default: g++): Path of the Clang C++ compiler executable.
  Does not have to be absolute.
* `clang_version` (default: auto-detected): Version of the Clang compiler.
  Format: `major` * 10000 + `minor` * 100 + `patchlevel`

### Mac toolchain

TODO: Mac builds are currently unsupported.

## Recommended workflow

Fork this repo and add it as a submodule/`DEPS`-entry to your project.
This way you can modify every part of the `//build` directory while still being
able to easily merge upstream changes (e.g. support for new GN features that
you don't want to implement yourself.)
