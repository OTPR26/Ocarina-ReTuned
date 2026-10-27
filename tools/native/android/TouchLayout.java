package org.triaevum.android;

import java.util.LinkedHashMap;
import java.util.Map;

/** Normalized control centers, independent of screen resolution and density. */
final class TouchLayout {
    private static final String KEYS = "|a|b|x|y|l|r|zl|zr|start|settings|dpad|move|look|visibility|map|";
    private final Map<String, float[]> centers = new LinkedHashMap<>();

    float[] get(String key) { return centers.get(key); }
    void clear() { centers.clear(); }
    void set(String key, float x, float y) {
        if (!KEYS.contains("|" + key + "|") || !Float.isFinite(x) || !Float.isFinite(y)) return;
        centers.put(key, new float[]{Math.max(0, Math.min(1, x)), Math.max(0, Math.min(1, y))});
    }
    TouchLayout copy() { return decode(encode()); }
    String encode() {
        StringBuilder out = new StringBuilder("v1");
        for (Map.Entry<String, float[]> entry : centers.entrySet()) {
            float[] p = entry.getValue();
            out.append(';').append(entry.getKey()).append('=').append(p[0]).append(',').append(p[1]);
        }
        return out.toString();
    }
    static TouchLayout decode(String value) {
        TouchLayout layout = new TouchLayout();
        if (value == null || value.length() > 4096) return layout;
        String[] fields = value.split(";", -1);
        if (!fields[0].equals("v1")) return layout;
        for (int i = 1; i < fields.length; i++) {
            String[] pair = fields[i].split("=", -1);
            if (pair.length != 2) continue;
            String[] xy = pair[1].split(",", -1);
            if (xy.length != 2) continue;
            try { layout.set(pair[0], Float.parseFloat(xy[0]), Float.parseFloat(xy[1])); }
            catch (NumberFormatException ignored) { }
        }
        return layout;
    }
}
