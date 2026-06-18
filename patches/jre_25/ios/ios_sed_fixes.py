#!/usr/bin/env python3
"""Hard sed-style fixes for iOS JDK 25 build.

Runs after jdk25_ios_fixups.py and the fuzz-fallback pass. Handles cases
where the Python fixup's old text didn't match exactly due to whitespace
or version differences. All fixes are idempotent.

Usage: python3 ios_sed_fixes.py [/path/to/openjdk-25]
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '.')


def show(path, pattern):
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if re.search(pattern, line):
            print(f'  {i}: {line}')


# Fix 1: _load_reported bitfield
# mirror_w_set takes address of _load_reported which is still a :1 bitfield.
# C++ forbids taking the address of a bitfield so the build fails with
# "address of bit-field requested". Rewrite to go through mirror_w(this).
p = ROOT / 'src/hotspot/share/code/nmethod.hpp'
if p.exists():
    s = p.read_text()
    s2 = s.replace(
        'mirror_w_set(_load_reported) = true',
        'mirror_w(this)->_load_reported = true'
    )
    if s2 != s:
        p.write_text(s2)
        print('[ios_sed_fixes] fix1: patched nmethod.hpp _load_reported')
    else:
        print('[ios_sed_fixes] fix1: nmethod.hpp already patched or pattern not found')
else:
    print('[ios_sed_fixes] fix1: WARN nmethod.hpp not found')


# Fix 2: memMapPrinter_macosx.cpp includes mach_vm.h which is explicitly
# unsupported on the iOS SDK. Wrap the entire file in !TARGET_OS_IPHONE
# and provide an empty stub so the NMT linker symbol resolves.
p = ROOT / 'src/hotspot/os/bsd/memMapPrinter_macosx.cpp'
if p.exists():
    s = p.read_text()
    if 'TARGET_OS_IPHONE' not in s:
        patched = (
            '#include <TargetConditionals.h>\n'
            '#if !TARGET_OS_IPHONE\n'
            + s +
            '#endif\n'
            '#if TARGET_OS_IPHONE\n'
            '#include "nmt/memMapPrinter.hpp"\n'
            'void MemMapPrinter::pd_print_all_mappings(const MappingPrintSession&) {}\n'
            '#endif\n'
        )
        p.write_text(patched)
        print('[ios_sed_fixes] fix2: patched memMapPrinter_macosx.cpp')
    else:
        print('[ios_sed_fixes] fix2: memMapPrinter_macosx.cpp already patched')
else:
    print('[ios_sed_fixes] fix2: WARN memMapPrinter_macosx.cpp not found')


# Fix 3: flags-ldflags.m4 sets -mmacosx-version-min which conflicts with
# -miphoneos-version-min at link time. Comment it out.
p = ROOT / 'make/autoconf/flags-ldflags.m4'
if p.exists():
    s = p.read_text()
    s2 = re.sub(
        r'(\s+)(OS_LDFLAGS="-mmacosx-version-min=)',
        r'\1#OS_LDFLAGS="-mmacosx-version-min=',
        s
    )
    if s2 != s:
        p.write_text(s2)
        print('[ios_sed_fixes] fix3: patched flags-ldflags.m4')
    else:
        print('[ios_sed_fixes] fix3: flags-ldflags.m4 already patched or pattern not found')
else:
    print('[ios_sed_fixes] fix3: WARN flags-ldflags.m4 not found')


# Fix 4: CoreLibraries.gmk links ApplicationServices and Cocoa which don't
# exist on iOS SDK. Replace every pair with Foundation. Also strip any
# remaining standalone ApplicationServices or Cocoa lines.
p = ROOT / 'make/modules/java.base/lib/CoreLibraries.gmk'
if p.exists():
    s = p.read_text()
    original = s
    s = re.sub(
        r'[ \t]*-framework ApplicationServices[ \t]*\\\n[ \t]*-framework Cocoa[ \t]*\\',
        '        -framework Foundation \\\\',
        s
    )
    s = re.sub(r'[ \t]*-framework ApplicationServices[ \t]*\\\n', '', s)
    s = re.sub(r'[ \t]*-framework Cocoa[ \t]*\\\n', '', s)
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix4: patched CoreLibraries.gmk')
        show(p, r'framework.*(Foundation|ApplicationServices|Cocoa)')
    else:
        print('[ios_sed_fixes] fix4: CoreLibraries.gmk already patched or pattern not found')
        show(p, r'ApplicationServices|Cocoa')
else:
    print('[ios_sed_fixes] fix4: WARN CoreLibraries.gmk not found')


# Fix 5: Lib.gmk libnet block is missing -framework CFNetwork. The symbols
# CFNetworkCopyProxiesForURL etc. live in CFNetwork, not CoreServices.
p = ROOT / 'make/modules/java.base/Lib.gmk'
if p.exists():
    s = p.read_text()
    if 'CFNetwork' not in s:
        original = s
        patterns = [
            ('        -framework CoreServices, \\\n',
             '        -framework CoreServices \\\n        -framework CFNetwork, \\\n'),
            ('    -framework CoreServices, \\\n',
             '    -framework CoreServices \\\n    -framework CFNetwork, \\\n'),
            ('-framework CoreServices, \\',
             '-framework CoreServices \\\n        -framework CFNetwork, \\'),
        ]
        for old, new in patterns:
            if old in s:
                s = s.replace(old, new)
                break
        if s != original:
            p.write_text(s)
            print('[ios_sed_fixes] fix5: patched Lib.gmk CFNetwork')
            show(p, r'CFNetwork|CoreServices')
        else:
            print('[ios_sed_fixes] fix5: WARN Lib.gmk CoreServices pattern not matched')
            print('[ios_sed_fixes] fix5: candidates:')
            for line in s.splitlines():
                if 'CoreServices' in line:
                    print(' ', repr(line))
    else:
        print('[ios_sed_fixes] fix5: Lib.gmk CFNetwork already present')
else:
    print('[ios_sed_fixes] fix5: WARN Lib.gmk not found')


# Fix 6: java.instrument/Lib.gmk - ApplicationServices + Cocoa don't exist
# on iOS. Replace with Foundation only.
p = ROOT / 'make/modules/java.instrument/Lib.gmk'
if p.exists():
    s = p.read_text()
    original = s
    s = re.sub(
        r'[ \t]*-framework ApplicationServices[ \t]*\\\n[ \t]*-framework Cocoa[ \t]*\\',
        '        -framework Foundation \\\\',
        s
    )
    s = re.sub(r'[ \t]*-framework ApplicationServices[ \t]*\\\n', '', s)
    s = re.sub(r'[ \t]*-framework Cocoa[ \t]*\\\n', '', s)
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix6: patched java.instrument/Lib.gmk')
        show(p, r'framework')
    else:
        print('[ios_sed_fixes] fix6: java.instrument/Lib.gmk already patched or no match')
        show(p, r'ApplicationServices|Cocoa')
else:
    print('[ios_sed_fixes] fix6: WARN java.instrument/Lib.gmk not found')


# Fix 7: AwtLibraries.gmk - guard BUILD_LIBJAWT with macosx_NOTIOS so iOS
# skips it entirely. The sources live in src/java.desktop/macosx which gets
# moved out so the build errors with "No sources found for BUILD_LIBJAWT".
p = ROOT / 'make/modules/java.desktop/lib/AwtLibraries.gmk'
if p.exists():
    s = p.read_text()
    if 'libjawt disabled for iOS' not in s:
        original = s
        old = '$(eval $(call SetupJdkLibrary, BUILD_LIBJAWT,'
        if old in s:
            idx = s.index(old)
            targets_marker = 'TARGETS += $(BUILD_LIBJAWT)'
            targets_idx = s.index(targets_marker, idx)
            end_idx = targets_idx + len(targets_marker)
            block = s[idx:end_idx]
            new_block = (
                '# libjawt disabled for iOS - sources moved to macosx_NOTIOS\n'
                'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n'
                + block + '\n'
                'endif'
            )
            s = s[:idx] + new_block + s[end_idx:]
            p.write_text(s)
            print('[ios_sed_fixes] fix7: patched AwtLibraries.gmk BUILD_LIBJAWT guard')
        else:
            print('[ios_sed_fixes] fix7: WARN BUILD_LIBJAWT block not found')
    else:
        print('[ios_sed_fixes] fix7: AwtLibraries.gmk already patched')
else:
    print('[ios_sed_fixes] fix7: WARN AwtLibraries.gmk not found')


# Fix 8: ClientLibraries.gmk - guard the ENTIRE libosxui block with
# macosx_NOTIOS. The outer ifeq (macosx) wraps both Metal shader compilation
# AND the SetupJdkLibrary call. The Metal shader step references
# src/java.desktop/macosx/native/... which gets moved out on iOS, so the
# entire block must be skipped, not just the library setup.
p = ROOT / 'make/modules/java.desktop/lib/ClientLibraries.gmk'
if p.exists():
    s = p.read_text()
    original = s
    # Change the outer macosx guard that wraps the entire libosxui block
    # (Metal shaders + SetupJdkLibrary + TARGETS line)
    old = 'ifeq ($(call isTargetOs, macosx), true)\n  ##############################################################################\n  ## Build libosxui'
    new = 'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n  ##############################################################################\n  ## Build libosxui'
    if old in s:
        s = s.replace(old, new)
        print('[ios_sed_fixes] fix8: patched ClientLibraries.gmk outer libosxui guard')
    else:
        # Try the actual format we saw in the patched tree
        old2 = 'ifeq ($(call isTargetOs, macosx), true)\n  ##############################################################################\n  ## Build libosxui\n  ##############################################################################'
        new2 = 'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n  ##############################################################################\n  ## Build libosxui\n  ##############################################################################'
        if old2 in s:
            s = s.replace(old2, new2)
            print('[ios_sed_fixes] fix8: patched ClientLibraries.gmk outer libosxui guard (v2)')
        else:
            # Regex fallback — match any macosx guard before Build libosxui
            s2 = re.sub(
                r'ifeq \(\$\(call isTargetOs, macosx\), true\)(\s*\n\s*#{10,}\s*\n\s*## Build libosxui)',
                r'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\1',
                s
            )
            if s2 != s:
                s = s2
                print('[ios_sed_fixes] fix8: patched ClientLibraries.gmk outer libosxui guard (regex)')
            else:
                print('[ios_sed_fixes] fix8: WARN outer libosxui guard not found')
                for i, line in enumerate(s.splitlines(), 1):
                    if 'libosxui' in line or ('isTargetOs' in line and 'macosx' in line):
                        print(f'  {i}: {line}')

    # Also remove the redundant inner macosx_NOTIOS guard that fix8 previously
    # added inside the outer block (now the outer block handles it)
    if '# libosxui disabled for iOS - sources moved to macosx_NOTIOS\nifeq ($(call isTargetOs, macosx_NOTIOS), true)' in s:
        s = s.replace(
            '  # libosxui disabled for iOS - sources moved to macosx_NOTIOS\nifeq ($(call isTargetOs, macosx_NOTIOS), true)\n',
            '  '
        )
        # Find matching endif and remove it
        print('[ios_sed_fixes] fix8: removed redundant inner macosx_NOTIOS guard')

    if s != original:
        p.write_text(s)
else:
    print('[ios_sed_fixes] fix8: WARN ClientLibraries.gmk not found')


# Fix 9: AwtLibraries.gmk - guard BUILD_LIBOSXAPP with macosx_NOTIOS.
# libosxapp sources are in src/java.desktop/macosx which gets moved out.
# libawt_lwawt depends on libosxapp so both must be skipped together.
p = ROOT / 'make/modules/java.desktop/lib/AwtLibraries.gmk'
if p.exists():
    s = p.read_text()
    original = s
    # Guard libosxapp block
    if 'libosxapp disabled for iOS' not in s:
        old = 'ifeq ($(call isTargetOs, macosx), true)\n  ##############################################################################\n  # Build libosxapp'
        new = 'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n  ##############################################################################\n  # Build libosxapp'
        if old in s:
            s = s.replace(old, new)
            print('[ios_sed_fixes] fix9a: patched libosxapp guard')
        else:
            # Try alternate - just find and replace the isTargetOs macosx guard near libosxapp
            s = re.sub(
                r'(ifeq \(\$\(call isTargetOs, macosx\), true\)\s*\n\s*#{10,}\s*\n\s*# Build libosxapp)',
                lambda m: m.group(0).replace('isTargetOs, macosx)', 'isTargetOs, macosx_NOTIOS)'),
                s
            )
            if s != original:
                print('[ios_sed_fixes] fix9a: patched libosxapp guard (regex)')
            else:
                print('[ios_sed_fixes] fix9a: WARN libosxapp guard not found')

    # Guard libawt_lwawt block
    if 'libawt_lwawt disabled for iOS' not in s:
        old2 = 'ifeq ($(call isTargetOs, macosx), true)\n  ##############################################################################\n  ## Build libawt_lwawt'
        new2 = 'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n  ##############################################################################\n  ## Build libawt_lwawt'
        if old2 in s:
            s = s.replace(old2, new2)
            print('[ios_sed_fixes] fix9b: patched libawt_lwawt guard')
        else:
            s2 = re.sub(
                r'(ifeq \(\$\(call isTargetOs, macosx\), true\)\s*\n\s*#{10,}\s*\n\s*## Build libawt_lwawt)',
                lambda m: m.group(0).replace('isTargetOs, macosx)', 'isTargetOs, macosx_NOTIOS)'),
                s
            )
            if s2 != s:
                s = s2
                print('[ios_sed_fixes] fix9b: patched libawt_lwawt guard (regex)')
            else:
                print('[ios_sed_fixes] fix9b: WARN libawt_lwawt guard not found')

    if s != original:
        p.write_text(s)
else:
    print('[ios_sed_fixes] fix9: WARN AwtLibraries.gmk not found')


# Fix 10: jdk.hotspot.agent/Lib.gmk - libsaproc links JavaRuntimeSupport
# which doesn't exist on iOS. Comment out TARGETS += $(BUILD_LIBSAPROC).
p = ROOT / 'make/modules/jdk.hotspot.agent/Lib.gmk'
if p.exists():
    s = p.read_text()
    if 'BUILD_LIBSAPROC)  # disabled for iOS' not in s:
        s2 = s.replace(
            'TARGETS += $(BUILD_LIBSAPROC)',
            '#TARGETS += $(BUILD_LIBSAPROC)  # disabled for iOS'
        )
        if s2 != s:
            p.write_text(s2)
            print('[ios_sed_fixes] fix10: patched jdk.hotspot.agent/Lib.gmk libsaproc')
        else:
            print('[ios_sed_fixes] fix10: WARN BUILD_LIBSAPROC not found in Lib.gmk')
    else:
        print('[ios_sed_fixes] fix10: libsaproc already disabled')
else:
    print('[ios_sed_fixes] fix10: WARN jdk.hotspot.agent/Lib.gmk not found')


# Fix 11: jdk.jpackage/Lib.gmk - jpackageapplauncher links Cocoa which
# doesn't exist on iOS. Replace with Foundation.
p = ROOT / 'make/modules/jdk.jpackage/Lib.gmk'
if p.exists():
    s = p.read_text()
    original = s
    s = re.sub(r'-framework Cocoa(\s)', r'-framework Foundation\1', s)
    s = re.sub(r'-framework Cocoa,', r'-framework Foundation,', s)
    s = re.sub(r'-framework Cocoa\\', r'-framework Foundation\\', s)
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix11: patched jdk.jpackage/Lib.gmk Cocoa -> Foundation')
        show(p, r'framework.*(Cocoa|Foundation)')
    else:
        print('[ios_sed_fixes] fix11: jdk.jpackage/Lib.gmk already patched or no Cocoa found')
        show(p, r'Cocoa|Foundation')
else:
    print('[ios_sed_fixes] fix11: WARN jdk.jpackage/Lib.gmk not found')


# Fix 12: ClientLibraries.gmk - libfontmanager depends on libawt_lwawt
# which is skipped on iOS. Switch ALL occurrences to libawt_headless.
# Run unconditionally since partial application leaves stale lwawt references.
p = ROOT / 'make/modules/java.desktop/lib/ClientLibraries.gmk'
if p.exists():
    s = p.read_text()
    original = s
    # Replace ALL occurrences unconditionally via regex
    s = re.sub(
        r'(JDK_LIBS_macosx\s*:=\s*)libawt_lwawt',
        r'\1libawt_headless',
        s
    )
    # Also catch bare libawt_lwawt references in LIBS lines
    s = re.sub(
        r'\blibawt_lwawt\b',
        'libawt_headless',
        s
    )
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix12: patched ClientLibraries.gmk all libawt_lwawt -> libawt_headless')
        for line in s.splitlines():
            if 'libawt' in line:
                print(' ', repr(line))
    else:
        print('[ios_sed_fixes] fix12: no libawt_lwawt found in ClientLibraries.gmk')
        for line in s.splitlines():
            if 'libawt' in line:
                print(' ', repr(line))
else:
    print('[ios_sed_fixes] fix12: WARN ClientLibraries.gmk not found')


# Fix 13: AwtLibraries.gmk - libawt_headless is guarded with:
#   ifeq ($(call isTargetOs, windows macosx), false)
# which means it does NOT build on macOS. Since we're building with a macOS
# toolchain targeting iOS, libawt_headless never gets built, so libfontmanager
# can't depend on it. Change the guard to macosx_NOTIOS so iOS builds it.
p = ROOT / 'make/modules/java.desktop/lib/AwtLibraries.gmk'
if p.exists():
    s = p.read_text()
    original = s
    patterns = [
        ('ifeq ($(call isTargetOs, windows macosx), false)',
         'ifeq ($(call isTargetOs, windows macosx_NOTIOS), false)'),
        ('ifeq ($(call isTargetOs, windows macosx_NOTIOS), false)', None),  # already patched
    ]
    patched = False
    for old, new in patterns:
        if new is None:
            print('[ios_sed_fixes] fix13: libawt_headless guard already patched')
            patched = True
            break
        if old in s:
            s = s.replace(old, new)
            patched = True
            break
    if not patched:
        # Try regex for whitespace variations
        s2 = re.sub(
            r'ifeq \(\$\(call isTargetOs, windows macosx\), false\)',
            'ifeq ($(call isTargetOs, windows macosx_NOTIOS), false)',
            s
        )
        if s2 != s:
            s = s2
            patched = True
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix13: patched AwtLibraries.gmk libawt_headless guard')
    elif not patched:
        print('[ios_sed_fixes] fix13: WARN libawt_headless guard not found')
        for line in s.splitlines():
            if 'libawt_headless' in line or ('windows' in line and 'macosx' in line):
                print(' ', repr(line))
else:
    print('[ios_sed_fixes] fix13: WARN AwtLibraries.gmk not found')


# Fix 14: AwtLibraries.gmk - libawt LIBS_macosx links macOS-only frameworks
# (ApplicationServices, AudioToolbox, Cocoa, JavaRuntimeSupport, Metal, OpenGL)
# that don't exist on iOS. The cleanest fix is to rename LIBS_macosx to
# LIBS_macosx_NOTIOS so iOS gets an empty link list. Also handle any remaining
# standalone framework references that individual regex removals might miss.
p = ROOT / 'make/modules/java.desktop/lib/AwtLibraries.gmk'
if p.exists():
    s = p.read_text()
    original = s

    # Strategy 1: rename LIBS_macosx to LIBS_macosx_NOTIOS in libawt block
    # This is idempotent and covers all frameworks in one shot.
    # Only rename the specific block that has the problematic frameworks.
    s = re.sub(
        r'(    LIBS_macosx := \\\n'
        r'(?:[ \t]*-framework (?:ApplicationServices|AudioToolbox|Cocoa|JavaRuntimeSupport|Metal|OpenGL)[, \t]*\\\n)+)',
        lambda m: m.group(0).replace('    LIBS_macosx := \\\n', '    LIBS_macosx_NOTIOS := \\\n', 1),
        s
    )

    # Strategy 2: for any remaining individual framework lines that aren't
    # covered by the block rename, remove them directly.
    for fw in ['ApplicationServices', 'JavaRuntimeSupport', 'Metal', 'OpenGL']:
        # Match with optional comma before the trailing backslash
        s = re.sub(r'[ \t]*-framework ' + fw + r'[, \t]*\\\n', '', s)

    # Replace remaining Cocoa with Foundation (don't remove — need something)
    s = re.sub(r'(-framework )Cocoa', r'\1Foundation', s)

    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix14: patched AwtLibraries.gmk framework references')
        for line in s.splitlines():
            if any(f in line for f in ['ApplicationServices', 'JavaRuntimeSupport', 'Metal', 'OpenGL', 'Cocoa', 'LIBS_macosx']):
                print(' ', line.strip())
    else:
        print('[ios_sed_fixes] fix14: AwtLibraries.gmk already patched or no matches')
else:
    print('[ios_sed_fixes] fix14: WARN AwtLibraries.gmk not found')


# Fix 15: java.desktop/Lib.gmk - libjsound links AudioUnit which doesn't
# exist on iOS. Replace with AVFoundation. CoreMIDI IS available on iOS
# (since iOS 4.2) so leave it alone.
p = ROOT / 'make/modules/java.desktop/Lib.gmk'
if p.exists():
    s = p.read_text()
    original = s
    # Replace AudioUnit with AVFoundation only
    s = re.sub(r'(-framework )AudioUnit', r'\1AVFoundation', s)
    # Restore CoreMIDI if fix15 previously removed it
    if 'CoreMIDI' not in s and 'AVFoundation' in s:
        s = re.sub(
            r'(-framework AVFoundation[, \t]*\\\n)',
            r'\1          -framework CoreMIDI \\\n',
            s
        )
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix15: patched java.desktop/Lib.gmk libjsound frameworks')
        for line in s.splitlines():
            if any(f in line for f in ['AudioUnit', 'AVFoundation', 'CoreMIDI', 'AudioToolbox']):
                print(' ', line.strip())
    else:
        print('[ios_sed_fixes] fix15: java.desktop/Lib.gmk already patched or no matches')
else:
    print('[ios_sed_fixes] fix15: WARN java.desktop/Lib.gmk not found')

# Fix 16: os_bsd.cpp - DeviceRequiresTXMWorkaround() calls opendir/readdir
# which acquires a pthread mutex at address 0x40 that is unmapped on Darwin 27
# during early JVM init (CodeCache::initialize). Replace with sysctlbyname
# which is safe to call at any point during init.
#
# NOTE: a naive regex like '\{[^}]*\}' breaks if the function body has any
# nested braces (e.g. an if-block), since [^}]* stops at the FIRST closing
# brace, not the function's actual closing brace. We instead find the
# opening brace and walk forward counting depth to find the true end.
p = ROOT / 'src/hotspot/os/bsd/os_bsd.cpp'
if p.exists():
    s = p.read_text()
    if 'sysctlbyname("hw.machine"' not in s:
        marker = 'DeviceRequiresTXMWorkaround()'
        idx = s.find(marker)
        if idx == -1:
            print('[ios_sed_fixes] fix16: WARN DeviceRequiresTXMWorkaround not found in os_bsd.cpp')
        else:
            # Find the function definition's opening brace (skip past any
            # forward declaration that ends in ';' before the real def with '{')
            search_from = idx
            func_start = None
            brace_open = None
            while True:
                next_marker = s.find(marker, search_from)
                if next_marker == -1:
                    break
                # look at what follows after "()" - skip whitespace
                j = next_marker + len(marker)
                while j < len(s) and s[j] in ' \t\n':
                    j += 1
                if j < len(s) and s[j] == '{':
                    func_start = next_marker
                    brace_open = j
                    break
                search_from = next_marker + len(marker)

            if brace_open is None:
                print('[ios_sed_fixes] fix16: WARN could not find function body opening brace')
            else:
                # Walk forward counting brace depth to find the matching close
                depth = 0
                i = brace_open
                func_end = None
                while i < len(s):
                    if s[i] == '{':
                        depth += 1
                    elif s[i] == '}':
                        depth -= 1
                        if depth == 0:
                            func_end = i
                            break
                    i += 1

                if func_end is None:
                    print('[ios_sed_fixes] fix16: WARN could not find matching closing brace')
                else:
                    # Find the actual start of the function signature (walk
                    # back from func_start to the start of the line containing
                    # "static bool" or similar, to keep the replacement clean)
                    line_start = s.rfind('\n', 0, func_start) + 1
                    new_func = (
                        'static bool DeviceRequiresTXMWorkaround() {\n'
                        '  // readdir() crashes on Darwin 27 during early JVM init:\n'
                        '  // the pthread mutex it acquires at 0x40 is unmapped at this\n'
                        '  // point in CodeCache::initialize. Use sysctlbyname instead.\n'
                        '  char machine[64] = {};\n'
                        '  size_t len = sizeof(machine);\n'
                        '  if (sysctlbyname("hw.machine", machine, &len, nullptr, 0) != 0) {\n'
                        '    return false;\n'
                        '  }\n'
                        '  return strncmp(machine, "iPhone", 6) == 0;\n'
                        '}'
                    )
                    s = s[:line_start] + new_func + s[func_end+1:]
                    p.write_text(s)
                    print('[ios_sed_fixes] fix16: patched DeviceRequiresTXMWorkaround in os_bsd.cpp (brace-counted)')
    else:
        print('[ios_sed_fixes] fix16: os_bsd.cpp already patched')
else:
    print('[ios_sed_fixes] fix16: WARN os_bsd.cpp not found')

# Fix 17: atomic.hpp needs #include "os_bsd.hpp" so mirror_w/mirror_x macros
# are visible. The mirror_mapping patch's hunk for this file rejected.
p = ROOT / 'src/hotspot/share/runtime/atomic.hpp'
if p.exists():
    s = p.read_text()
    if 'os_bsd.hpp' not in s:
        s2 = s.replace(
            '#include "utilities/macros.hpp"\n\n#include <type_traits>',
            '#include "utilities/macros.hpp"\n\n#ifdef __APPLE__\n#include "os_bsd.hpp"\n#endif\n\n#include <type_traits>'
        )
        if s2 != s:
            p.write_text(s2)
            print('[ios_sed_fixes] fix17: patched atomic.hpp os_bsd.hpp include')
        else:
            print('[ios_sed_fixes] fix17: WARN atomic.hpp pattern not found')
    else:
        print('[ios_sed_fixes] fix17: atomic.hpp already patched')
else:
    print('[ios_sed_fixes] fix17: WARN atomic.hpp not found')

# Fix 18: signals_posix.cpp missing PROT_READ/PROT_EXEC/PROT_WRITE — the
# add-os-bsd-include hunk that also adds sys/mman.h rejected. Add it directly.
p = ROOT / 'src/hotspot/os/posix/signals_posix.cpp'
if p.exists():
    s = p.read_text()
    if '<sys/mman.h>' not in s:
        s2 = s.replace(
            '#include <signal.h>',
            '#include <signal.h>\n#include <sys/mman.h>'
        )
        if s2 != s:
            p.write_text(s2)
            print('[ios_sed_fixes] fix18: patched signals_posix.cpp sys/mman.h')
        else:
            print('[ios_sed_fixes] fix18: WARN signal.h not found in signals_posix.cpp')
    else:
        print('[ios_sed_fixes] fix18: signals_posix.cpp already patched')
else:
    print('[ios_sed_fixes] fix18: WARN signals_posix.cpp not found')

# Fix 19: icache_bsd_aarch64.hpp - __clear_cache is not available on iOS.
# Replace with sys_icache_invalidate which is the iOS equivalent.
p = ROOT / 'src/hotspot/os_cpu/bsd_aarch64/icache_bsd_aarch64.hpp'
if p.exists():
    s = p.read_text()
    if 'sys_icache_invalidate' not in s:
        original = s
        s = s.replace(
            '  static void invalidate_word(address addr) {\n    __clear_cache((char *)addr, (char *)(addr + 4));\n  }\n  static void invalidate_range(address start, int nbytes) {\n    __clear_cache((char *)start, (char *)(start + nbytes));\n  }',
            '  static void invalidate_word(address addr) {\n    sys_icache_invalidate((char *)addr, 4);\n  }\n  static void invalidate_range(address start, int nbytes) {\n    sys_icache_invalidate((char *)start, nbytes);\n  }'
        )
        if s != original:
            p.write_text(s)
            print('[ios_sed_fixes] fix19: patched icache_bsd_aarch64.hpp __clear_cache')
        else:
            print('[ios_sed_fixes] fix19: WARN __clear_cache pattern not found')
    else:
        print('[ios_sed_fixes] fix19: icache_bsd_aarch64.hpp already patched')
else:
    print('[ios_sed_fixes] fix19: WARN icache_bsd_aarch64.hpp not found')

# Fix 20: libosxsecurity uses macOS Keychain APIs unavailable on iOS.
# The Lib.gmk guard didn't apply. Skip by changing the ifeq guard directly
# using regex to catch any whitespace variation.
p = ROOT / 'make/modules/java.base/Lib.gmk'
if p.exists():
    s = p.read_text()
    original = s
    # Replace any macosx guard that precedes libosxsecurity
    s = re.sub(
        r'(ifeq \(\$\(call isTargetOs, )macosx(\), true\)\n[^\n]*\n[^\n]*security library)',
        r'\1macosx_NOTIOS\2',
        s
    )
    if s != original:
        p.write_text(s)
        print('[ios_sed_fixes] fix20: patched Lib.gmk libosxsecurity guard')
    else:
        # Nuclear option: just comment out the entire libosxsecurity source
        p2 = ROOT / 'src/java.base/macosx/native/libosxsecurity/KeystoreImpl.m'
        if p2.exists():
            content = p2.read_text()
            if '#if !TARGET_OS_IPHONE' not in content:
                p2.write_text(
                    '#include <TargetConditionals.h>\n'
                    '#if !TARGET_OS_IPHONE\n'
                    + content +
                    '#endif\n'
                )
                print('[ios_sed_fixes] fix20: wrapped KeystoreImpl.m in iOS guard')
            else:
                print('[ios_sed_fixes] fix20: KeystoreImpl.m already guarded')
        else:
            print('[ios_sed_fixes] fix20: WARN neither Lib.gmk nor KeystoreImpl.m fixable')
else:
    print('[ios_sed_fixes] fix20: WARN java.base/Lib.gmk not found')

# Fix 21: java.desktop/Lib.gmk - guard BUILD_LIBOSXAPP with macosx_NOTIOS.
# Sources moved out under the iOS hack, so this needs skipping here too.
p = ROOT / 'make/modules/java.desktop/Lib.gmk'
if p.exists():
    s = p.read_text()
    if 'libosxapp disabled for iOS' not in s:
        old = '$(eval $(call SetupJdkLibrary, BUILD_LIBOSXAPP,'
        if old in s:
            idx = s.index(old)
            targets_marker = 'TARGETS += $(BUILD_LIBOSXAPP)'
            targets_idx = s.index(targets_marker, idx)
            end_idx = targets_idx + len(targets_marker)
            block = s[idx:end_idx]
            new_block = (
                '# libosxapp disabled for iOS - sources moved to macosx_NOTIOS\n'
                'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n'
                + block + '\n'
                'endif'
            )
            s = s[:idx] + new_block + s[end_idx:]
            p.write_text(s)
            print('[ios_sed_fixes] fix21: patched java.desktop/Lib.gmk BUILD_LIBOSXAPP guard')
        else:
            print('[ios_sed_fixes] fix21: WARN BUILD_LIBOSXAPP block not found')
    else:
        print('[ios_sed_fixes] fix21: java.desktop/Lib.gmk already patched')
else:
    print('[ios_sed_fixes] fix21: WARN java.desktop/Lib.gmk not found')

# Fix 22: java.desktop/Lib.gmk - guard BUILD_LIBOSX with macosx_NOTIOS.
p = ROOT / 'make/modules/java.desktop/Lib.gmk'
if p.exists():
    s = p.read_text()
    if 'libosx disabled for iOS' not in s:
        old = '$(eval $(call SetupJdkLibrary, BUILD_LIBOSX,'
        if old in s:
            idx = s.index(old)
            targets_marker = 'TARGETS += $(BUILD_LIBOSX)'
            targets_idx = s.index(targets_marker, idx)
            end_idx = targets_idx + len(targets_marker)
            block = s[idx:end_idx]
            new_block = (
                '# libosx disabled for iOS - sources moved to macosx_NOTIOS\n'
                'ifeq ($(call isTargetOs, macosx_NOTIOS), true)\n'
                + block + '\n'
                'endif'
            )
            s = s[:idx] + new_block + s[end_idx:]
            p.write_text(s)
            print('[ios_sed_fixes] fix22: patched java.desktop/Lib.gmk BUILD_LIBOSX guard')
        else:
            print('[ios_sed_fixes] fix22: WARN BUILD_LIBOSX block not found')
    else:
        print('[ios_sed_fixes] fix22: java.desktop/Lib.gmk already patched')
else:
    print('[ios_sed_fixes] fix22: WARN java.desktop/Lib.gmk not found')

# Fix 23: java.security.jgss/Lib.gmk - libosxkrb5 uses Kerberos.h and
# SCDynamicStore APIs unavailable on iOS. Disable the whole target.
p = ROOT / 'make/modules/java.security.jgss/Lib.gmk'
if p.exists():
    s = p.read_text()
    if 'BUILD_LIBOSXKRB5)  # disabled for iOS' not in s:
        s2 = s.replace(
            'TARGETS += $(BUILD_LIBOSXKRB5)',
            '#TARGETS += $(BUILD_LIBOSXKRB5)  # disabled for iOS'
        )
        if s2 != s:
            p.write_text(s2)
            print('[ios_sed_fixes] fix23: patched java.security.jgss/Lib.gmk libosxkrb5')
        else:
            print('[ios_sed_fixes] fix23: WARN BUILD_LIBOSXKRB5 not found in Lib.gmk')
    else:
        print('[ios_sed_fixes] fix23: libosxkrb5 already disabled')
else:
    print('[ios_sed_fixes] fix23: WARN java.security.jgss/Lib.gmk not found')

# Fix 24: os_bsd.cpp - get_debug_jit_mapping() uses BreakGetJITMapping()
# (brk #0x69) which is deprecated in current JIT26 scripts and returns a
# garbage address (0xcccccccc...). vm_remap() then fails with KERN_INVALID_ADDRESS
# (error 1) which is what "[JIT26] Failed to remap RX region 1" actually means.
# Fix: allocate the RX region normally with mmap, then use JIT26PrepareRegion
# (brk #0xf00d command 1) to make it executable, matching what hooked_mmap does.
p = ROOT / 'src/hotspot/os/bsd/os_bsd.cpp'
if p.exists():
    s = p.read_text()
    if 'BreakGetJITMapping' in s and 'brk #0xf00d' not in s:
        old = (
            'char* get_debug_jit_mapping(size_t bytes) {\n'
            '    // the map we got has debuggable flag, r-x, setup mirrored map\n'
            '    vm_address_t buf_rx = 0;\n'
            '    if(MirrorMappedCodeCache) {\n'
            '        if(DeviceRequiresTXMWorkaround()) {\n'
            '            printf("[JIT26] Requesting %zu MB for JIT mapping\\n", bytes/ (1024 * 1024));\n'
            '            buf_rx = (vm_address_t)BreakGetJITMapping(bytes);\n'
            '        }\n'
            '        if(buf_rx) {\n'
            '            printf("[JIT26] Got JIT mapping %p from debugger\\n", (void*)buf_rx);\n'
            '        } else {\n'
            '            buf_rx = (vm_address_t)mmap(NULL, bytes, PROT_READ | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);\n'
            '        }'
        )
        new = (
            'char* get_debug_jit_mapping(size_t bytes) {\n'
            '    // the map we got has debuggable flag, r-x, setup mirrored map\n'
            '    vm_address_t buf_rx = 0;\n'
            '    if(MirrorMappedCodeCache) {\n'
            '        // BreakGetJITMapping (brk #0x69) is deprecated in JIT26 scripts\n'
            '        // and returns a garbage address causing vm_remap KERN_INVALID_ADDRESS.\n'
            '        // Allocate normally then use JIT26PrepareRegion (brk #0xf00d cmd 1).\n'
            '        printf("[JIT26] Requesting %zu MB for JIT mapping\\n", bytes / (1024 * 1024));\n'
            '        buf_rx = (vm_address_t)mmap(NULL, bytes, PROT_READ | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);\n'
            '        if(buf_rx && buf_rx != (vm_address_t)MAP_FAILED) {\n'
            '            JIT26PrepareRegion((void*)buf_rx, bytes);\n'
            '            printf("[JIT26] Got JIT mapping %p via JIT26PrepareRegion\\n", (void*)buf_rx);\n'
            '        }'
        )
        s2 = s.replace(old, new)
        if s2 != s:
            p.write_text(s2)
            print('[ios_sed_fixes] fix24: patched get_debug_jit_mapping to use JIT26PrepareRegion')
        else:
            print('[ios_sed_fixes] fix24: WARN get_debug_jit_mapping pattern not found')
            print('[ios_sed_fixes] fix24: searching for BreakGetJITMapping...')
            for i, line in enumerate(s.splitlines(), 1):
                if 'BreakGetJITMapping' in line or 'get_debug_jit_mapping' in line:
                    print(f'  {i}: {line}')
    elif 'brk #0xf00d' in s:
        print('[ios_sed_fixes] fix24: already patched')
    else:
        print('[ios_sed_fixes] fix24: BreakGetJITMapping not found - patch may already be applied or function changed')
else:
    print('[ios_sed_fixes] fix24: WARN os_bsd.cpp not found')
