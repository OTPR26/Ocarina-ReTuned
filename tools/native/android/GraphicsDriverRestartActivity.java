package org.triaevum.android;

import android.app.Activity;
import android.app.ActivityManager;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.*;

/** Wait for SDL's owner to exit before starting a fresh driver session. */
public final class GraphicsDriverRestartActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long deadline;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        deadline=SystemClock.uptimeMillis()+10000;
        check();
    }
    private void check() {
        if(isFinishing() || isDestroyed())return;
        int previous=getIntent().getIntExtra("previous-pid",-1);
        boolean running=false;
        java.util.List<ActivityManager.RunningAppProcessInfo> processes=getSystemService(ActivityManager.class).getRunningAppProcesses();
        if(processes!=null)for(ActivityManager.RunningAppProcessInfo process:processes)
            if(process.pid==previous && process.uid==android.os.Process.myUid())running=true;
        if(!running) {
            startActivity(new Intent(this,TriAevumActivity.class).putExtra("graphics-driver-return",true));finish();
        } else if(SystemClock.uptimeMillis()<deadline)handler.postDelayed(this::check,100);
        else new AlertDialog.Builder(this).setMessage("The previous game session has not closed. Close the app before reopening it to apply the driver.")
            .setPositiveButton("OK",(dialog,which)->finish()).show();
    }
    @Override protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);super.onDestroy();
        if(isFinishing())android.os.Process.killProcess(android.os.Process.myPid());
    }
}
