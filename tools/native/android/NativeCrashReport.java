package org.triaevum.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Reads only signal numbers and module-relative frames from an Android tombstone. */
final class NativeCrashReport {
    private static final int LIMIT = 2 * 1024 * 1024;
    private static final Set<String> LIBRARIES = new HashSet<>(Arrays.asList(
        "libTriAevum.so", "libtriaevum_public_runtime.so", "libtriaevum_title_aot.so", "triaevum_title_aot.so",
        "libtriaevum_title_bootstrap.so",
        "libSDL2.so", "libc.so", "libm.so", "libdl.so", "liblog.so", "libvulkan.so",
        "libc++_shared.so", "libshaderc.so", "libshaderc_shared.so", "libart.so", "libandroid_runtime.so"));

    static String read(InputStream input) {
        if (input == null) return "Native trace unavailable.";
        try (InputStream source = input) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] block = new byte[8192];
            for (int count; (count = source.read(block)) != -1;) {
                if (bytes.size() + count > LIMIT) return "Native trace exceeds report limit.";
                bytes.write(block, 0, count);
            }
            return summarize(bytes.toByteArray());
        } catch (IOException | IllegalArgumentException error) {
            return "Native trace could not be decoded.";
        }
    }

    // Field numbers follow AOSP debuggerd/proto/tombstone.proto. All other
    // fields, including paths, command lines, messages, and memory dumps, are skipped.
    private static String summarize(byte[] bytes) throws IOException {
        Reader root = new Reader(bytes, 0, bytes.length);
        long tid = -1;
        String signal = "";
        for (int tag; (tag = root.tag()) != 0;) {
            if (tag == (6 << 3)) tid = root.number();
            else if (tag == ((10 << 3) | 2)) {
                Reader info = root.message();
                long number = 0, code = 0;
                for (int field; (field = info.tag()) != 0;) {
                    if (field == 8) number = info.number();
                    else if (field == 24) code = (int)info.number();
                    else info.skip(field);
                }
                signal = "Native signal=" + number + ", code=" + code + '\n';
            } else root.skip(tag);
        }
        root = new Reader(bytes, 0, bytes.length);
        for (int tag; (tag = root.tag()) != 0;) {
            if (tag != ((16 << 3) | 2)) { root.skip(tag); continue; }
            Reader entry = root.message(), thread = null;
            long key = -2;
            for (int field; (field = entry.tag()) != 0;) {
                if (field == 8) key = entry.number();
                else if (field == 18) thread = entry.message();
                else entry.skip(field);
            }
            if (key != tid || thread == null) continue;
            StringBuilder frames = new StringBuilder();
            int count = 0;
            for (int field; (field = thread.tag()) != 0 && count < 12;) {
                if (field != 34) { thread.skip(field); continue; }
                Reader frame = thread.message();
                long pc = 0;
                String module = "other native library", build = "";
                for (int part; (part = frame.tag()) != 0;) {
                    if (part == 8) pc = frame.number();
                    else if (part == 50) module = module(frame.text());
                    else if (part == 66) {
                        String value = frame.text();
                        if (value.matches("[0-9a-fA-F]{8,64}")) build = value.toLowerCase(Locale.ROOT);
                    } else frame.skip(part);
                }
                frames.append("  #").append(count++).append(" pc ").append(Long.toHexString(pc))
                    .append(' ').append(module);
                if (!build.isEmpty()) frames.append(" build=").append(build);
                frames.append('\n');
            }
            return signal + (count > 0 ? frames : "Native frames unavailable.");
        }
        return signal + "Native frames unavailable.";
    }

    private static String module(String path) {
        String name = path.substring(path.lastIndexOf('/') + 1);
        if (LIBRARIES.contains(name)) return name;
        if (name.matches("(?:vulkan\\.(?:adreno|mali)|libGLESv[12]_adreno)\\.so")) return name;
        return "other native library";
    }

    private static final class Reader {
        final byte[] bytes;
        final int end;
        int position;
        Reader(byte[] bytes, int position, int end) { this.bytes=bytes; this.position=position; this.end=end; }
        int tag() throws IOException {
            if (position == end) return 0;
            long value = number();
            if (value < 8 || value > Integer.MAX_VALUE) throw new IOException();
            return (int)value;
        }
        long number() throws IOException {
            long result = 0;
            for (int shift=0; shift<64; shift+=7) {
                if (position == end) throw new IOException();
                int value = bytes[position++] & 255;
                if (shift == 63 && value > 1) throw new IOException();
                result |= (long)(value & 127) << shift;
                if ((value & 128) == 0) return result;
            }
            throw new IOException();
        }
        Reader message() throws IOException {
            long length = number();
            if (length < 0 || length > end-position) throw new IOException();
            Reader value = new Reader(bytes, position, position+(int)length);
            position += (int)length;
            return value;
        }
        String text() throws IOException {
            Reader value = message();
            return value.end-value.position > 512 ? "" :
                new String(bytes, value.position, value.end-value.position, StandardCharsets.UTF_8);
        }
        void skip(int tag) throws IOException {
            switch (tag & 7) {
                case 0: number(); return;
                case 1: advance(8); return;
                case 2: message(); return;
                case 5: advance(4); return;
                default: throw new IOException();
            }
        }
        void advance(int count) throws IOException {
            if (count > end-position) throw new IOException();
            position += count;
        }
    }
}
