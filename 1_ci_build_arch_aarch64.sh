#!/bin/bash
set -e

if [[ "$BUILD_IOS" == "1" ]]; then
  export TARGET=aarch64-apple-ios
else
  export TARGET=aarch64-linux-android
fi
export TARGET_JDK=aarch64

exec bash 2_ci_build_global.sh
