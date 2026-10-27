package org.triaevum.android;

/** Preparation steps are work milestones, not equal portions of elapsed time. */
public final class PreparationProgress {
    private PreparationProgress() {}
    private static final String[] STAGES = {"checking", "extracting", "normalizing",
        "assets", "patching", "translating", "compiling", "verifying", "activating"};
    public static final int MAX = STAGES.length * 100;
    static int index(String stage) {
        if ("tools".equals(stage) || "copying".equals(stage)) return 0;
        if ("generating".equals(stage)) return 5;
        for (int i = 0; i < STAGES.length; i++) if (STAGES[i].equals(stage)) return i;
        return -1;
    }
    static int position(String stage, long completed, long total) {
        if ("complete".equals(stage)) return MAX;
        int index = index(stage);
        if (index < 0) return -1;
        int fraction = total > 0 ? (int)(100.0 * Math.min(Math.max(0, completed), total) / total) : 0;
        return index * 100 + fraction;
    }
    static String step(String stage) {
        int index = index(stage);
        return index < 0 ? ("complete".equals(stage) ? "Preparation complete" : "")
            : "Step " + (index + 1) + " of " + STAGES.length;
    }
    static long remaining(long elapsed, long completed, long total, long previousDuration) {
        if (total > 0 && completed >= total) return 0;
        if (completed >= 2 && completed < total && elapsed >= 10000)
            return Math.max(0, Math.round((double)elapsed / completed * (total - completed)));
        if (previousDuration > elapsed) return previousDuration - elapsed;
        return -1;
    }
    static String duration(long millis) {
        long seconds = Math.max(0, millis / 1000);
        return seconds < 60 ? seconds + " sec" : (seconds / 60) + " min " + (seconds % 60) + " sec";
    }
    static String estimate(long millis) {
        if (millis < 0) return "Calculating time estimate…";
        if (millis < 60000) return "About a minute or less left in this step";
        long low = Math.max(1, Math.round(millis * .8 / 60000));
        long high = Math.max(low + 1, Math.round(millis * 1.25 / 60000));
        return "About " + low + "–" + high + " min left in this step";
    }
}
