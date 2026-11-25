package org.triaevum.android;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.util.Base64;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** Document transport only. Native code validates the run and owns its saves. */
public final class RandomizerDocuments {
    public static final int IMPORT = 4620, EXPORT = 4621;
    private static final int LIMIT = 10 * 1024 * 1024;
    private final Activity activity;
    private int request, slot;
    private boolean delivered;
    private byte[] exportBytes;
    private String result = "";

    public RandomizerDocuments(Activity activity) { this.activity = activity; }

    public synchronized boolean chooseImport(int selectedSlot) {
        return begin(IMPORT, selectedSlot, null);
    }
    public synchronized boolean chooseExport(int selectedSlot, byte[] bytes) {
        if (bytes == null || bytes.length == 0 || bytes.length > LIMIT) return false;
        return begin(EXPORT, selectedSlot, bytes.clone());
    }
    private boolean begin(int operation, int selectedSlot, byte[] bytes) {
        if (request != 0 || selectedSlot < 0 || selectedSlot > 2) return false;
        request = operation; slot = selectedSlot; exportBytes = bytes; delivered = false;
        activity.runOnUiThread(() -> {
            try {
                Intent picker = new Intent(operation == IMPORT ? Intent.ACTION_OPEN_DOCUMENT : Intent.ACTION_CREATE_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE).setType("application/octet-stream");
                if (operation == IMPORT) picker.setType("*/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                else picker.putExtra(Intent.EXTRA_TITLE, "randomizer-slot-" + (selectedSlot + 1) + ".retuned-run");
                activity.startActivityForResult(picker, operation);
            } catch (Exception error) { complete(null, false, error); }
        });
        return true;
    }
    public boolean result(int operation, int code, Intent data) {
        final byte[] outgoing;
        synchronized (this) {
            if (operation != request || (operation != IMPORT && operation != EXPORT)) return false;
            if (delivered || !result.isEmpty()) return true;
            delivered = true;
            outgoing = exportBytes;
        }
        if (code != Activity.RESULT_OK || data == null || data.getData() == null) {
            complete(null, true, null); return true;
        }
        final Uri uri = data.getData();
        new Thread(() -> {
            try {
                if (operation == IMPORT) {
                    byte[] incoming;
                    try (InputStream input = activity.getContentResolver().openInputStream(uri)) {
                        if (input == null) throw new IOException("Could not read the selected run");
                        incoming = readBounded(input);
                    }
                    complete(incoming, false, null);
                } else {
                    try (OutputStream output = activity.getContentResolver().openOutputStream(uri, "wt")) {
                        if (output == null) throw new IOException("Could not open the export document");
                        output.write(outgoing); output.flush();
                    }
                    complete(null, false, null);
                }
            } catch (Exception error) { complete(null, false, error); }
        }, "randomizer-document").start();
        return true;
    }
    static byte[] readBounded(InputStream input) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[65536];
        for (int count; (count = input.read(buffer)) != -1;) {
            if (count > LIMIT - output.size()) throw new IOException("Randomizer run exceeds 10 MB");
            output.write(buffer, 0, count);
        }
        if (output.size() == 0) throw new IOException("Randomizer run is empty");
        return output.toByteArray();
    }
    private synchronized void complete(byte[] bytes, boolean cancelled, Exception error) {
        if (request == 0 || !result.isEmpty()) return;
        try {
            JSONObject value = new JSONObject().put("slot", slot).put("operation", request == IMPORT ? "import" : "export")
                .put("cancelled", cancelled);
            if (error != null) value.put("error", error.getMessage() == null ? "Document transfer failed" : error.getMessage());
            else if (bytes != null) value.put("data", Base64.encodeToString(bytes, Base64.NO_WRAP));
            result = value.toString();
        } catch (Exception unexpected) { result = "{\"error\":\"Document transfer failed\"}"; }
        exportBytes = null;
    }
    public synchronized String takeResult() {
        String value = result;
        if (!value.isEmpty()) { result = ""; request = 0; }
        return value;
    }
}
