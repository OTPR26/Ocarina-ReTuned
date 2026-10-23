package org.triaevum.android;

/** Bounded structural Java trace; throwable messages and file paths are never exported. */
final class StartupReport {
    static String exception(Throwable error) {
        StringBuilder out = new StringBuilder();
        for (int causes = 0; error != null && causes < 4; causes++, error = error.getCause()) {
            out.append(error.getClass().getName()).append('\n');
            StackTraceElement[] frames = error.getStackTrace();
            for (int i = 0; i < Math.min(frames.length, 12); i++)
                out.append("  ").append(frames[i].getClassName()).append('.').append(frames[i].getMethodName()).append(':').append(frames[i].getLineNumber()).append('\n');
        }
        return out.toString();
    }
}
