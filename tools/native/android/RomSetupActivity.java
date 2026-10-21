package org.triaevum.android;

import android.app.Activity;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** First-run only. Prepared installations proceed to the existing native startup. */
public class RomSetupActivity extends Activity {
    private static final int PICK_ROM = 206;
    private TextView message;
    private Button choose, start, cancel;
    private ProgressBar spinner;
    private boolean busy, registered, starting;
    private Typeface regular, bold;
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
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

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size, boolean heading) {
        TextView view = new TextView(this); view.setText(value); view.setTextColor(Color.rgb(239, 243, 250));
        view.setTextSize(size); view.setTypeface(heading ? bold : regular); return view;
    }
    private Button button(String label) {
        Button view = new Button(this); view.setText(label); view.setTextSize(20); view.setAllCaps(false);
        view.setTypeface(regular); view.setTextColor(Color.WHITE); view.setMinHeight(dp(56)); view.setPadding(dp(20), dp(10), dp(20), dp(10));
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
        if (ready(this)) { launchGame(); return; }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        try {
            regular = Typeface.createFromAsset(getAssets(), "retuned/InterfaceSans-Regular.ttf");
            bold = Typeface.createFromAsset(getAssets(), "retuned/InterfaceSans-Bold.ttf");
        } catch (Exception error) { regular = Typeface.create("sans-serif", 0); bold = Typeface.create("sans-serif", 1); }
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.HORIZONTAL); root.setBackgroundColor(Color.BLACK); root.setPadding(dp(24), dp(24), dp(24), dp(24));
        ImageView art = new ImageView(this); art.setScaleType(ImageView.ScaleType.FIT_CENTER);
        try (InputStream input = getAssets().open("retuned/ocarina-illustration.png")) { art.setImageDrawable(android.graphics.drawable.Drawable.createFromStream(input, null)); }
        catch (Exception ignored) { }
        root.addView(art, new LinearLayout.LayoutParams(0, -1, .40f));
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true); root.addView(scroll, new LinearLayout.LayoutParams(0, -1, .60f));
        LinearLayout panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL); panel.setPadding(dp(20), 0, 0, 0); scroll.addView(panel);
        add(panel, text("Ocarina ReTuned", 34, true), 0);
        add(panel, text("First-time setup", 22, false), 12);
        message = text("Choose your clean, decrypted Ocarina of Time 3D USA ROM (.3ds or .cci). Preparation runs entirely on this device. First-time setup can take some time.", 18, false); add(panel, message, 12);
        spinner = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal); spinner.setIndeterminate(true); spinner.setVisibility(View.GONE); add(panel, spinner, 14);
        choose = button("Choose ROM"); choose.setOnClickListener(view -> {
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE);
            picker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            try { startActivityForResult(picker, PICK_ROM); }
            catch (ActivityNotFoundException error) { message.setText("No file picker is available on this device."); }
        }); add(panel, choose, 18);
        start = button("Continue to startup"); start.setVisibility(View.GONE); start.setOnClickListener(view -> launchGame()); add(panel, start, 12);
        cancel = button("Cancel setup"); cancel.setVisibility(View.GONE); cancel.setOnClickListener(view -> requestCancel()); add(panel, cancel, 12);
        add(panel, text("Your original ROM, saves and controller settings will not be replaced.", 15, false), 18);
        setContentView(root); choose.requestFocus();
    }

    private void launchGame() {
        startActivity(new Intent().setClassName(getPackageName(), "org.triaevum.android.RetunedGameActivity")); finish();
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
        spinner.setVisibility(busy ? View.VISIBLE : View.GONE);
        boolean complete = stage.equals("complete") && ready(this);
        start.setVisibility(complete ? View.VISIBLE : View.GONE);
        choose.setVisibility(complete ? View.GONE : View.VISIBLE);
        if (complete) start.requestFocus();
    }
    @Override protected void onActivityResult(int request, int result, Intent intent) {
        super.onActivityResult(request, result, intent);
        if (request != PICK_ROM || result != RESULT_OK || intent == null || intent.getData() == null) return;
        Uri uri = intent.getData();
        try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); }
        catch (SecurityException ignored) { }
        starting = true;
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
        if (starting) return;
        try {
            JSONObject saved = new JSONObject(new String(java.nio.file.Files.readAllBytes(new File(getFilesDir(), "rom-setup-status.json").toPath()), StandardCharsets.UTF_8));
            String stage = saved.getString("stage");
            boolean active = false;
            android.app.ActivityManager manager = getSystemService(android.app.ActivityManager.class);
            for (android.app.ActivityManager.RunningServiceInfo service : manager.getRunningServices(Integer.MAX_VALUE))
                if (RomPreparationService.class.getName().equals(service.service.getClassName())) active = true;
            if (!active && !stage.equals("complete") && !stage.equals("error") && !stage.equals("cancelled"))
                showStatus("error", "The previous setup was interrupted. Choose your ROM again to retry; your saves are unchanged.");
            else showStatus(stage, saved.getString("message"));
        } catch (Exception ignored) { }
    }
    @Override protected void onPause() {
        if (registered) { unregisterReceiver(statusReceiver); registered = false; }
        super.onPause();
    }
    @Override public void onBackPressed() { if (busy) requestCancel(); else super.onBackPressed(); }
}
