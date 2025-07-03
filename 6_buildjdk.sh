#!/bin/bash
set -e
. setdevkitpath.sh

export FREETYPE_DIR=$PWD/freetype-$BUILD_FREETYPE_VERSION/build_android-$TARGET_SHORT
export CUPS_DIR=$PWD/cups-2.2.4
export CFLAGS+=" -DLE_STANDALONE" # -I$FREETYPE_DIR -I$CUPS_DI
if [[ "$TARGET_JDK" == "arm" ]] # || [[ "$BUILD_IOS" == "1" ]]
then
  export CFLAGS+=" -O3 -D__thumb__"
else
  if [[ "$TARGET_JDK" == "x86" ]]; then
     export CFLAGS+=" -O3 -mstackrealign"
  else
     export CFLAGS+=" -O3"
  fi
fi

# if [[ "$TARGET_JDK" == "aarch32" ]] || [[ "$TARGET_JDK" == "aarch64" ]]
# then
#   export CFLAGS+=" -march=armv7-a+neon"
# fi

# It isn't good, but need make it build anyways
# cp -R $CUPS_DIR/* $ANDROID_INCLUDE/

# cp -R /usr/include/X11 $ANDROID_INCLUDE/
# cp -R /usr/include/fontconfig $ANDROID_INCLUDE/

if [[ "$BUILD_IOS" != "1" ]]; then
  chmod +x android-wrapped-clang
  chmod +x android-wrapped-clang++
  ln -s -f /usr/include/X11 $ANDROID_INCLUDE/
  ln -s -f /usr/include/fontconfig $ANDROID_INCLUDE/
  platform_args="--with-toolchain-type=gcc \
    --with-freetype-include=$FREETYPE_DIR/include/freetype2 \
    --with-freetype-lib=$FREETYPE_DIR/lib \
    "

  if [[ $TARGET_VERSION -eq 21 ]]; then
    platform_args+="--build=x86_64-unknown-linux-gnu \
    "
  fi

  platform_args+="OBJCOPY=${OBJCOPY} \
    RANLIB=${RANLIB} \
    AR=${AR} \
    STRIP=${STRIP} \
    "

  AUTOCONF_x11arg="--x-includes=$ANDROID_INCLUDE/X11"

  export CFLAGS+=" -mllvm -polly -DANDROID -Wno-error=implicit-function-declaration -Wno-error=int-conversion"
  export LDFLAGS+=" -L$PWD/dummy_libs -Wl,--undefined-version"

# Create dummy libraries so we won't have to remove them in OpenJDK makefiles
  mkdir -p dummy_libs
  ar cru dummy_libs/libpthread.a
  ar cru dummy_libs/librt.a
  ar cru dummy_libs/libthread_db.a
else
  ln -s -f /opt/X11/include/X11 $ANDROID_INCLUDE/
  ln -sfn $themacsysroot/System/Library/Frameworks/CoreAudio.framework/Headers $ANDROID_INCLUDE/CoreAudio
  ln -sfn $themacsysroot/System/Library/Frameworks/IOKit.framework/Headers $ANDROID_INCLUDE/IOKit
  if [[ "$(uname -p)" == "arm" ]]; then
    ln -s -f /opt/homebrew/include/fontconfig $ANDROID_INCLUDE/
  else
    ln -s -f /usr/local/include/fontconfig $ANDROID_INCLUDE/
  fi
  platform_args="--with-toolchain-type=clang --with-sysroot=$(xcrun --sdk iphoneos --show-sdk-path) \
    --with-boot-jdk=$(/usr/libexec/java_home -v $TARGET_VERSION) \
    --with-freetype=bundled \
    "
  AUTOCONF_x11arg="--with-x=/opt/X11/include/X11 --prefix=/usr/lib"
  sameflags="-arch arm64 -DHEADLESS=1 -I$PWD/ios-missing-include -Wno-implicit-function-declaration"
  export CFLAGS+=" $sameflags"
  export LDFLAGS+="-arch arm64"
  export BUILD_SYSROOT_CFLAGS="-isysroot ${themacsysroot}"

  if [[ "$J316SAP" != "1" ]]; then
    HOMEBREW_NO_AUTO_UPDATE=1 brew install fontconfig ldid xquartz autoconf
  fi 
fi

# fix building libjawt
ln -s -f $CUPS_DIR/cups $ANDROID_INCLUDE/

cd openjdk-${TARGET_VERSION}

# Apply patches
git add .
git reset --hard
if [[ "$BUILD_IOS" != "1" ]]; then
  find ../patches/jre_${TARGET_VERSION}/android -name "*.diff" -print0 | xargs -0 -I {} sh -c 'echo "Applying {}" && git apply  --reject --whitespace=fix {} || (echo "git apply failed (Android patch set)" && exit 1)' 
else
  find ../patches/jre_${TARGET_VERSION}/ios -name "*.diff" -print0 | sort -z | xargs -0 -I {} sh -c 'echo "Applying {}" && git apply --reject --whitespace=fix {} || (echo "git apply failed (iOs patch set)" && exit 1)' 

  # Hack: exclude building macOS stuff
  desktop_mac=src/java.desktop/macosx
  mv ${desktop_mac} ${desktop_mac}_NOTIOS
  mkdir -p ${desktop_mac}/native
  mv ${desktop_mac}_NOTIOS/native/libjsound ${desktop_mac}/native/
fi

# rm -rf build

#   --with-extra-cxxflags="$CXXFLAGS -Dchar16_t=uint16_t -Dchar32_t=uint32_t" \
#   --with-extra-cflags="$CPPFLAGS" \

bash ./configure \
    --openjdk-target=$TARGET \
    --with-extra-cflags="$CFLAGS" \
    --with-extra-cxxflags="$CFLAGS" \
    --with-extra-ldflags="$LDFLAGS" \
    --disable-precompiled-headers \
    --disable-warnings-as-errors \
    --enable-option-checking=fatal \
    --enable-headless-only=yes \
    --with-jvm-variants=$JVM_VARIANTS \
    --with-jvm-features=-dtrace,-zero,-vm-structs,-epsilongc \
    --with-cups-include=$CUPS_DIR \
    --with-devkit=$TOOLCHAIN \
    --with-native-debug-symbols=external \
    --with-debug-level=$JDK_DEBUG_LEVEL \
    --with-fontconfig-include=$ANDROID_INCLUDE \
    $AUTOCONF_x11arg $AUTOCONF_EXTRA_ARGS \
    --x-libraries=/usr/lib \
        $platform_args || \
error_code=$?
if [[ "$error_code" -ne 0 ]]; then
  echo "\n\nCONFIGURE ERROR $error_code , config.log:"
  cat config.log
  exit $error_code
fi

jobs=4

if [[ "$BUILD_IOS" == "1" ]]; then
  jobs=$(sysctl -n hw.ncpu)
else
  jobs=$(nproc)
fi

# Failsafe environment variable for computers with too many cores
# i.e. Cart's 7K62
if [[ "$TOO_MANY_CORES" == "1" ]]; then
  jobs=6
fi

echo Running ${jobs} jobs to build the jdk

cd build/${JVM_PLATFORM}-${TARGET_JDK}-${JVM_VARIANTS}-${JDK_DEBUG_LEVEL}
make JOBS=$jobs images || \
error_code=$?
if [[ "$error_code" -ne 0 ]]; then
  echo "Build failure, exited with code $error_code. Trying again."
  make JOBS=$jobs images
fi
