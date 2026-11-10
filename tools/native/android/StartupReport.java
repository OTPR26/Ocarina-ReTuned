package org.triaevum.android;

/** Bounded diagnostics containing structural traces and recognized error fields. */
final class StartupReport {
    static String nativeException(String message) {
        if (message == null) return "Unclassified native exception; message omitted.";
        message = message.substring(0, Math.min(message.length(), 2048));
        java.util.regex.Matcher result = java.util.regex.Pattern.compile(
            "\\b(vk[A-Z][A-Za-z0-9_]{1,80})(?:\\(count\\))? failed with VkResult (-?[0-9]{1,10})\\b").matcher(message);
        if (result.find()) return result.group(1) + " failed with VkResult " + result.group(2);
        if (message.contains("needs Vulkan 1.2") || message.contains("requires Vulkan 1.2"))
            return "The renderer requires Vulkan 1.2 or newer; the candidate device does not meet this requirement.";
        String[] recognized = {
            "native PICA texture exceeds the per-frame upload arena",
            "native PICA texture upload size is invalid",
            "native PICA texture upload region is invalid",
            "no Vulkan physical device is available",
            "no Vulkan adapter supports graphics, presentation and swapchain",
            "Vulkan renderer was paired with a non-Vulkan SDL backend",
            "SDL Vulkan window creation failed",
            "SDL_Vulkan_GetInstanceExtensions failed",
            "SDL_Vulkan_CreateSurface failed",
            "SDL_GetWindowWMInfo failed"
        };
        for (String reason : recognized) if (message.contains(reason)) return reason;
        for (String operation : new String[]{"vkGetPhysicalDeviceFeatures2", "vkGetPhysicalDeviceProperties2"})
            if (message.contains(operation) && message.contains("loader predates Vulkan 1.1"))
                return operation + " is unavailable; the Vulkan loader predates Vulkan 1.1.";
        return "Unclassified native exception; message omitted.";
    }

    private static String loaderFailure(String message) {
        if (message == null) return "";
        message = message.substring(0, Math.min(message.length(), 2048));
        java.util.regex.Matcher symbol = java.util.regex.Pattern.compile(
            "cannot locate symbol [\"']([A-Za-z_][A-Za-z0-9_]{0,127})[\"']").matcher(message);
        if (symbol.find()) return "Missing native symbol: " + symbol.group(1);
        for (String library : new String[]{"libTriAevum.so", "libSDL2.so", "libc++_shared.so",
                "libtriaevum_title_bootstrap.so", "libvulkan.so"})
            if (message.contains("library \"" + library + "\" not found"))
                return "Missing native library: " + library;
        if (message.contains("is not accessible for the namespace")) return "Native library blocked by Android linker namespace.";
        return "";
    }

    static String exception(Throwable error) {
        StringBuilder out = new StringBuilder();
        for (int causes = 0; error != null && causes < 4; causes++, error = error.getCause()) {
            out.append(error.getClass().getName()).append('\n');
            if (error instanceof UnsatisfiedLinkError) {
                String reason = loaderFailure(error.getMessage());
                if (!reason.isEmpty()) out.append(reason).append('\n');
            }
            StackTraceElement[] frames = error.getStackTrace();
            for (int i = 0; i < Math.min(frames.length, 12); i++)
                out.append("  ").append(frames[i].getClassName()).append('.').append(frames[i].getMethodName()).append(':').append(frames[i].getLineNumber()).append('\n');
        }
        return out.toString();
    }
}
