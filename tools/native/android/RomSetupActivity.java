package org.triaevum.android;

import android.app.Activity;
import android.content.*;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** ROM preparation for first launch and the General settings action. */
public class RomSetupActivity extends Activity {
    private static final int PICK_ROM = 206;
    private TextView message;
    private Button choose, update, start, cancel;
    private ProgressBar spinner;
    private TextView progressDetails;
    private JSONObject latestProgress;
    private long requestedAt;
    private final Handler progressClock = new Handler(Looper.getMainLooper());
    private final Runnable updateClock = new Runnable() {
        @Override public void run() {
            if (busy) restoreProgress();
            updateProgressDetails();
            progressClock.removeCallbacks(this);
            if (busy) progressClock.postDelayed(this, 1000);
        }
    };
    private boolean busy, registered, starting, ignorePreviousStatus;
    private boolean requiredUpdate, automaticUpdate, pendingAutomaticUpdate, handingOff;
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            try { latestProgress = new JSONObject(intent.getStringExtra("progress")); }
            catch (Exception ignored) { latestProgress = null; }
            showStatus(intent.getStringExtra("stage"), intent.getStringExtra("message"));
        }
    };

    static boolean ready(Context context) {
        File root = context.getExternalFilesDir(null);
        if (root == null) return false;
        try {
            JSONObject profile = new JSONObject(new String(java.nio.file.Files.readAllBytes(new File(root, "native-launch.json").toPath()), StandardCharsets.UTF_8));
            JSONArray args = profile.getJSONArray("arguments");
            File manifest = null, module = null;
            for (int index = 0; index + 1 < args.length(); ++index) {
                if ("--a32-process-manifest".equals(args.getString(index))) manifest = new File(args.getString(index + 1));
                if ("--title-plugin".equals(args.getString(index))) module = new File(args.getString(index + 1));
            }
            if (module == null) module = new File(context.getFilesDir(), "native/triaevum_title_aot.so");
            return manifest != null && manifest.isFile() && module.isFile();
        } catch (Exception error) { return false; }
    }

    private boolean hasLocalInputs() {
        File[] entries = new File(getFilesDir(), "native-data/verified-inputs").listFiles();
        if (entries != null) for (File entry : entries)
            if (entry.getName().matches("[0-9a-f]{64}") && new File(entry, "receipt.json").isFile()) return true;
        return false;
    }

    private boolean preparationRunning() {
        android.app.ActivityManager manager = getSystemService(android.app.ActivityManager.class);
        for (android.app.ActivityManager.RunningServiceInfo service : manager.getRunningServices(Integer.MAX_VALUE))
            if (RomPreparationService.class.getName().equals(service.service.getClassName())) return true;
        return false;
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size, boolean heading) {
        TextView view = new TextView(this); view.setText(value); view.setTextColor(Color.rgb(239, 243, 250));
        if (heading) InterfaceTypography.title(view);
        else if (size >= 20) InterfaceTypography.heading(view);
        else InterfaceTypography.body(view);
        return view;
    }
    private Button button(String label) {
        Button view = new Button(this); view.setText(label); InterfaceTypography.button(view, false); view.setAllCaps(false);
        view.setTextColor(Color.WHITE); view.setMinHeight(dp(44)); view.setMinimumHeight(dp(44)); view.setPadding(dp(16), dp(8), dp(16), dp(8));
        android.content.res.ColorStateList colors = new android.content.res.ColorStateList(
            new int[][] {{android.R.attr.state_pressed}, {android.R.attr.state_focused}, {}},
            new int[] {Color.rgb(35, 83, 137), Color.rgb(35, 83, 137), Color.rgb(17, 38, 66)});
        GradientDrawable shape = new GradientDrawable(); shape.setCornerRadius(dp(12)); shape.setColor(colors);
        view.setBackground(shape); view.setFocusable(true); return view;
    }
    private void add(LinearLayout parent, View view, int top) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2); params.topMargin = dp(top); parent.addView(view, params);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (StartupDiagnostics.recover(this)) return;
        StartupDiagnostics.stage(this, "launcher / checking prepared ROM");
        boolean updating = ready(this);
        boolean requested = getIntent().getBooleanExtra("reprepare-rom", false);
        boolean running = preparationRunning();
        if (!requested && !running && GameSession.resume(this)) return;
        String checkError = null;
        if (updating || hasLocalInputs()) {
            try { requiredUpdate = !updating || !PreparationUpdate.current(this); }
            catch (Exception error) { requiredUpdate = true; checkError = "The preparation manifest is incomplete. Install the complete app package and try again."; }
        }
        if (updating && !requested && !running && !requiredUpdate) { launchGame(); return; }
        automaticUpdate = requiredUpdate && !requested;
        pendingAutomaticUpdate = automaticUpdate && !running && state == null && checkError == null && hasLocalInputs();
        ignorePreviousStatus = !running && (requested || requiredUpdate);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.HORIZONTAL); root.setBackgroundColor(Color.BLACK); root.setPadding(dp(24), dp(24), dp(24), dp(24));
        ImageView art = new ImageView(this); art.setScaleType(ImageView.ScaleType.FIT_CENTER);
        art.setScaleX(.5f); art.setScaleY(.5f);
        try (InputStream input = getAssets().open("retuned/ocarina-illustration.png")) { art.setImageDrawable(android.graphics.drawable.Drawable.createFromStream(input, null)); }
        catch (Exception ignored) { }
        boolean narrow = getResources().getConfiguration().screenWidthDp < 600;
        if (!narrow) root.addView(art, new LinearLayout.LayoutParams(0, -1, .40f));
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true); root.addView(scroll, new LinearLayout.LayoutParams(0, -1, .60f));
        LinearLayout panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL); panel.setPadding(dp(20), 0, 0, 0); scroll.addView(panel);
        add(panel, text("Ocarina ReTuned", 34, true), 0);
        add(panel, text(updating || requiredUpdate ? "Game preparation" : "First-time setup", 22, false), 12);
        message = text("Choose your clean, decrypted Ocarina of Time 3D USA ROM (.3ds or .cci). Preparation runs entirely on this device. First-time setup can take some time.", 18, false); add(panel, message, 12);
        if (updating || requiredUpdate) message.setText(hasLocalInputs()
            ? "Apply the latest game fixes using the game inputs already on this device. Your saves, textures, and settings are preserved."
            : "This upgrade needs your ROM once to update the prepared game. Your saves, textures, and settings are preserved.");
        if (checkError != null) message.setText(checkError);
        spinner = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal); spinner.setProgressTintList(android.content.res.ColorStateList.valueOf(Color.rgb(111, 168, 255))); spinner.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.rgb(28, 44, 66))); spinner.setMax(PreparationProgress.MAX); spinner.setIndeterminate(false); spinner.setMinimumHeight(dp(12)); spinner.setVisibility(View.GONE); add(panel, spinner, 14);
        progressDetails = text("", 17, false); progressDetails.setVisibility(View.GONE); add(panel, progressDetails, 8);
        update = button("Update prepared game");
        update.setVisibility(hasLocalInputs() ? View.VISIBLE : View.GONE);
        update.setOnClickListener(view -> beginUpdate());
        add(panel, update, 18);
        choose = button("Choose ROM"); choose.setOnClickListener(view -> {
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE);
            picker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            try { startActivityForResult(picker, PICK_ROM); }
            catch (ActivityNotFoundException error) { message.setText("No file picker is available on this device."); }
        }); add(panel, choose, 18);
        start = button(updating ? "Back to startup" : "Continue to startup"); start.setVisibility(updating && !requiredUpdate ? View.VISIBLE : View.GONE); start.setOnClickListener(view -> launchGame()); add(panel, start, 12);
        cancel = button("Cancel setup"); cancel.setVisibility(View.GONE); cancel.setOnClickListener(view -> requestCancel()); add(panel, cancel, 12);
        Button saves = button("Manage save files"); saves.setOnClickListener(view -> { if(!busy)SaveFiles.open(this); }); add(panel, saves, 12);
        add(panel, text("Your original ROM, saves, and controller settings will not be replaced.", 15, false), 18);
        Button diagnostics = button("Startup diagnostics"); diagnostics.setOnClickListener(view -> startActivity(new Intent(this, StartupDiagnosticsActivity.class))); add(panel, diagnostics, 12);
        setContentView(root); choose.requestFocus();
        StartupDiagnostics.stage(this, "ROM chooser ready");
    }

    private void beginUpdate() {
        ignorePreviousStatus = false; latestProgress = null; starting = true;
        requestedAt = System.currentTimeMillis();
        progressDetails.setVisibility(View.GONE); spinner.setProgress(0);
        showStatus("starting", "Updating from the verified game inputs on this device…");
        startForegroundService(new Intent(this, RomPreparationService.class).putExtra("reuse-inputs", true));
    }
    private boolean canLaunch() {
        if (!ready(this)) return false;
        if (!requiredUpdate) return true;
        try { return PreparationUpdate.current(this); } catch (Exception error) { return false; }
    }
    private void launchGame() {
        if (handingOff) return;
        handingOff = true;
        StartupDiagnostics.stage(this, "reconciling saves before game launch");
        SaveFiles.launch(this);
    }
    private void requestCancel() {
        startService(new Intent(this, RomPreparationService.class).setAction(RomPreparationService.CANCEL));
        message.setText("Cancelling after the current preparation stage..."); cancel.setEnabled(false);
    }
    private void showStatus(String stage, String value) {
        if (message == null || stage == null) return;
        if (!stage.equals("starting")) starting = false;
        busy = !(stage.equals("complete") || stage.equals("error") || stage.equals("cancelled"));
        message.setText(value); choose.setEnabled(!busy); cancel.setVisibility(busy ? View.VISIBLE : View.GONE); cancel.setEnabled(true);
        spinner.setVisibility(busy || stage.equals("complete") ? View.VISIBLE : View.GONE);
        int position = PreparationProgress.position(stage, latestProgress == null ? -1 : latestProgress.optLong("completed", -1),
            latestProgress == null ? -1 : latestProgress.optLong("total", -1));
        if (position >= 0) spinner.setProgress(position);
        updateProgressDetails();
        progressClock.removeCallbacks(updateClock);
        if (busy) progressClock.postDelayed(updateClock, 1000);
        boolean complete = stage.equals("complete") && ready(this);
        start.setVisibility(!busy && canLaunch() ? View.VISIBLE : View.GONE);
        update.setVisibility(!busy && hasLocalInputs() ? View.VISIBLE : View.GONE);
        choose.setVisibility(busy ? View.GONE : View.VISIBLE);
        choose.setText(complete ? "Prepare ROM again" : "Choose ROM");
        if (complete && automaticUpdate && canLaunch()) launchGame();
        if (complete) start.requestFocus();
    }
    private void updateProgressDetails() {
        if (progressDetails == null || latestProgress == null) return;
        long now = System.currentTimeMillis();
        long started = latestProgress.optLong("started_at", now);
        long elapsed = Math.max(0, (busy ? now : latestProgress.optLong("updated_at", now)) - started);
        String stage = latestProgress.optString("stage");
        String step = PreparationProgress.step(stage);
        String detail = step;
        if (latestProgress.has("started_at"))
            detail += (detail.isEmpty() ? "" : " · ") + "Elapsed " + PreparationProgress.duration(elapsed);
        if (busy) {
            long remaining = PreparationProgress.remaining(Math.max(0, now - latestProgress.optLong("stage_started_at", now)),
                latestProgress.optLong("completed", -1), latestProgress.optLong("total", -1), latestProgress.optLong("previous_duration", -1));
            detail += "\n" + PreparationProgress.estimate(remaining);
        }
        progressDetails.setText(detail); progressDetails.setVisibility(View.VISIBLE);
    }

    @Override protected void onActivityResult(int request, int result, Intent intent) {
        super.onActivityResult(request, result, intent);
        if (request != PICK_ROM || result != RESULT_OK || intent == null || intent.getData() == null) return;
        Uri uri = intent.getData();
        try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); }
        catch (SecurityException ignored) { }
        ignorePreviousStatus = false;
        latestProgress = null;
        progressDetails.setVisibility(View.GONE);
        spinner.setProgress(0);
        starting = true;
        requestedAt = System.currentTimeMillis();
        showStatus("starting", "Preparing your ROM on this device...");
        startForegroundService(new Intent(this, RomPreparationService.class).putExtra("uri", uri.toString()));
    }
    @Override protected void onResume() {
        super.onResume();
        if (message == null) return;
        IntentFilter filter = new IntentFilter(RomPreparationService.STATUS);
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(statusReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(statusReceiver, filter);
        registered = true;
        if (pendingAutomaticUpdate) { pendingAutomaticUpdate = false; beginUpdate(); return; }
        if (ignorePreviousStatus) return;
        restoreProgress();
        progressClock.removeCallbacks(updateClock);
        if (busy) progressClock.postDelayed(updateClock, 1000);
    }
    private void restoreProgress() {
        try {
            JSONObject saved = new JSONObject(new String(java.nio.file.Files.readAllBytes(new File(getFilesDir(), "rom-setup-status.json").toPath()), StandardCharsets.UTF_8));
            if (saved.optLong("started_at", 0) < requestedAt) return;
            latestProgress = saved;
            String stage = saved.getString("stage");
            boolean active = preparationRunning();
            if (!active && !stage.equals("complete") && !stage.equals("error") && !stage.equals("cancelled"))
                showStatus("error", "The previous setup was interrupted. Choose your ROM again to retry; your saves are unchanged.");
            else showStatus(stage, saved.getString("message"));
        } catch (Exception ignored) { }
    }
    @Override protected void onPause() {
        progressClock.removeCallbacks(updateClock);
        if (registered) { unregisterReceiver(statusReceiver); registered = false; }
        super.onPause();
    }
    @Override public void onBackPressed() { if (busy) requestCancel(); else if (canLaunch()) launchGame(); else super.onBackPressed(); }
}
