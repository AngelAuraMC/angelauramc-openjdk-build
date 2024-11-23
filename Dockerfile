FROM ubuntu:22.04

RUN apt-get update



# Install dependencies
RUN apt-get install -y wget

# Cmake repositories to have an up to date version
RUN wget -qO - https://apt.kitware.com/kitware-archive.sh | bash 

# Raw tools
RUN apt-get install -y \
    autoconf \
    python3 \
    python-is-python3 \
    python3-distutils \
    unzip \
    zip \
    systemtap-sdt-dev \
    libxtst-dev \
    libasound2-dev \
    libelf-dev \
    libfontconfig1-dev \
    libx11-dev \
    libxext-dev \
    libxrandr-dev \
    libxrender-dev \
    libxtst-dev \
    libxt-dev \
    gcc \
    g++ \
    clang \
    git \
    file \
    make \
    cmake \
    xz-utils

# JDK 17
RUN apt-get install -y openjdk-17-jdk
RUN apt-get install -y openjdk-21-jdk

WORKDIR /home


# NDK install
ENV NDK_VERSION r27b
ENV ANDROID_NDK_HOME /home/android-ndk-$NDK_VERSION
RUN \
    wget -nc -nv -O android-ndk-$NDK_VERSION-linux-x86_64.zip "https://dl.google.com/android/repository/android-ndk-$NDK_VERSION-linux.zip" \
    && unzip -q android-ndk-$NDK_VERSION-linux-x86_64.zip \
    && rm android-ndk-$NDK_VERSION-linux-x86_64.zip


COPY . .