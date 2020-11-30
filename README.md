# //build directory for GN-based projects

This project provides a work-in-progress standalone version of the toolchains and configs used by the Chromium project.

## Supported platforms

The toolchains have been tested on the following platforms:

* Windows (MSVC 2013/2015/2017/2019, Clang 3.8)
* FreeBSD (GCC 6, Clang 11)
* Linux (GCC 6, Clang 3.8)
* OS X (Xcode 7.3.1)

[![Build Status](https://travis-ci.org/timniederhausen/gn-build.svg?branch=master)](https://travis-ci.org/timniederhausen/gn-build)
[![Build status](https://ci.appveyor.com/api/projects/status/jpot0c7wp6e78lkk/branch/master?svg=true)](https://ci.appveyor.com/project/timniederhausen/gn-build)

The [testsrc](https://github.com/timniederhausen/gn-build/tree/testsrc)
branch contains the test/example project used by the CI tests.

## Reference

### Basic variables

All variables described here are build args and can be overridden in the user's
`args.gn` file.

#### [`//build/config/BUILDCONFIG.gn`](config/BUILDCONFIG.gn)

(these variables are available everywhere)

* `is_debug` (default: true): Toggle between debug and release builds.
* `is_clang` (default: false): Favor Clang over the platform default (GCC/MSVC).
* `is_official_build` (default: !is_debug): Set to enable the official build
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

* `visual_studio_version` (default: "latest"): Desired version of Visual Studio.
  If `visual_studio_path` is set, this must be the version of the VS installation
  at the `visual_studio_path`.

  Use "2013" for Visual Studio 2013 or "latest" for automatically choosing the
  highest version (`visual_studio_path` must be unset in this case).
* `visual_studio_path` (default: auto-detected): The path of your MSVC installation.
  If this is set you must set visual_studio_version as well.
  Autodetected based on `visual_studio_version`.
* `windows_sdk_version` (default: auto-detected): Windows SDK version to use.
  Can either be a full Windows 10 SDK number (e.g. 10.0.10240.0),
  "8.1" for the Windows 8.1 SDK or "default" for the default SDK selected by VS.
* `clang_msc_ver` (default: auto-detected): MSVC version `clang-cl` will report
  in `_MSC_VER`.

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

### Mac/iOS toolchain

#### [`//build/toolchain/mac/settings.gni`](toolchain/mac/settings.gni)

* `use_system_xcode` (default: true): Use the system install of Xcode for tools
  like ibtool, libtool, etc. This does not affect the compiler. When this
  variable is false, targets will instead use a hermetic install of Xcode.
* `hermetic_xcode_path` (default: ""): The path to the hermetic install of
  Xcode. Only relevant when use_system_xcode = false.
* `use_xcode_clang` (default: true): Compile with Xcode version of clang
  instead of hermetic version shipped with the build. If `true`,
  `clang_base_path` needs to be set.
* `enable_dsyms` (default: true): Produce dSYM files for targets that are
  configured to do so. dSYM generation is controlled globally as it is a
  linker output (produced via the `//build/toolchain/mac/linker_driver.py`.
  Enabling this will result in all shared library, loadable module, and
  executable targets having a dSYM generated.
* `enable_stripping` (default: `is_official_build`): Strip symbols from linked
  targets by default. If this is enabled, the //build/config/mac:strip_all
  config will be applied to all linked targets. If custom stripping parameters
  are required, remove that config from a linked target and apply custom
  `-Wcrl,strip` flags. See //build/toolchain/mac/linker_driver.py for more
  information.

#### [`//build/toolchain/mac/mac_sdk.gni`](toolchain/mac/mac_sdk.gni)

* `mac_sdk_min` (default: "10.10"): Minimum supported version of the Mac SDK.
* `mac_deployment_target` (default: "10.9"): Minimum supported version of OSX.
* `mac_sdk_path` (default: ""): Path to a specific version of the Mac SDK, not
  including a slash at the end. If empty, the path to the lowest version
  greater than or equal to `mac_sdk_min` is used.
* `mac_sdk_name` (default: "macosx"): The SDK name as accepted by xcodebuild.

#### [`//build/toolchain/mac/ios_sdk.gni`](toolchain/mac/ios_sdk.gni)

* `ios_sdk_path` (default: ""): Path to a specific version of the iOS SDK, not
  including a slash at the end. When empty this will use the default SDK based
  on the value of use_ios_simulator.

  SDK properties (required when `ios_sdk_path` is non-empty):

  * `ios_sdk_name`: The SDK name as accepted by xcodebuild.
  * `ios_sdk_version`
  * `ios_sdk_platform`
  * `ios_sdk_platform_path`
  * `xcode_version`
  * `xcode_build`
  * `machine_os_build`

* `ios_deployment_target` (default: "9.0"): Minimum supported version of OSX.

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

Fork this repo and add it as a submodule/subtree/`DEPS`-entry to your project.
This way you can modify every part of the `//build` directory while still being
able to easily merge upstream changes (e.g. support for new GN features that
you don't want to implement yourself.)

To ease sharing/composition of projects using this `//build` repo,
it is recommended that you refrain from modifying large parts of the toolchains/configs.
If changes are necessary, consider contributing them back ;)

For more complex projects, it might be feasible to use a custom build-config file
that just `import()s` [`//build/config/BUILDCONFIG.gn`](config/BUILDCONFIG.gn) and then overrides
the defaults set inside `BUILDCONFIG.gn`. There's also GN's `default_args` scope, which can be used
to provide project-specific argument overrides.
