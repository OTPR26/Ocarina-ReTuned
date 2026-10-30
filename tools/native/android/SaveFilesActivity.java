// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.os.*;
import android.provider.OpenableColumns;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.util.*;

/** Available before gameplay; file replacement never happens in a running guest session. */
public final class SaveFilesActivity extends Activity {
    private static final int IMPORT=4620,EXPORT=4621,FOLDER=4622;
    private long generation=0;private boolean busy=false;private TextView message;private final List<Button> buttons=new ArrayList<>(),customButtons=new ArrayList<>();
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable refresh=new Runnable(){public void run(){if(message!=null)message.setText(SaveFiles.status());for(Button b:customButtons)b.setVisibility(SaveFiles.folder(SaveFilesActivity.this)==null?View.GONE:View.VISIBLE);handler.postDelayed(this,500);}};
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    @Override public void onCreate(Bundle state){
        super.onCreate(state);ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setFitsSystemWindows(true);scroll.setBackgroundColor(Color.rgb(8,14,20));
        LinearLayout panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);panel.setPadding(dp(28),dp(24),dp(28),dp(24));scroll.addView(panel);
        text(panel,"Ocarina ReTuned — Save files",22);
        text(panel,"Import Citra/Azahar in-game saves, or export a ZIP. Save states are separate.",17);
        text(panel,"For Syncthing, choose a folder such as Documents/ReTuned Saves. Changes load when you reopen the app; new in-game saves copy back automatically. Play on one synced device at a time.",17);
        message=text(panel,"",16);
        button(panel,"Import saves",()->picker(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION),IMPORT));
        button(panel,"Export saves",()->picker(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"Ocarina-ReTuned-Saves.zip"),EXPORT));
        button(panel,"Choose custom save folder",()->picker(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).putExtra(Intent.EXTRA_LOCAL_ONLY,true).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION),FOLDER));
        button(panel,"Use folder saves",()->resolve(false));customButtons.add(buttons.get(buttons.size()-1));
        button(panel,"Keep app saves",()->resolve(true));customButtons.add(buttons.get(buttons.size()-1));
        button(panel,"Use app save folder",()->{
            if(SaveFiles.folder(this)==null){SaveFiles.status("Using the app save folder.");return;}
            new AlertDialog.Builder(this).setTitle("Stop using the custom folder?").setMessage("Current app saves remain available. Files in the selected folder will not be deleted.").setNegativeButton("Cancel",null).setPositiveButton("Use app folder",(d,w)->work("Disconnecting custom folder...",()->{if(!SaveFiles.prefs(this).edit().remove("tree").remove("baseline").commit())throw new IOException("Could not save folder setting");SaveFiles.status("Using the app save folder. Custom folder files were kept.");})).show();
        });
        customButtons.add(buttons.get(buttons.size()-1));
        button(panel,"Startup diagnostics",()->startActivity(new Intent(this,StartupDiagnosticsActivity.class)));
        button(panel,getIntent().getBooleanExtra("return-to-caller",false)?"Done":"Continue to startup",this::prepareAndLaunch);
        setContentView(scroll);
        SaveFiles.status(SaveFiles.folder(this)==null?"Using the app save folder.":"A custom save folder is selected. Folder access uses Android's document permission.");
        if(state==null&&getIntent().getBooleanExtra("launch-game",false))prepareAndLaunch();
        else if(state==null){String action=getIntent().getStringExtra("action");int index="import".equals(action)?0:"export".equals(action)?1:"folder".equals(action)?2:-1;if(index>=0)handler.post(()->buttons.get(index).performClick());}
    }
    private TextView text(LinearLayout parent,String value,int size){TextView v=new TextView(this);v.setText(value);if(size>=20)InterfaceTypography.heading(v);else InterfaceTypography.body(v);v.setTextColor(Color.WHITE);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(14);parent.addView(v,p);return v;}
    private void button(LinearLayout parent,String name,Runnable action){Button b=new Button(this);b.setText(name);b.setAllCaps(false);b.setTextColor(Color.WHITE);InterfaceTypography.button(b,false);
        android.graphics.drawable.GradientDrawable shape=new android.graphics.drawable.GradientDrawable();shape.setCornerRadius(dp(10));shape.setColor(new android.content.res.ColorStateList(new int[][]{{android.R.attr.state_pressed},{android.R.attr.state_focused},{}},new int[]{Color.rgb(35,83,137),Color.rgb(35,83,137),Color.rgb(17,38,66)}));b.setBackground(shape);
        b.setMinHeight(dp(52));b.setOnClickListener(v->action.run());LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(8);parent.addView(b,p);buttons.add(b);}
    private void busy(boolean value){busy=value;for(Button b:buttons)b.setEnabled(!value);}
    private interface Task {void run()throws Exception;}
    private void work(String status,Task task){final long token=++generation;busy(true);SaveFiles.status(status);SaveFiles.WORK.execute(()->{try{task.run();}catch(Exception e){SaveFiles.status("Save operation failed: "+SaveFiles.message(e)+" Existing saves were preserved unless an import already completed.");}finally{runOnUiThread(()->{if(generation==token)busy(false);});}});}
    private void picker(Intent intent,int request){try{startActivityForResult(intent,request);}catch(Exception e){SaveFiles.status("Could not open the file picker: "+SaveFiles.message(e));}}
    private void prepareAndLaunch(){work("Checking save folder...",()->{SaveFiles.prepare(this);runOnUiThread(()->{if(!getIntent().getBooleanExtra("return-to-caller",false))startActivity(new Intent().setClassName(getPackageName(),"org.triaevum.android.RetunedGameActivity"));finish();});});}
    private void resolve(boolean app){Uri tree=SaveFiles.folder(this);if(tree==null){SaveFiles.status("Choose a custom save folder first.");return;}
        new AlertDialog.Builder(this).setTitle(app?"Keep app saves?":"Use folder saves?")
            .setMessage(app?"Matching save files in the selected folder will be replaced with the app's copies.":"Matching app save files will be replaced with the selected folder's copies. A local recovery copy is kept.")
            .setNegativeButton("Cancel",null).setPositiveButton("Continue",(d,w)->work("Updating save copies...",()->SaveFiles.useFolder(this,tree,app))).show();
    }
    private String name(Uri uri)throws IOException {
        try(Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){if(c!=null&&c.moveToFirst()&&!c.isNull(0))return c.getString(0);}throw new IOException("Cannot read selected filename");
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null){SaveFiles.status("Selection cancelled. Saves are unchanged.");return;}
        if(request==IMPORT){
            List<Uri> uris=new ArrayList<>();if(data.getClipData()!=null){for(int i=0;i<data.getClipData().getItemCount();i++)uris.add(data.getClipData().getItemAt(i).getUri());}else if(data.getData()!=null)uris.add(data.getData());
            work("Reading selected saves...",()->{
                if(uris.isEmpty()||uris.size()>7)throw new IOException("Select up to seven save files, or one ZIP");Map<String,byte[]> files=new TreeMap<>();
                for(Uri uri:uris){String name=name(uri);try(InputStream in=getContentResolver().openInputStream(uri)){
                    if(name.toLowerCase(Locale.ROOT).endsWith(".zip")){if(uris.size()!=1)throw new IOException("Select one ZIP without other files");files.putAll(SaveFilesCore.readZip(in));}
                    else SaveFilesCore.add(files,name,SaveFilesCore.read(in,Math.max(0,SaveFilesCore.size(name))));
                }}
                runOnUiThread(()->new AlertDialog.Builder(this).setTitle("Import "+files.size()+" save files?").setMessage("Matching app saves will be replaced. Other slots are kept, and the previous save folder is retained as a local recovery copy.")
                    .setNegativeButton("Cancel",(d,w)->SaveFiles.status("Import cancelled. Saves are unchanged."))
                    .setPositiveButton("Import",(d,w)->work("Importing saves...",()->{SaveFilesCore.install(SaveFiles.root(this),files);SaveFiles.status("Saves imported. Continue to startup to load them.");SaveFiles.committed(this);})).show());
            });
        }else if(request==EXPORT&&data.getData()!=null){Uri uri=data.getData();work("Exporting saves...",()->{Map<String,byte[]> files=SaveFilesCore.local(SaveFiles.root(this));if(files.isEmpty())throw new IOException("No in-game saves to export yet");try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")){if(out==null)throw new IOException("Cannot write selected ZIP");SaveFilesCore.writeZip(files,out);}SaveFiles.status("Save ZIP exported. It contains ordinary in-game save files.");});
        }else if(request==FOLDER&&data.getData()!=null){Uri tree=data.getData();
            try{int flags=data.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);if(flags!=(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION))throw new IOException("Choose a writable local folder");getContentResolver().takePersistableUriPermission(tree,flags);}catch(Exception e){SaveFiles.status("Could not retain folder permission: "+SaveFiles.message(e));return;}
            work("Checking the selected folder...",()->{SaveDocumentStore store=new SaveDocumentStore(this,tree);store.probe();Map<String,byte[]> remote=store.read(),local=SaveFilesCore.local(SaveFiles.root(this));
                if(remote.isEmpty()||SaveFilesCore.digest(remote).equals(SaveFilesCore.digest(local))){SaveFiles.useFolder(this,tree,true);return;}
                runOnUiThread(()->new AlertDialog.Builder(this).setTitle("This folder already has saves").setMessage("Choose which copies to keep for matching save files. Other slots are preserved.")
                    .setNegativeButton("Cancel",(d,w)->SaveFiles.status("Folder selection cancelled. Previous selection is unchanged."))
                    .setNeutralButton("Keep app saves",(d,w)->work("Selecting save folder...",()->SaveFiles.useFolder(this,tree,true)))
                    .setPositiveButton("Use folder saves",(d,w)->work("Selecting save folder...",()->SaveFiles.useFolder(this,tree,false))).show());
            });
        }
    }
    @Override protected void onResume(){super.onResume();handler.post(refresh);}
    @Override protected void onPause(){handler.removeCallbacks(refresh);super.onPause();}
    @Override public void onBackPressed(){if(!busy)super.onBackPressed();}
}
