package org.triaevum.android;

public final class TouchLayoutCheck {
    static void require(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        TouchLayout original = new TouchLayout();
        original.set("a", .8f, .6f);
        original.set("dpad", .2f, .3f);
        TouchLayout draft = original.copy();
        draft.set("a", .5f, .4f);
        require(original.get("a")[0] == .8f); // Cancel retains saved layout.
        TouchLayout saved = TouchLayout.decode(draft.encode());
        require(saved.get("a")[0] == .5f && saved.get("dpad")[1] == .3f);
        require(saved.get("a")[0] * 1920 == 960 && saved.get("a")[0] * 1280 == 640);
        saved.clear();
        require(saved.get("a") == null && original.get("a") != null);
        TouchLayout invalid = TouchLayout.decode("v1;a=NaN,0.5;b=0.5,Infinity;unknown=0.1,0.2;dpad=bad;map=-2,7");
        require(invalid.get("a") == null && invalid.get("b") == null && invalid.get("unknown") == null);
        require(invalid.get("map")[0] == 0 && invalid.get("map")[1] == 1);
        require(TouchLayout.decode("v2;a=0.1,0.2").get("a") == null);
        require(TouchLayout.decode("x".repeat(4097)).get("a") == null);
        require(TouchLayout.decode(null).get("a") == null);
        java.util.Locale.setDefault(java.util.Locale.FRANCE);
        require(TouchLayout.decode(original.encode()).get("a")[0] == .8f);
        System.out.println("Touch layout persistence, cancellation, resize, reset, malformed input, and locale checks passed");
    }
}
