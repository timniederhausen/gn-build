# //build directory for GN-based projects

This project provides a work-in-progress standalone version of the toolchains and configs used by the Chromium project.

## Supported platforms

The toolchains have been tested on the following platforms:

* Windows (MSVC 2013/2015, Clang 3.8)
* FreeBSD (GCC 5, Clang 3.7)
* Linux (GCC 4.9, Clang 3.8)

[![Build Status](https://travis-ci.org/timniederhausen/gn-build.svg?branch=master)](https://travis-ci.org/timniederhausen/gn-build)
[![Build status](https://ci.appveyor.com/api/projects/status/jpot0c7wp6e78lkk?svg=true)](https://ci.appveyor.com/project/timniederhausen/gn-build)

The [testsrc](https://github.com/timniederhausen/gn-build/tree/testsrc)
branch contains the test/example project used by the CI tests.

## Reference

### Basic variables

All variables described here are build args and can be overridden in the user's
`args.gn` file.

#### [`//build/config/BUILDCONFIG.gn`](config/BUILDCONFIG.gn)

(these variables are available everywhere)

* `is_debug` (default: true): Enable/disable debugging options.
* `is_clang` (default: false): Favor Clang over the platform default (GCC/MSVC).
* `is_official_build` (default: !`is_debug`): Set to enable the official build
  level of optimization. This enables an additional level of optimization above
  release (!is_debug).
* `external` (default: "//external"): Label of the external projects directory.
  By convention, all 3rd-party projects should end up in this directory, so they
  can depend on each other (e.g. $external/mysql_connector -> $external/zlib)

#### [`//build/toolchain/clang.gni`](toolchain/clang.gni)

* `use_lld` (default: false): Use the new LLD linker.
  This requires `is_clang` to be true.
* `clang_base_path` (default: ""): The path of your Clang installation folder
  (without /bin). If you use Clang on Windows, you are required to set this,
  as the Clang installation isn't automatically detected.

#### [`//build/toolchain/compiler_version.gni`](toolchain/compiler_version.gni)

* `gcc_version` (default: auto-detected): Version of the GCC compiler.
  **Note:** Auto-detection is toolchain-specific and happens only if GCC is the
  active compiler. <br>
  Format: `major` * 10000 + `minor` * 100 + `patchlevel`
* `clang_version` (default: auto-detected): Version of the Clang compiler.
  **Note:** Auto-detection is toolchain-specific and happens only if Clang is
  the active compiler. <br>
  Format: `major` * 10000 + `minor` * 100 + `patchlevel`
* `msc_ver` (default: auto-detected): Value of the _MSC_VER variable.
  See https://msdn.microsoft.com/en-us/library/b0084kay.aspx.
  **Note:** Auto-detection happens only when targeting Windows.
* `msc_full_ver` (default: auto-detected): Value of the _MSC_FULL_VER variable.
  See https://msdn.microsoft.com/en-us/library/b0084kay.aspx.
  **Note:** Auto-detection happens only when targeting Windows.

### Windows toolchain

#### [`//build/toolchain/win/settings.gni`](toolchain/win/settings.gni)

* `visual_studio_version` (default: 2013): The MSVC version to use.
* `visual_studio_path` (default: auto-detected): The path of your MSVC installation.
  Autodetected based on `visual_studio_version`.
* `windows_sdk_path` (default: auto-detected):
  Path of your Windows SDK installation.

### POSIX toolchain

This is the default toolchain for POSIX operating systems,
which is used for all POSIX systems that don't have special toolchains.

#### [`//build/toolchain/posix/settings.gni`](toolchain/posix/settings.gni)

* `gcc_cc` (default: gcc): Path of the GCC C compiler executable.
  Does not have to be absolute.
* `gcc_cxx` (default: g++): Path of the GCC C++ compiler executable.
  Does not have to be absolute.
* `clang_cc` (default: clang): Path of the Clang C compiler executable.
  Does not have to be absolute. **Note:** If `clang_base_path` is set,
  the default will be `clang_base_path/bin/clang`.
* `clang_cxx` (default: clang++): Path of the Clang C++ compiler executable.
  Does not have to be absolute. **Note:** If `clang_base_path` is set,
  the default will be `clang_base_path/bin/clang++`.

### Mac toolchain

TODO: Mac builds are currently unsupported.

### Android toolchain

#### [`//build/toolchain/android/settings.gni`](toolchain/android/settings.gni)

* `android_ndk_root` (default: "$external/android_tools/ndk"):
  Path of the Android NDK.
* `android_ndk_version` (default: "r12b"): NDK Version string.
* `android_ndk_major_version` (default: 12): NDK Major version.
* `android_sdk_root` (default: "$external/android_tools/sdk"):
  Path of the Android SDK.
* `android_sdk_version` (default: "24"): Android SDK version.
* `android_sdk_build_tools_version` (default: "24.0.2"):
  Version of the Build Tools contained in the SDK.
* `android_libcpp_lib_dir` (default: ""): Libc++ library directory.
  Override to use a custom libc++ binary.
* `use_order_profiling` (default: false): Adds intrumentation to each function.
  Writes a file with the order that functions are called at startup.

## Recommended workflow

Fork this repo and add it as a submodule/`DEPS`-entry to your project.
This way you can modify every part of the `//build` directory while still being
able to easily merge upstream changes (e.g. support for new GN features that
you don't want to implement yourself.)
