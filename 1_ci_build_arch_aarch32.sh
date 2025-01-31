#!/bin/bash
set -e

export TARGET=armv7a-linux-androideabi
export TARGET_JDK=arm
export JVM_VARIANTS=client

bash 2_ci_build_global.sh
