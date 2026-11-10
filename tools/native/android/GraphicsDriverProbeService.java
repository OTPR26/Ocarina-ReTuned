package org.triaevum.android;

import android.app.Service;
import android.content.Intent;
import android.os.*;
import org.json.JSONObject;

/** Driver code runs in a disposable process, without loading the game. */
public final class GraphicsDriverProbeService extends Service {
    private boolean running;
    private final Messenger commands = new Messenger(new Handler(Looper.getMainLooper(), message -> {
        if(message.what == 1)android.os.Process.killProcess(android.os.Process.myPid());
        return true;
    }));
    @Override public IBinder onBind(Intent intent) {
        if (running || intent == null) return commands.getBinder();
        running = true;
        ResultReceiver receiver = intent.getParcelableExtra("receiver");
        Handler handler = new Handler(Looper.getMainLooper());
        handler.postDelayed(() -> android.os.Process.killProcess(android.os.Process.myPid()), 18000);
        new Thread(() -> {
            Bundle result = new Bundle();
            try {
                GraphicsDriver.load(this, new JSONObject(intent.getStringExtra("candidate")));
                long[] values = GraphicsDriver.inspect();
                result.putLongArray("device", values);
            } catch (Exception | LinkageError error) {
                android.util.Log.e("ReTunedDriver", "Driver compatibility check failed", error);
                result.putString("error", "This driver could not initialize a usable Vulkan 1.2 graphics device. Your previous selection is unchanged.");
            }
            if (receiver != null) receiver.send(0, result);

        }, "graphics-driver-check").start();
        return commands.getBinder();
    }
    @Override public void onDestroy() {
        super.onDestroy();
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}
