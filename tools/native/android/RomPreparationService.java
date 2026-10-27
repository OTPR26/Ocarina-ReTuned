package org.triaevum.android;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.provider.OpenableColumns;
import android.util.AtomicFile;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

/** Runs in :preparation, so Python/compiler memory is released before gameplay. */
public final class RomPreparationService extends Service {
    static final String STATUS = "org.triaevum.android.ROM_SETUP_STATUS";
    static final String CANCEL = "cancel";
    private final AtomicBoolean running = new AtomicBoolean();
    private final AtomicBoolean cancelRequested = new AtomicBoolean();
    private PowerManager.WakeLock wakeLock;
    private File cancelFile;
    private long startedAt, stageStartedAt;
    private String currentStage = "";
    private PendingIntent pending;
    private final java.util.Map<String, Long> previousDurations = new java.util.HashMap<>();
    private final Handler lifecycle = new Handler(Looper.getMainLooper());
    private final Runnable shutdown = () -> { if (!running.get()) android.os.Process.killProcess(android.os.Process.myPid()); };

    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent, int flags, int id) {
        if (intent != null && CANCEL.equals(intent.getAction())) {
            cancelRequested.set(true);
            try { if (cancelFile != null) new FileOutputStream(cancelFile).close(); }
            catch (IOException error) { progress("error", "Could not cancel setup. Please keep the app open."); }
            if (!running.get()) stopSelf();
            return START_NOT_STICKY;
        }
        lifecycle.removeCallbacks(shutdown);
        if (!running.compareAndSet(false, true)) return START_NOT_STICKY;
        cancelRequested.set(false);
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel("rom-setup", "ROM preparation", NotificationManager.IMPORTANCE_LOW));
        Intent open = new Intent().setClassName(getPackageName(), "org.triaevum.android.TriAevumActivity").addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        pending = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        startForeground(204, new Notification.Builder(this, "rom-setup")
            .setSmallIcon(android.R.drawable.stat_sys_download).setContentTitle("Ocarina ReTuned")
            .setContentText("Preparing your ROM on this device").setContentIntent(pending)
            .setOngoing(true).setProgress(0, 0, true).build());
        PowerManager power = getSystemService(PowerManager.class);
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, getPackageName() + ":rom-setup");
        wakeLock.acquire(6 * 60 * 60 * 1000L);
        final String selected = intent == null ? null : intent.getStringExtra("uri");
        startedAt = stageStartedAt = System.currentTimeMillis();
        try {
            File timings = new File(getFilesDir(), "native-data/setup-timings.json");
            JSONObject previous = new JSONObject(new String(java.nio.file.Files.readAllBytes(timings.toPath()), StandardCharsets.UTF_8));
            if ("complete".equals(previous.optString("outcome"))) {
                org.json.JSONArray stages = previous.getJSONArray("stages");
                for (int i = 0; i < stages.length(); i++) {
                    JSONObject stage = stages.getJSONObject(i);
                    previousDurations.merge(stage.getString("stage"), Math.round(stage.getDouble("seconds") * 1000), Long::sum);
                }
            }
        } catch (Exception ignored) { }
        final boolean reuseInputs = intent != null && intent.getBooleanExtra("reuse-inputs", false);
        new Thread(() -> prepare(selected, reuseInputs), "retuned-rom-setup").start();
        return START_NOT_STICKY;
    }

    public void progress(String stage, String message) {
        progressDetailed(stage, message, -1, -1);
    }

    public synchronized void progressDetailed(String stage, String message, long completed, long total) {
        long now = System.currentTimeMillis();
        if (!stage.equals(currentStage)) {
            if (PreparationProgress.index(currentStage) >= 0 && !stage.equals("error") && !stage.equals("cancelled"))
                getSharedPreferences("preparation-timings", MODE_PRIVATE).edit().putLong(currentStage, now - stageStartedAt).apply();
            currentStage = stage; stageStartedAt = now;
        }
        long previous = getSharedPreferences("preparation-timings", MODE_PRIVATE)
            .getLong(stage, previousDurations.getOrDefault(stage, -1L));
        try {
            JSONObject status = new JSONObject().put("stage", stage).put("message", message)
                .put("completed", completed).put("total", total).put("started_at", startedAt)
                .put("stage_started_at", stageStartedAt).put("previous_duration", previous).put("updated_at", now);
            AtomicFile file = new AtomicFile(new File(getFilesDir(), "rom-setup-status.json"));
            FileOutputStream output = file.startWrite();
            try { output.write(status.toString().getBytes(StandardCharsets.UTF_8)); file.finishWrite(output); }
            catch (Exception error) { file.failWrite(output); throw error; }
            sendBroadcast(new Intent(STATUS).setPackage(getPackageName()).putExtra("stage", stage)
                .putExtra("message", message).putExtra("progress", status.toString()));
            int position = PreparationProgress.position(stage, completed, total);
            if (running.get() && position >= 0) getSystemService(NotificationManager.class).notify(204,
                new Notification.Builder(this, "rom-setup").setSmallIcon(android.R.drawable.stat_sys_download)
                    .setContentTitle("Ocarina ReTuned · " + PreparationProgress.step(stage))
                    .setContentText(message).setContentIntent(pending).setOngoing(!stage.equals("complete"))
                    .setProgress(PreparationProgress.MAX, position, false).build());
        } catch (Exception error) { android.util.Log.e("ReTunedSetup", "Could not save setup status", error); }
    }

    private void prepare(String selected, boolean reuseInputs) {
        File input = new File(getFilesDir(), ".rom-input-" + UUID.randomUUID() + ".cci");
        File internal = new File(getFilesDir(), "native-data");
        try {
            if (selected == null && !reuseInputs) throw new IOException("Choose your ROM to begin setup.");
            File userdata = getExternalFilesDir(null);
            if (userdata == null) throw new IOException("App data storage is unavailable.");
            if (!internal.isDirectory() && !internal.mkdirs()) throw new IOException("Cannot create game data directory.");
            // This is the only preparation service process and no worker is
            // active before this job. Remove only its reserved interrupted work,
            // never immutable installations or the external save/settings tree.
            File[] partials = internal.listFiles((directory, name) -> name.startsWith(".rom-setup-"));
            if (partials != null) for (File partial : partials) PreparationKit.deleteTree(partial);
            new File(internal, ".rom-setup.lock").delete();
            cancelFile = new File(internal, "cancel-request"); cancelFile.delete();
            if (cancelRequested.get()) new FileOutputStream(cancelFile).close();
            progress("tools", "Preparing the local setup tools...");
            File kit = PreparationKit.install(this);
            if (cancelFile.exists()) { progress("cancelled", "Setup cancelled. Your ROM and saves are unchanged."); return; }
            if (reuseInputs) {
                if (new StatFs(getFilesDir().getPath()).getAvailableBytes() < 1610612736L)
                    throw new IOException("Not enough free storage to update the prepared game. Free about 2 GB and try again.");
            } else {
                Uri uri = Uri.parse(selected);
                long size = -1;
                try (Cursor cursor = getContentResolver().query(uri, new String[] {OpenableColumns.SIZE}, null, null, null)) {
                    if (cursor != null && cursor.moveToFirst() && !cursor.isNull(0)) size = cursor.getLong(0);
                }
                long required = 1610612736L + (size > 0 ? size : 1073741824L);
                if (new StatFs(getFilesDir().getPath()).getAvailableBytes() < required)
                    throw new IOException("Not enough free storage for setup. Free about 3 GB and try again.");
                progress("copying", "Reading your ROM. The original file will not be changed...");
                try (InputStream source = getContentResolver().openInputStream(uri); FileOutputStream output = new FileOutputStream(input)) {
                    if (source == null) throw new IOException("The ROM could not be opened.");
                    byte[] block = new byte[1024 * 1024]; int count; long total = 0, lastReport = 0;
                    while ((count = source.read(block)) != -1) {
                        if (cancelFile.exists()) { progress("cancelled", "Setup cancelled. Your ROM and saves are unchanged."); return; }
                        total += count;
                        if (total > 4294967296L) throw new IOException("This file is too large to be a supported ROM.");
                        output.write(block, 0, count);
                        long now = System.currentTimeMillis();
                        if (now - lastReport >= 500) {
                            progressDetailed("copying", "Reading your ROM…", total, size); lastReport = now;
                        }
                    }
                    output.getFD().sync();
                    progressDetailed("copying", "ROM read complete.", total, total);
                }
            }
            if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
            Python.getInstance().getModule("retuned_setup_entry").callAttr("prepare",
                kit.getAbsolutePath(), getApplicationInfo().nativeLibraryDir, reuseInputs ? "" : input.getAbsolutePath(),
                internal.getAbsolutePath(), userdata.getAbsolutePath(), cancelFile.getAbsolutePath(), PreparationUpdate.expected(this), this);
        } catch (Exception error) {
            android.util.Log.e("ReTunedSetup", "Local preparation failed", error);
            progress("error", error.getMessage() == null ? "Setup could not finish. Please choose your ROM and try again." : error.getMessage());
        } finally {
            input.delete();
            if (selected != null) {
                try { getContentResolver().releasePersistableUriPermission(Uri.parse(selected), Intent.FLAG_GRANT_READ_URI_PERMISSION); }
                catch (SecurityException ignored) { }
            }
            lifecycle.post(() -> {
                running.set(false);
                if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
                stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
                lifecycle.postDelayed(shutdown, 300);
            });
        }
    }

    @Override public void onTimeout(int startId, int foregroundServiceType) {
        progress("error", "Setup took too long. Your ROM and saves are unchanged; please retry.");
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}
