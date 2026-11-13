package org.triaevum.android;

public final class TouchLayoutCheck {
    static void require(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        require(TouchLayout.dragAxis(0,16,2)==0);
        require(Math.abs(TouchLayout.dragAxis(12,20,2)-.5f)<.0001f);
        require(TouchLayout.dragAxis(12,20,2)==TouchLayout.dragAxis(6,20,1));
        require(TouchLayout.dragAxis(24,40,2)==TouchLayout.dragAxis(12,20,2));
        require(TouchLayout.dragAxis(-1200,1,2)==-1);
        require(TouchLayout.dragAxis(1200,1,2)==1);
        require(TouchLayout.dragAxis(Float.NaN,1,2)==0);
        require(TouchLayout.dragAxis(12,0,0)==0);
        TouchLayout original = new TouchLayout();
        original.set("a", .8f, .6f);
        original.set("dpad", .2f, .3f);
        original.setSize("a", 1.2f);
        TouchLayout draft = original.copy();
        draft.setSize("a", .75f);
        require(original.size("a", 1) == 1.2f);
        require(TouchLayout.decode(draft.encode()).size("a", 1) == .75f);
        require(TouchLayout.decode("v1;a=0.1,0.2").size("a", 1) == 1);
        require(TouchLayout.pinchedSize(1, 150, 100) == 1.5f);
        require(TouchLayout.pinchedSize(1, 10, 100) == .5f);
        require(TouchLayout.pinchedSize(.75f, 100, 0) == .75f);
        require(TouchLayout.pinchedSize(1, Float.NaN, 100) == 1);
        TouchLayout badSize = TouchLayout.decode("v2;size.a=NaN;size.b=Infinity;size.x=9;size.y=-1;size.unknown=1");
        require(badSize.size("a", 1) == 1 && badSize.size("b", 1) == 1);
        require(badSize.size("x", 1) == 1.5f && badSize.size("y", 1) == .5f);
        require(badSize.size("unknown", 0) == 0);
        draft.set("a", .5f, .4f);
        require(original.get("a")[0] == .8f); // Cancel retains saved layout.
        TouchLayout saved = TouchLayout.decode(draft.encode());
        require(saved.get("a")[0] == .5f && saved.get("dpad")[1] == .3f);
        require(saved.get("a")[0] * 1920 == 960 && saved.get("a")[0] * 1280 == 640);
        saved.clear();
        require(saved.size("a", 1.2f) == 1 && saved.size("dpad", .8f) == 1);
        require(saved.get("a") == null && original.get("a") != null);
        TouchLayout invalid = TouchLayout.decode("v1;a=NaN,0.5;b=0.5,Infinity;unknown=0.1,0.2;dpad=bad;map=-2,7");
        require(invalid.get("a") == null && invalid.get("b") == null && invalid.get("unknown") == null);
        require(invalid.get("map")[0] == 0 && invalid.get("map")[1] == 1);
        require(TouchLayout.decode("v3;a=0.1,0.2").get("a") == null);
        require(TouchLayout.decode("x".repeat(4097)).get("a") == null);
        require(TouchLayout.decode(null).get("a") == null);
        java.util.Locale.setDefault(java.util.Locale.FRANCE);
        require(TouchLayout.decode(original.encode()).get("a")[0] == .8f);
        System.out.println("Touch layout persistence, cancellation, resize, reset, malformed input, and locale checks passed");
    }
}
