package org.triaevum.android;

import android.app.Activity;
import android.app.ProgressDialog;
import android.content.Intent;
import android.os.Bundle;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.*;

/** A transparent bridge keeps Python and driver checks outside the game process. */
public final class GraphicsDriverPickerActivity extends Activity {
    private static final int PICK = 4660;
    private ProgressDialog progress;
    private boolean busy;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if(state != null) {
            if(state.getBoolean("importing",false))complete("Driver import was interrupted. Your previous driver is unchanged.",false);
            return;
        }
        if (!new File("/dev/kgsl-3d0").exists()) {
            complete("Custom Adreno drivers are unavailable on this device. They do not support Mali GPUs.",false); return;
        }
        try { startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*")
            .addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION), PICK); }
        catch (RuntimeException error) { complete("No file browser is available.",false); }
    }
    private void complete(String message, boolean success) {
        if(isDestroyed())return;
        if(progress != null)progress.dismiss();
        setResult(success?RESULT_OK:RESULT_CANCELED,new Intent().putExtra("driver-message",message));
        finish();
    }
    @Override protected void onActivityResult(int request,int result,Intent intent) {
        super.onActivityResult(request,result,intent);
        if(request!=PICK)return;
        if(result!=RESULT_OK || intent==null || intent.getData()==null) { complete("",false); return; }
        busy=true;
        progress=ProgressDialog.show(this,"Graphics driver","Checking driver package…",true,false);
        new Thread(() -> {
            File input = null;
            try {
                input = File.createTempFile("graphics-driver-", ".zip",getCacheDir());
                try(InputStream source=getContentResolver().openInputStream(intent.getData()); OutputStream output=new FileOutputStream(input)) {
                    if(source==null)throw new IOException("Unavailable file");
                    byte[] block=new byte[65536]; int count; long size=0;
                    while((count=source.read(block))!=-1) {
                        size+=count; if(size>128L*1024*1024)throw new IOException("Driver package exceeds 128 MiB");
                        output.write(block,0,count);
                    }
                }
                if(!Python.isStarted())Python.start(new AndroidPlatform(getApplicationContext()));
                String recordText=Python.getInstance().getModule("driver_package").callAttr("install_json",input.getAbsolutePath(),GraphicsDriver.root(this).getAbsolutePath(),android.os.Build.VERSION.SDK_INT).toString();
                JSONObject record=new JSONObject(recordText);
                runOnUiThread(() -> {
                    if(isDestroyed())return;
                    progress.setMessage("Checking Vulkan compatibility…");
                    GraphicsDriver.check(this,record,checked -> {
                        if(checked.containsKey("error")){complete(checked.getString("error"),false);return;}
                        try {
                            GraphicsDriver.select(this,record);
                            complete("Driver checked and selected.",true);
                        } catch(Exception error) { complete("Could not save the driver selection. Your previous driver is unchanged.",false); }
                    });
                });
            } catch(Exception error) {
                runOnUiThread(() -> complete("Driver import failed. Choose a compatible ARM64 Adreno driver ZIP with valid meta.json. Your current driver is unchanged.",false));
            } finally { if(input!=null)input.delete(); }
        },"graphics-driver-import").start();
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        state.putBoolean("importing",busy); super.onSaveInstanceState(state);
    }
    @Override public void onBackPressed() { if(!busy)super.onBackPressed(); }
    @Override protected void onDestroy() {
        if(progress != null)progress.dismiss();
        super.onDestroy();
        if(isFinishing())android.os.Process.killProcess(android.os.Process.myPid());
    }
}
