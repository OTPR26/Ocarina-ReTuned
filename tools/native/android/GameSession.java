// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.app.Activity;
import android.content.Intent;
import java.lang.ref.WeakReference;

/** Reopening the launcher resumes the existing SDL owner. */
final class GameSession {
    private static WeakReference<Activity> active = new WeakReference<>(null);
    static void attach(Activity game) { active = new WeakReference<>(game); }
    static void detach(Activity game) { if (active.get() == game) active.clear(); }
    static boolean resume(Activity launcher) {
        Activity game = active.get();
        if (game == null || game.isFinishing() || game.isDestroyed()) return false;
        launcher.startActivity(new Intent(launcher, game.getClass())
            .addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT | Intent.FLAG_ACTIVITY_SINGLE_TOP));
        launcher.finish();
        return true;
    }
}
