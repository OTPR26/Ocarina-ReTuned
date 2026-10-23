package org.triaevum.android;

import android.app.Activity;
import android.content.*;
import android.os.Bundle;
import android.widget.*;

/** Java-only recovery UI: deliberately does not initialize SDL or the renderer. */
public final class StartupDiagnosticsActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(24,24,24,24);
        TextView title = new TextView(this); title.setText("Ocarina ReTuned diagnostics"); title.setTextSize(24); root.addView(title);
        TextView help = new TextView(this); help.setText("If the app closed unexpectedly, copy this report into your issue. Nothing is sent automatically. Your ROM and saves are unchanged."); root.addView(help);
        String report = StartupDiagnostics.report(this);
        ScrollView scroll = new ScrollView(this); TextView text = new TextView(this); text.setText(report); text.setTextIsSelectable(true); scroll.addView(text); root.addView(scroll, new LinearLayout.LayoutParams(-1,0,1));
        Button copy = new Button(this); copy.setText("Copy report"); copy.setOnClickListener(v -> { getSystemService(ClipboardManager.class).setPrimaryClip(ClipData.newPlainText("Startup report", report)); Toast.makeText(this,"Report copied",Toast.LENGTH_SHORT).show(); }); root.addView(copy);
        Button retry = new Button(this); retry.setText("Continue to app"); retry.setOnClickListener(v -> { StartupDiagnostics.prefs(this).edit().putBoolean("pending",false).commit(); startActivity(new Intent(this,TriAevumActivity.class)); finish(); }); root.addView(retry);
        setContentView(root);
    }
}
