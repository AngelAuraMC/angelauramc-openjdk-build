#!/bin/bash
set -e

if [[ $TARGET_VERSION -eq 21 ]]; then
    git clone --depth 1 https://github.com/openjdk/jdk21u openjdk-21
else
    git clone --depth 1 https://github.com/openjdk/jdk17u openjdk-17
fi