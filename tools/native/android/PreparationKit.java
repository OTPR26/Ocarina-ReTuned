package org.triaevum.android;

import android.content.Context;
import org.json.JSONObject;
import java.io.*;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Installs only the signed APK's neutral tools; never downloads prepared game data. */
final class PreparationKit {
    static void deleteTree(File file) throws IOException {
        if (java.nio.file.Files.isSymbolicLink(file.toPath())) {
            java.nio.file.Files.deleteIfExists(file.toPath());
            return;
        }
        File[] children = file.listFiles();
        if (children != null) for (File child : children) deleteTree(child);
        if (file.exists() && !file.delete()) throw new IOException("Cannot remove interrupted preparation tools");
    }

    static File install(Context context) throws Exception {
        JSONObject metadata;
        try (InputStream input = context.getAssets().open("retuned/preparation-kit.json")) {
            ByteArrayOutputStream text = new ByteArrayOutputStream();
            byte[] block = new byte[4096]; int count;
            while ((count = input.read(block)) != -1) {
                if (text.size() + count > 16384) throw new IOException("Invalid tools manifest");
                text.write(block, 0, count);
            }
            metadata = new JSONObject(text.toString("UTF-8"));
        } catch (FileNotFoundException error) {
            throw new IOException("ROM preparation tools are not included in this build.", error);
        }
        if (!"retuned_preparation_asset_v1".equals(metadata.getString("format")))
            throw new IOException("Unsupported preparation tools");
        String expected = metadata.getString("sha256");
        if (!expected.matches("[0-9a-f]{64}")) throw new IOException("Invalid tools checksum");
        long maximum = metadata.getLong("unpacked_bytes");
        if (maximum < 1 || maximum > 1073741824L) throw new IOException("Invalid tools size");
        File parent = new File(context.getFilesDir(), "preparation-tools");
        if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create tools directory");
        File destination = new File(parent, expected);
        if (new File(destination, "complete").isFile()) return destination;
        File stage = new File(parent, ".install-" + UUID.randomUUID());
        if (!stage.mkdir()) throw new IOException("Cannot stage preparation tools");
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream original = context.getAssets().open("retuned/preparation-kit.zip");
                 DigestInputStream checked = new DigestInputStream(original, digest);
                 ZipInputStream archive = new ZipInputStream(checked)) {
                byte[] block = new byte[65536]; ZipEntry entry; long total = 0; int entries = 0;
                java.util.HashSet<String> names = new java.util.HashSet<>();
                while ((entry = archive.getNextEntry()) != null) {
                    if (++entries > 100000 || !names.add(entry.getName())) throw new IOException("Invalid tools archive");
                    File target = new File(stage, entry.getName());
                    if (!target.getCanonicalPath().startsWith(stage.getCanonicalPath() + File.separator))
                        throw new IOException("Unsafe tools archive path");
                    if (entry.isDirectory()) { if (!target.isDirectory() && !target.mkdirs()) throw new IOException("Cannot create tools folder"); continue; }
                    File directory = target.getParentFile();
                    if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create tools folder");
                    try (OutputStream output = new FileOutputStream(target)) {
                        int count;
                        while ((count = archive.read(block)) != -1) {
                            total += count;
                            if (total > maximum) throw new IOException("Tools archive exceeds declared size");
                            output.write(block, 0, count);
                        }
                    }
                    if (!target.setReadOnly()) throw new IOException("Cannot protect preparation tools");
                }
                while (checked.read(block) != -1) { }
                if (total != maximum) throw new IOException("Incomplete preparation tools");
            }
            StringBuilder actual = new StringBuilder();
            for (byte value : digest.digest()) actual.append(String.format(Locale.ROOT, "%02x", value & 255));
            if (!expected.equals(actual.toString())) throw new IOException("Preparation tools failed their checksum");
            try (FileOutputStream receipt = new FileOutputStream(new File(stage, "complete"))) {
                receipt.write(expected.getBytes(java.nio.charset.StandardCharsets.US_ASCII)); receipt.getFD().sync();
            }
            if (destination.exists()) deleteTree(destination);
            if (!stage.renameTo(destination)) throw new IOException("Cannot activate preparation tools");
            return destination;
        } finally { deleteTree(stage); }
    }
}
