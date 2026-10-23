package org.triaevum.android;
public final class StartupReportCheck {
    public static void main(String[] args) {
        RuntimeException cause = new RuntimeException("private-email@example.test /private/ROM.3ds");
        cause.setStackTrace(new StackTraceElement[]{new StackTraceElement("org.example.Loader","load","/private/user/secret.java",42)});
        RuntimeException outer = new RuntimeException("private save path",cause);
        String report = StartupReport.exception(outer);
        if (report.contains("private") || report.contains("example.test") || report.contains("secret.java")) throw new AssertionError(report);
        if (!report.contains("org.example.Loader.load:42") || !report.contains("java.lang.RuntimeException")) throw new AssertionError(report);
        RuntimeException longTrace = new RuntimeException();
        StackTraceElement[] frames = new StackTraceElement[1000];
        java.util.Arrays.fill(frames,new StackTraceElement("test.Loader","load","hidden",1));longTrace.setStackTrace(frames);
        if (StartupReport.exception(longTrace).split("\n").length != 13) throw new AssertionError("unbounded report");
        System.out.println("PASS structural trace, cause chain, privacy exclusions and bounds");
    }
}
