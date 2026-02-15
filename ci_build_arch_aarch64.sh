#!/bin/bash
set -e

if [[ "$BUILD_IOS" == "1" ]]; then
  export TARGET=aarch64-apple-darwin18.2
else
  export TARGET=aarch64-linux-android
fi
export TARGET_JDK=aarch64
export NDK_PREBUILT_ARCH=/toolchains/aarch64-linux-android-4.9/prebuilt/linux-x86_64/aarch64-linux-android/bin/strip

exec bash ci_build_global.sh
