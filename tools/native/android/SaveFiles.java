// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.content.*;
import android.net.Uri;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.*;

/** Small immutable snapshots cross the native commit boundary; document I/O runs on one worker. */
public final class SaveFiles {
    static final ExecutorService WORK=Executors.newSingleThreadExecutor(r->new Thread(r,"retuned-save-files"));
    private static volatile String status="";
    static SharedPreferences prefs(Context c){return c.getSharedPreferences("save-files",0);}
    static File root(Context c)throws IOException {
        File base=c.getExternalFilesDir(null);if(base==null)throw new IOException("App save storage is unavailable");
        File root=new File(base,"saves"),profile=new File(base,"native-launch.json");
        if(profile.isFile())try{
            JSONArray args=new JSONObject(new String(Files.readAllBytes(profile.toPath()),StandardCharsets.UTF_8)).getJSONArray("arguments");
            for(int i=0;i+1<args.length();i++)if(args.getString(i).equals("--save-data")){root=new File(args.getString(i+1));break;}
        }catch(JSONException e){throw new IOException("Launch settings are invalid; saves were not changed",e);}
        String path=root.getCanonicalPath(),external=base.getCanonicalPath()+File.separator,internal=c.getFilesDir().getCanonicalPath()+File.separator;
        if(!path.startsWith(external)&&!path.startsWith(internal))throw new IOException("This custom launch profile uses an unsupported save path");return root;
    }
    static Uri folder(Context c){String value=prefs(c).getString("tree","");return value.isEmpty()?null:Uri.parse(value);}
    public static String status(){return status;}
    static void status(String text){status=text;}
    static void baseline(Context c,Map<String,byte[]> files){if(!prefs(c).edit().putString("baseline",SaveFilesCore.digest(files)).commit())throw new IllegalStateException("Could not save folder sync state");}
    static void prepare(Context c)throws IOException {
        Uri tree=folder(c);if(tree==null){status="Using the app save folder.";return;}
        SaveDocumentStore store=new SaveDocumentStore(c,tree);Map<String,byte[]> remote=store.read(),local=SaveFilesCore.local(root(c));
        String base=prefs(c).getString("baseline","");String r=SaveFilesCore.digest(remote),l=SaveFilesCore.digest(local);
        if(r.equals(l)){baseline(c,local);status="Custom save folder is up to date.";return;}
        if(base.isEmpty()||(!r.equals(base)&&!l.equals(base)))throw new IOException("Both app saves and folder saves changed. Open Save files and choose Use folder saves or Keep app saves.");
        if(r.equals(base))store.publish(local,base);
        else {
            if(remote.isEmpty())throw new IOException("The selected folder has no saves. App saves are preserved. Open Save files to choose which copy to keep.");
            SaveFilesCore.install(root(c),remote); // Preserve other local slots; synchronize their merged set as well.
            local=SaveFilesCore.local(root(c));store.publish(local,r);
        }
        baseline(c,local);status="Custom save folder is up to date.";
    }
    public static void committed(Context context){
        Context c=context.getApplicationContext();if(folder(c)==null)return;
        try{
            final Map<String,byte[]> snapshot=SaveFilesCore.local(root(c));
            WORK.execute(()->{try{Uri tree=folder(c);if(tree==null)return;SaveDocumentStore store=new SaveDocumentStore(c,tree);store.publish(snapshot,prefs(c).getString("baseline",""));baseline(c,snapshot);status="Saved to custom folder.";}catch(Exception e){status="Custom folder needs attention: "+message(e)+" App saves are safe.";}});
        }catch(Exception e){status="Could not sync saves: "+message(e);}
    }
    static void useFolder(Context c,Uri tree,boolean keepApp)throws IOException {
        SaveDocumentStore store=new SaveDocumentStore(c,tree);store.probe();Map<String,byte[]> remote=store.read(),local=SaveFilesCore.local(root(c));
        if(!keepApp&&!remote.isEmpty()){SaveFilesCore.install(root(c),remote);local=SaveFilesCore.local(root(c));}
        else if(keepApp){Map<String,byte[]> missing=new TreeMap<>(remote);for(String name:local.keySet())missing.remove(name);if(!missing.isEmpty()){SaveFilesCore.install(root(c),missing);local=SaveFilesCore.local(root(c));}}
        store.publish(local,SaveFilesCore.digest(remote));
        if(!prefs(c).edit().putString("tree",tree.toString()).putString("baseline",SaveFilesCore.digest(local)).commit())throw new IOException("Could not retain save folder selection");
        status="Custom folder selected. Saves load before gameplay and write back after an in-game save.";
    }
    static String message(Exception e){return e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();}
    public static void open(android.app.Activity activity){open(activity,"");}
    public static void open(android.app.Activity activity,String action){activity.runOnUiThread(()->activity.startActivity(new Intent(activity,SaveFilesActivity.class).putExtra("return-to-caller",true).putExtra("action",action)));}
    public static void launch(android.app.Activity activity){activity.startActivity(new Intent(activity,SaveFilesActivity.class).putExtra("launch-game",true));activity.finish();}
}
