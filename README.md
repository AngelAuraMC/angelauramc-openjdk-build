# angelauramc-openjdk-build 

**This branch is for OpenJDK 17 and 21.**

Based on [Java for Android](http://openjdk.java.net/projects/mobile/android.html) and [the PojavLauncher variant](https://github.com/PojavLauncherTeam/android-openjdk-build-multiarch)

## Building 

### Setup
#### Android
**Note:** We use Ubuntu 24.04 LTS to build our JDKs. Adapt these dependencies to your distribution, it should build fine.
- Install `autoconf`, `python3`, `python-is-python3`, `unzip`, `zip`, `systemtap-sdt-dev`, `libxtst-dev`, `libasound2-dev`, `libelf-dev`, `libfontconfig1-dev`, `libx11-dev`, `libxext-dev`, `libxrandr-dev`, `libxrender-dev`, `libxtst-dev`, `libxt-dev`.
- If building JDK 17, install `openjdk-17-jdk`. For 21, `openjdk-21-jdk`.
- Install Android NDK r27b.

#### iOS
- Install latest Xcode on your Mac.
- If building JDK 17, install JDK 17. For 21, install JDK 21.

### Platform and architecture specific environment variables
<table>
      <thead>
        <tr>
          <th></th>
          <th align="center" colspan="7">Environment variables</th>
        </tr>
        <tr>
          <th>Platform - Architecture</th>
          <th align="center">TARGET</th>
          <th align="center">TARGET_JDK</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Android - armv8/aarch64</td>
          <td align="center">aarch64-linux-android</td>
          <td align="center">aarch64</td>
        </tr>
        <tr>
          <td>Android - armv7/aarch32</td>
          <td align="center">arm-linux-androideabi</td>
          <td align="center">arm</td>
        </tr>
        <tr>
          <td>Android - x86/i686</td>
          <td align="center">i686-linux-android</td>
          <td align="center">x86</td>
        </tr>
        <tr>
          <td>Android - x86_64/amd64</td>
          <td align="center">x86_64-linux-android</td>
          <td align="center">x86_64</td>
        </tr>
        <tr>
          <td>iOS/iPadOS - armv8/aarch64</td>
          <td align="center">aarch64-macos-ios</td>
          <td align="center">aarch64</td>
        </tr>
      </tbody>
	</table>

### Run in this directory:
```
export BUILD_IOS=1 # only when targeting iOS, default is 0 (target Android)

export BUILD_FREETYPE_VERSION=[2.6.2/.../2.10.4] # default: 2.10.4
export JDK_DEBUG_LEVEL=[release/fastdebug/debug] # default: release
export JVM_VARIANTS=[client/server] # default: client (aarch32), server (other architectures)

# Setup NDK, run once (Android only)
./extractndk.sh
./maketoolchain.sh 

# Get CUPS, Freetype and build Freetype
./getlibs.sh
./buildlibs.sh

# Clone JDK, run once
./clonejdk.sh

# Configure JDK and build, if no configuration is changed, run makejdkwithoutconfigure.sh instead
./buildjdk.sh

# Pack the built JDK
./removejdkdebuginfo.sh
./tarjdk.sh
```

