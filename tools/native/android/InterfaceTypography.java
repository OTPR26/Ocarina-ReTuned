// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.content.Context;
import android.graphics.Typeface;
import android.widget.TextView;

/** Logical sp sizes retain Android's display-density and accessibility scaling. */
final class InterfaceTypography {
    static final int BODY = 15, HEADING = 20, STARTUP = 32;
    private static Typeface body, heading, display;
    private static synchronized void load(Context context) {
        if (body != null) return;
        try {
            body = Typeface.createFromAsset(context.getAssets(), "retuned/FiraSans-Regular.ttf");
            heading = Typeface.createFromAsset(context.getAssets(), "retuned/FiraSansCondensed-Regular.ttf");
            display = Typeface.createFromAsset(context.getAssets(), "retuned/AlegreyaSC-Regular.ttf");
        } catch (RuntimeException missingFont) {
            body = Typeface.create("sans-serif", Typeface.NORMAL);
            heading = Typeface.create("sans-serif-condensed", Typeface.NORMAL);
            display = heading;
        }
    }
    static void body(TextView view) { apply(view, BODY, false, false); }
    static void heading(TextView view) { apply(view, HEADING, true, false); }
    static void button(TextView view, boolean startup) { apply(view, startup ? STARTUP : HEADING, true, false); }
    static void title(TextView view) { apply(view, STARTUP, false, true); }
    private static void apply(TextView view, int size, boolean condensed, boolean decorative) {
        load(view.getContext());
        view.setTypeface(decorative ? display : condensed ? heading : body);
        view.setTextSize(size);
    }
}
