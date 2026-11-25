package org.triaevum.android;

import android.app.*;
import android.content.Intent;
import android.os.*;

/** A separate process waits until the previous SDL/title owner is gone. */
public final class RandomizerRestartActivity extends Activity {
    private final Handler handler=new Handler(Looper.getMainLooper());
    private long deadline;
    @Override public void onCreate(Bundle state){super.onCreate(state);deadline=SystemClock.uptimeMillis()+10000;check();}
    private void check() {
        if(isFinishing() || isDestroyed())return;
        int previous=getIntent().getIntExtra("previous-pid",-1);
        if(previous<=0){finish();return;}
        boolean running=false;
        java.util.List<ActivityManager.RunningAppProcessInfo> processes=getSystemService(ActivityManager.class).getRunningAppProcesses();
        if(processes==null)running=true;
        else for(ActivityManager.RunningAppProcessInfo process:processes)
            if(process.pid==previous && process.uid==android.os.Process.myUid())running=true;
        if(!running) {
            startActivity(new Intent(this,RetunedGameActivity.class));finish();
        } else if(SystemClock.uptimeMillis()<deadline)handler.postDelayed(this::check,100);
        else new AlertDialog.Builder(this).setMessage("The previous game is still closing. Close and reopen the app to continue. Your saves are unchanged.")
            .setPositiveButton("OK",(dialog,which)->finish()).show();
    }
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);super.onDestroy();if(isFinishing())android.os.Process.killProcess(android.os.Process.myPid());}
}
