#!/bin/bash
set -e

export TARGET=x86_64-linux-android
export TARGET_JDK=x86_64

exec bash 2_ci_build_global.sh
