package org.triaevum.android;

import android.app.Activity;
import android.content.Intent;
import android.system.Os;
import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import org.json.*;

/** One-use handoff; native-launch.json always remains the normal game profile. */
final class RandomizerSession {
    private static String[] arguments;
    private static boolean resolved;
    private static boolean queued;
    private static File root(Activity activity) { return new File(activity.getFilesDir(), "randomizer"); }
    private static AtomicFile pending(Activity activity) { return new AtomicFile(new File(root(activity), "next-launch.json")); }

    static synchronized boolean queue(Activity activity,String encoded,int slot,boolean newGame) {
        if(queued || slot < -1 || slot > 2 || encoded.length()>65536)return false;
        try {
            JSONArray args=new JSONArray(encoded);
            validate(args);
            if(!root(activity).isDirectory() && !root(activity).mkdirs())return false;
            JSONObject request=new JSONObject().put("arguments",args).put("slot",slot).put("newGame",newGame);
            AtomicFile file=pending(activity);
            FileOutputStream stream=file.startWrite();
            try{stream.write(request.toString().getBytes(StandardCharsets.UTF_8));file.finishWrite(stream);}
            catch(Exception error){file.failWrite(stream);throw error;}
            queued=true;
            activity.runOnUiThread(()->{
                try {
                    activity.startActivity(new Intent(activity,RandomizerRestartActivity.class)
                        .putExtra("previous-pid",android.os.Process.myPid()));
                    activity.finish();
                } catch(Exception error) {
                    synchronized(RandomizerSession.class){queued=false;pending(activity).delete();}
                    android.util.Log.e("ReTunedRandomizer","Could not restart game",error);
                }
            });
            return true;
        } catch(Exception error){return false;}
    }
    static void validate(JSONArray args) throws JSONException {
        if(args.length()==0 || args.length()>128)throw new JSONException("Invalid game arguments");
        for(int i=0;i<args.length();i++) {
            String arg=args.getString(i);
            if(arg.length()>8192 || arg.indexOf('\0')>=0)throw new JSONException("Invalid game argument");
        }
    }
    static synchronized String[] arguments(Activity activity) {
        if(resolved)return arguments;
        resolved=true;
        try {
            for(String name:new String[]{"RETUNED_RANDOMIZER_ACTIVE_SLOT","RETUNED_RANDOMIZER_NEW_GAME",
                    "RETUNED_RANDOMIZER_CONTINUE","RETUNED_RANDOMIZER_START_NORMAL","RETUNED_RANDOMIZER_LAUNCHER"})Os.unsetenv(name);
            File config=new File(root(activity),"runtime.json");
            if(config.isFile())Os.setenv("RETUNED_RANDOMIZER_LAUNCHER",config.getAbsolutePath(),true);
            AtomicFile pending=pending(activity);
            if(!pending.getBaseFile().isFile() && !new File(pending.getBaseFile().getPath()+".bak").isFile())return null;
            if(pending.getBaseFile().length()>65536)throw new IOException("Invalid randomizer handoff size");
            JSONObject request=new JSONObject(new String(pending.readFully(),StandardCharsets.UTF_8));
            JSONArray args=request.getJSONArray("arguments");validate(args);
            int slot=request.getInt("slot");
            if(slot < -1 || slot > 2)throw new IOException("Invalid randomizer slot");
            String[] values=new String[args.length()];
            for(int i=0;i<values.length;i++)values[i]=args.getString(i);
            if(slot>=0) {
                Os.setenv("RETUNED_RANDOMIZER_ACTIVE_SLOT",Integer.toString(slot),true);
                Os.setenv(request.getBoolean("newGame")?"RETUNED_RANDOMIZER_NEW_GAME":"RETUNED_RANDOMIZER_CONTINUE","1",true);
            } else Os.setenv("RETUNED_RANDOMIZER_START_NORMAL","1",true);
            pending.delete();arguments=values;return arguments;
        } catch(Exception error) {
            pending(activity).delete();
            // Do not silently launch a different game/save after a failed handoff.
            throw new IllegalStateException("Could not resume the selected randomizer run",error);
        }
    }
}
