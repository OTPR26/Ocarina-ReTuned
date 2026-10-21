    @Override protected String[] getArguments() {
        File profile = new File(getExternalFilesDir(null), "native-launch.json");
        try {
            org.json.JSONArray arguments = new JSONObject(new String(Files.readAllBytes(profile.toPath()), StandardCharsets.UTF_8)).getJSONArray("arguments");
            for (int index = 0; index + 1 < arguments.length(); ++index)
                if ("--title-plugin".equals(arguments.getString(index)))
                    return new String[] {"--launch-profile", profile.getAbsolutePath()};
        } catch (Exception error) { Log.w("ReTunedSetup", "Using legacy module location", error); }
        return new String[] {
            "--launch-profile", profile.getAbsolutePath(),
            "--title-plugin", new File(getFilesDir(), "native/triaevum_title_aot.so").getAbsolutePath()
        };
    }
