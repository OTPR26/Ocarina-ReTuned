package org.triaevum.android;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.os.Build;
import java.util.*;

/** Local, deliberately restricted report: no paths, identifiers, saves or exception messages. */
public final class StartupDiagnostics extends Application {
    static android.content.SharedPreferences prefs(Context c) { return c.getSharedPreferences("startup-diagnostics", 0); }
    static synchronized void stage(Context c, String stage) { prefs(c).edit().putString("stage", stage).commit(); }
    static void graphics(Context c, int api, int vendor, int driver) {
        String value = ((api >>> 22) & 127) + "." + ((api >>> 12) & 1023) + "." + (api & 4095)
            + ", vendor=0x" + Integer.toHexString(vendor) + ", driver=0x" + Integer.toHexString(driver);
        prefs(c).edit().putString("runtime_vulkan", value).commit();
    }
    static synchronized void nativeStage(Context c, int code) {
        String[] stages = {"native entry", "loading game module", "game runtime setup", "reading process manifest",
            "loading fonts and UI resources", "allocating guest memory", "guest memory allocated", "creating renderer context",
            "Vulkan instance/device initialization", "Vulkan swapchain/resources", "preparing shaders",
            "starting guest execution", "guest initialization complete", "first frame processing", "native runtime exception"};
        if (code < 0 || code >= stages.length) return;
        String snapshot = "memory unavailable";
        try {
            ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
            c.getSystemService(ActivityManager.class).getMemoryInfo(memory);
            snapshot = "available MiB=" + memory.availMem / 1048576 + ", system lowMemory=" + memory.lowMemory
                + ", process PSS KiB=" + android.os.Debug.getPss()
                + ", native heap MiB=" + android.os.Debug.getNativeHeapAllocatedSize() / 1048576;
        } catch (RuntimeException ignored) { }
        android.content.SharedPreferences p = prefs(c);
        String[] old = p.getString("native_history", "").split("\n");
        StringBuilder history = new StringBuilder();
        for (int i = Math.max(0, old.length - 11); i < old.length; i++)
            if (!old[i].isEmpty()) history.append(old[i]).append('\n');
        history.append(stages[code]).append(": ").append(snapshot);
        android.content.SharedPreferences.Editor edit = p.edit().putString("stage", stages[code])
            .putString("native_stage", stages[code]).putString("native_history", history.toString());
        if (code == 14) edit.putBoolean("pending", true).putString("failure",
            "Native runtime returned an exception.\nLast native stage: " + p.getString("native_stage", "not captured")
                + "\nRuntime Vulkan: " + p.getString("runtime_vulkan", "not captured")
                + "\nStartup checkpoints:\n" + history);
        edit.commit();
    }
    @Override public void onCreate() {
        super.onCreate();
        // ROM preparation has its own process and must not overwrite game startup evidence.
        if (!getPackageName().equals(Application.getProcessName())) return;
        android.content.SharedPreferences p = prefs(this);
        long previous = p.getLong("session", 0);
        String failure = "";
        if (Build.VERSION.SDK_INT >= 30 && previous > 0) {
            try {
                for (ApplicationExitInfo exit : getSystemService(ActivityManager.class).getHistoricalProcessExitReasons(null, 0, 12)) {
                    if (!getPackageName().equals(exit.getProcessName()) || exit.getTimestamp() < previous) continue;
                    int reason = exit.getReason();
                    if (reason == ApplicationExitInfo.REASON_CRASH || reason == ApplicationExitInfo.REASON_CRASH_NATIVE || reason == ApplicationExitInfo.REASON_ANR || reason == ApplicationExitInfo.REASON_INITIALIZATION_FAILURE || reason == ApplicationExitInfo.REASON_LOW_MEMORY) {
                        failure = "Android exit reason=" + reason + " (" + exitName(reason) + "), status=" + exit.getStatus()
                            + "\nLast stage: " + p.getString("stage", "unknown")
                            + "\nLast sampled exit PSS KiB=" + exit.getPss() + ", RSS KiB=" + exit.getRss()
                            + "; these samples are not peak memory."
                            + "\nLast native stage: " + p.getString("native_stage", "not captured")
                            + "\nRuntime Vulkan: " + p.getString("runtime_vulkan", "not captured")
                            + "\nStartup checkpoints:\n" + p.getString("native_history", "not captured");
                        if (reason == ApplicationExitInfo.REASON_CRASH_NATIVE && Build.VERSION.SDK_INT >= 31) {
                            try { failure += "\n" + NativeCrashReport.read(exit.getTraceInputStream()); }
                            catch (java.io.IOException | RuntimeException ignored) { failure += "\nNative trace unavailable."; }
                        }
                    }
                    break;
                }
            } catch (RuntimeException ignored) { }
        }
        // Keep the structural Java trace recorded by the uncaught handler as well as Android's exit reason.
        if (!failure.isEmpty() && p.getLong("java_session", -1) == previous)
            failure += "\n" + p.getString("java_failure", "");
        android.content.SharedPreferences.Editor edit = p.edit().putLong("session", System.currentTimeMillis())
            .remove("native_stage").remove("native_history").remove("runtime_vulkan");
        if (!failure.isEmpty()) edit.putString("failure", failure).putBoolean("pending", true);
        edit.commit();
        Thread.UncaughtExceptionHandler previousHandler = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
            try { failure(this, error); }
            catch (Throwable ignored) { }
            if (previousHandler != null) previousHandler.uncaughtException(thread, error);
            else { android.os.Process.killProcess(android.os.Process.myPid()); System.exit(10); }
        });
    }
    private static String exitName(int reason) {
        switch (reason) {
            case ApplicationExitInfo.REASON_CRASH: return "Java crash";
            case ApplicationExitInfo.REASON_CRASH_NATIVE: return "native crash";
            case ApplicationExitInfo.REASON_ANR: return "not responding";
            case ApplicationExitInfo.REASON_INITIALIZATION_FAILURE: return "initialization failure";
            case ApplicationExitInfo.REASON_LOW_MEMORY: return "low memory";
            default: return "other";
        }
    }
    static void failure(Context c, Throwable error) {
        String detail = "Java failure at " + prefs(c).getString("stage", "unknown") + "\n" + StartupReport.exception(error);
        prefs(c).edit().putString("failure", detail).putString("java_failure", detail).putLong("java_session", prefs(c).getLong("session", 0)).putBoolean("pending", true).commit();
    }
    static boolean recover(Activity a) {
        if (!prefs(a).getBoolean("pending", false)) return false;
        a.startActivity(new Intent(a, StartupDiagnosticsActivity.class)); a.finish(); return true;
    }
    static String report(Context c) {
        String version = "unknown";
        try { version = c.getPackageManager().getPackageInfo(c.getPackageName(), 0).versionName; } catch (PackageManager.NameNotFoundException ignored) { }
        StringBuilder out = new StringBuilder("Ocarina ReTuned startup report\nApp: ").append(version)
            .append("\nDevice: ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
            .append("\nAndroid API: ").append(Build.VERSION.SDK_INT)
            .append("\nABI: ").append(Arrays.toString(Build.SUPPORTED_ABIS));
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo(); c.getSystemService(ActivityManager.class).getMemoryInfo(memory);
        out.append("\nRAM MiB: ").append(memory.totalMem / 1048576).append("; available MiB: ").append(memory.availMem / 1048576);
        for (FeatureInfo feature : c.getPackageManager().getSystemAvailableFeatures()) {
            if ("android.hardware.vulkan.version".equals(feature.name) || "android.hardware.vulkan.level".equals(feature.name)) out.append('\n').append(feature.name).append(": ").append(feature.version);
        }
        out.append("\nVulkan values are system-advertised capabilities, not a driver test.")
            .append("\nROM prepared: ").append(RomSetupActivity.ready(c))
            .append("\nCurrent stage: ").append(prefs(c).getString("stage", "unknown"))
            .append("\nCurrent native stage: ").append(prefs(c).getString("native_stage", "not captured"))
            .append("\nRuntime Vulkan: ").append(prefs(c).getString("runtime_vulkan", "not captured"))
            .append("\nPrevious failure: ").append(prefs(c).getString("failure", "No failure captured. Android 10 cannot report prior native exit reasons."));
        return out.toString();
    }
}
