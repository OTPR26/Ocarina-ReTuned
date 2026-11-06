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
        String nativeError = StartupReport.nativeException("vkCreateDevice failed with VkResult -8 /private/ROM.3ds owner@example.test");
        if (!nativeError.equals("vkCreateDevice failed with VkResult -8")) throw new AssertionError(nativeError);
        if (!StartupReport.nativeException("private-user GPU; TriAevum needs Vulkan 1.2 or newer").contains("requires Vulkan 1.2")) throw new AssertionError("missing API reason");
        for (String message : new String[]{"owner@example.test /private/ROM.3ds", "", null,
                "x".repeat(3000) + "vkCreateDevice failed with VkResult -8"}) {
            String safe = StartupReport.nativeException(message);
            if (!safe.equals("Unclassified native exception; message omitted.")) throw new AssertionError(safe);
        }
        String loader = StartupReport.exception(new UnsatisfiedLinkError(
            "dlopen failed: cannot locate symbol \"__aarch64_ldadd4_acq_rel\" referenced by /private/person/secret.so"));
        if (!loader.contains("Missing native symbol: __aarch64_ldadd4_acq_rel") || loader.contains("/private") || loader.contains("secret.so")) throw new AssertionError(loader);
        String library = StartupReport.exception(new UnsatisfiedLinkError("dlopen failed: library \"libc++_shared.so\" not found in /private/person"));
        if (!library.contains("Missing native library: libc++_shared.so") || library.contains("/private")) throw new AssertionError(library);
        String unknown = StartupReport.exception(new UnsatisfiedLinkError("dlopen failed: library \"private-person.so\" not found"));
        if (unknown.contains("private-person")) throw new AssertionError(unknown);
        System.out.println("PASS structural trace, cause chain, privacy exclusions and bounds");
    }
}
