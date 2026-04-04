#!/bin/bash
set -e

export TARGET=arm-linux-androideabi
export TARGET_JDK=arm
export NDK_PREBUILT_ARCH=/toolchains/arm-linux-androideabi-4.9/prebuilt/linux-x86_64/arm-linux-androideabi/bin/strip

exec bash ci_build_global.sh
