#!/bin/bash
# duplicate of buildjdk.sh that avoids reconfiguring. Used for making changes to openjdk code.

set -e
. setdevkitpath.sh
export FREETYPE_DIR=`pwd`/freetype-${BUILD_FREETYPE_VERSION}/build_android-${TARGET_SHORT}
export CUPS_DIR=`pwd`/cups-2.2.4

cd openjdk-${TARGET_VERSION}/build/${JVM_PLATFORM}-${TARGET_JDK}-${JVM_VARIANTS}-${JDK_DEBUG_LEVEL}
make JOBS=4 images
