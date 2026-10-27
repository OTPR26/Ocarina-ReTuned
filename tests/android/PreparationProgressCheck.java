package org.triaevum.android;

public final class PreparationProgressCheck {
    private static void check(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        check(PreparationProgress.position("tools", -1, -1) == 0);
        check(PreparationProgress.position("compiling", 33, 66) == 650);
        check(PreparationProgress.position("compiling", 99, 66) == 700);
        check(PreparationProgress.position("complete", -1, -1) == PreparationProgress.MAX);
        check(PreparationProgress.position("error", -1, -1) == -1);
        check(PreparationProgress.step("compiling").equals("Step 7 of 9"));
        check(PreparationProgress.remaining(30000, 3, 9, -1) == 60000);
        check(PreparationProgress.remaining(5000, 1, 9, -1) == -1);
        check(PreparationProgress.remaining(30000, -1, -1, 120000) == 90000);
        check(PreparationProgress.remaining(120001, -1, -1, 120000) == -1);
        check(PreparationProgress.remaining(30000, 9, 9, -1) == 0);
        check(PreparationProgress.duration(125000).equals("2 min 5 sec"));
        check(PreparationProgress.estimate(-1).contains("Calculating"));
        check(PreparationProgress.estimate(120000).contains("left in this step"));
    }
}
