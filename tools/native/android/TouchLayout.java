package org.triaevum.android;

import java.util.LinkedHashMap;
import java.util.Map;

/** Normalized control centers, independent of screen resolution and density. */
final class TouchLayout {
    private static final String KEYS = "|a|b|x|y|l|r|zl|zr|start|settings|dpad|move|look|visibility|map|";
    private final Map<String, float[]> centers = new LinkedHashMap<>();
    private final Map<String, Float> sizes = new LinkedHashMap<>();
    static final String[] CONTROL_KEYS={"a","b","x","y","l","r","zl","zr","start","settings","dpad","move","look","visibility","map"};
    float size(String key,float fallback) { return sizes.getOrDefault(key,fallback); }
    void setSize(String key,float value) {
        if(KEYS.contains("|"+key+"|")&&Float.isFinite(value))sizes.put(key,Math.max(.5f,Math.min(1.5f,value)));
    }
    static float pinchedSize(float initial,float distance,float initialDistance) {
        if(!Float.isFinite(distance)||!Float.isFinite(initialDistance)||initialDistance<1)return initial;
        return Math.max(.5f,Math.min(1.5f,initial*distance/initialDistance));
    }

    float[] get(String key) { return centers.get(key); }
    void clear() { centers.clear();sizes.clear();for(String key:CONTROL_KEYS)setSize(key,1); }
    void set(String key, float x, float y) {
        if (!KEYS.contains("|" + key + "|") || !Float.isFinite(x) || !Float.isFinite(y)) return;
        centers.put(key, new float[]{Math.max(0, Math.min(1, x)), Math.max(0, Math.min(1, y))});
    }
    /** Swipe velocity in density-independent pixels; a stationary finger produces no camera input. */
    static float dragAxis(float delta, long elapsedMillis, float density) {
        if(!Float.isFinite(delta)||!Float.isFinite(density)||density<=0)return 0;
        float seconds=Math.max(.008f,elapsedMillis/1000f);
        return Math.max(-1,Math.min(1,delta/seconds/(600*density)));
    }
    TouchLayout copy() { return decode(encode()); }
    String encode() {
        StringBuilder out = new StringBuilder("v2");
        for (Map.Entry<String, float[]> entry : centers.entrySet()) {
            float[] p = entry.getValue();
            out.append(';').append(entry.getKey()).append('=').append(p[0]).append(',').append(p[1]);
        }
        for(Map.Entry<String,Float> entry:sizes.entrySet())out.append(";size.").append(entry.getKey()).append("=").append(entry.getValue());
        return out.toString();
    }
    static TouchLayout decode(String value) {
        TouchLayout layout = new TouchLayout();
        if (value == null || value.length() > 4096) return layout;
        String[] fields = value.split(";", -1);
        if (!fields[0].equals("v1")&&!fields[0].equals("v2")) return layout;
        for (int i = 1; i < fields.length; i++) {
            String[] pair = fields[i].split("=", -1);
            if (pair.length != 2) continue;
            if(fields[0].equals("v2")&&pair[0].startsWith("size.")) {
                try {layout.setSize(pair[0].substring(5),Float.parseFloat(pair[1]));}catch(NumberFormatException ignored){}
                continue;
            }
            String[] xy = pair[1].split(",", -1);
            if (xy.length != 2) continue;
            try { layout.set(pair[0], Float.parseFloat(xy[0]), Float.parseFloat(xy[1])); }
            catch (NumberFormatException ignored) { }
        }
        return layout;
    }
}
