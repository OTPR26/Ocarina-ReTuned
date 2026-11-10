package org.triaevum.android;

import android.content.Context;
import android.content.Intent;
import android.os.*;
import android.util.AtomicFile;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.function.Consumer;

final class GraphicsDriver {
    static final int PICK_REQUEST = 4661;
    private static String loadedId;
    private static boolean restartRequired;
    private static volatile String feedback = "";
    private static String cachedStatus = "";
    private static long statusTime;
    static void choose(android.app.Activity activity) {
        feedback=""; statusTime=0;
        activity.startActivityForResult(new Intent(activity,GraphicsDriverPickerActivity.class),PICK_REQUEST);
    }
    static void result(Intent intent) {
        feedback=intent == null?"":intent.getStringExtra("driver-message"); statusTime=0;
    }
    static void useSystem(Context context) {
        try { select(context,new JSONObject()); feedback="System driver selected."; }
        catch(Exception error) { feedback="Could not save the driver selection."; }
        statusTime=0;
    }
    static boolean needsRestart(Context context) { status(context); return restartRequired; }
    static void restart(android.app.Activity activity) {
        activity.startActivity(new Intent(activity,GraphicsDriverRestartActivity.class).putExtra("previous-pid",android.os.Process.myPid()));
        activity.finish();
    }
    static synchronized String status(Context context) {
        long now=SystemClock.uptimeMillis();
        if(now-statusTime<500 && !cachedStatus.isEmpty())return cachedStatus;
        try {
            JSONObject record=read(context);
            cachedStatus="Selected: "+record.optString("name","System driver");
            restartRequired=loadedId != null && !loadedId.equals(record.optString("id"));
            if(restartRequired)cachedStatus+="\nRestart the app to apply this change.";
            if(feedback != null && !feedback.isEmpty())cachedStatus+="\n"+feedback;
        } catch(Exception error) { cachedStatus="Driver selection is unavailable. Use system driver to recover."; }
        statusTime=now;return cachedStatus;
    }
    static native String initialize(String hooks, String directory, String library);
    static native long[] inspect();
    static File root(Context context) { return new File(context.getFilesDir(), "graphics-drivers"); }
    private static AtomicFile selection(Context context) {
        return new AtomicFile(new File(context.getFilesDir(), "graphics-driver.json"));
    }
    static JSONObject read(Context context) throws Exception {
        AtomicFile file = selection(context);
        if (!file.getBaseFile().exists()) return new JSONObject();
        if (file.getBaseFile().length() > 4096) throw new IOException("Invalid driver selection");
        return new JSONObject(new String(file.readFully(), StandardCharsets.UTF_8));
    }
    static void select(Context context, JSONObject record) throws Exception {
        AtomicFile file = selection(context);
        FileOutputStream output = file.startWrite();
        try { output.write(record.toString().getBytes(StandardCharsets.UTF_8)); file.finishWrite(output); }
        catch (Exception error) { file.failWrite(output); throw error; }
    }
    static String[] paths(Context context, JSONObject record) throws Exception {
        String id = record.optString("id", "");
        if (id.isEmpty()) return new String[]{"", ""};
        String library = record.getString("library");
        if (!id.matches("[0-9a-f]{64}") || !library.matches("[A-Za-z0-9][A-Za-z0-9_.-]*\\.so"))
            throw new IOException("Invalid driver selection");
        File directory = new File(root(context), id);
        File file = new File(directory, library);
        if (!file.isFile() || !file.getCanonicalPath().equals(new File(new File(root(context).getCanonicalFile(), id), library).getPath()))
            throw new IOException("Imported driver is missing or invalid");
        return new String[]{directory.getAbsolutePath(), library};
    }
    static void load(Context context, JSONObject record) throws Exception {
        String[] paths = paths(context, record);
        System.loadLibrary("retuned_vulkan");
        String error = initialize(context.getApplicationInfo().nativeLibraryDir, paths[0], paths[1]);
        if (!error.isEmpty()) throw new IOException(error);
        loadedId=record.optString("id");
    }
    static String name(Context context) {
        try { return read(context).optString("name", "System driver"); }
        catch (Exception error) { return "Invalid driver selection"; }
    }
    static void check(Context context, JSONObject candidate, Consumer<Bundle> done) {
        Handler handler = new Handler(Looper.getMainLooper());
        boolean[] completed = {false}, bound = {false};
        Bundle[] received = {null};
        Messenger[] remote = {null};
        android.content.ServiceConnection[] connection = new android.content.ServiceConnection[1];
        Runnable release = () -> {
            if(bound[0]) { bound[0]=false; context.unbindService(connection[0]); }
        };
        Runnable finish = () -> {
            if (completed[0]) return;
            completed[0] = true; release.run();
            Bundle result = received[0];
            if(result == null) {
                result = new Bundle();
                result.putString("error", "The graphics-driver test stopped or timed out. Select System driver or try a compatible package.");
            }
            done.accept(result);
        };
        Runnable exit = () -> {
            if(remote[0] == null || received[0] == null)return;
            try { remote[0].send(Message.obtain(null, 1)); }
            catch(RemoteException error) { finish.run(); }
        };
        connection[0] = new android.content.ServiceConnection() {
            @Override public void onServiceConnected(android.content.ComponentName name, IBinder service) {
                remote[0]=new Messenger(service); exit.run();
            }
            @Override public void onServiceDisconnected(android.content.ComponentName name) { finish.run(); }
            @Override public void onBindingDied(android.content.ComponentName name) { finish.run(); }
            @Override public void onNullBinding(android.content.ComponentName name) { finish.run(); }
        };
        ResultReceiver receiver = new ResultReceiver(handler) {
            @Override protected void onReceiveResult(int code, Bundle result) {
                if (completed[0]) return;
                received[0]=result; exit.run();
            }
        };
        Intent request = new Intent(context, GraphicsDriverProbeService.class);
        request.putExtra("candidate", candidate.toString()); request.putExtra("receiver", receiver);
        handler.postDelayed(finish, 20000);
        try {
            bound[0] = context.bindService(request, connection[0], Context.BIND_AUTO_CREATE);
            if(!bound[0])finish.run();
        } catch (RuntimeException error) { finish.run(); }
    }
}
