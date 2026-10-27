// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Compare the signed build's preparation inputs with the activated installation. */
final class PreparationUpdate {
    static String expected(Context context) throws Exception {
        try (InputStream input = context.getAssets().open("retuned/preparation-kit.json")) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] block = new byte[4096]; int count;
            while ((count = input.read(block)) != -1) {
                if (bytes.size() + count > 16384) throw new IOException("Invalid preparation manifest");
                bytes.write(block, 0, count);
            }
            byte[] data = bytes.toByteArray();
            String identity = new JSONObject(new String(data, StandardCharsets.UTF_8)).getString("preparation_identity");
            if (!identity.matches("[0-9a-f]{64}")) throw new IOException("Invalid preparation identity");
            return identity;
        }
    }
    static boolean current(Context context) throws Exception {
        String required = expected(context);
        File root = context.getExternalFilesDir(null);
        if (root == null) return false;
        JSONObject profile = new JSONObject(new String(Files.readAllBytes(new File(root, "native-launch.json").toPath()), StandardCharsets.UTF_8));
        JSONArray args = profile.getJSONArray("arguments");
        for (int i = 0; i + 1 < args.length(); i++) {
            if (!"--a32-process-manifest".equals(args.getString(i))) continue;
            File installation = new File(args.getString(i + 1)).getParentFile();
            try {
                JSONObject receipt = new JSONObject(new String(Files.readAllBytes(new File(installation, "setup-receipt.json").toPath()), StandardCharsets.UTF_8));
                return required.equals(receipt.optString("preparation_identity"));
            } catch (IOException | org.json.JSONException legacyOrDamagedReceipt) { return false; }
        }
        return false;
    }
}
