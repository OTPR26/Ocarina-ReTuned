// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.widget.*;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.*;
import java.util.ArrayList;
import java.util.List;

/** Runs separately from SDL; activation is available only before gameplay. */
public final class PlayerModelsActivity extends Activity {
    private static final int PICK = 4630;
    private final List<Button> buttons = new ArrayList<>();
    private TextView message;
    private RadioGroup age;
    private Spinner modelMode;
    private TextView importedName;
    private Button importButton;
    private boolean refreshing, currentImported, hasImported;
    private boolean busy;
    private String selectedAge;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true); scroll.setBackgroundColor(Color.rgb(8,14,20));
        LinearLayout panel = new LinearLayout(this); panel.setOrientation(LinearLayout.VERTICAL);
        int padding = Math.round(24 * getResources().getDisplayMetrics().density);
        panel.setPadding(padding,padding,padding,padding); scroll.addView(panel); setContentView(scroll);
        TextView title = new TextView(this); title.setText("Mods — Player appearance");
        title.setTextColor(Color.WHITE); InterfaceTypography.heading(title); panel.addView(title);
        message = new TextView(this); message.setTextColor(Color.WHITE); InterfaceTypography.body(message);
        message.setText("Import an OoT human player-model PAK or ZOBJ for child or adult Link. Scripts, custom animations, and sounds are not imported. Your saves and textures stay unchanged.");
        panel.addView(message);
        age = new RadioGroup(this); age.setOrientation(RadioGroup.HORIZONTAL);
        for(int i=0;i<2;i++) {
            RadioButton choice=new RadioButton(this); choice.setId(i+1); choice.setText(i==0?"Child":"Adult");
            choice.setTextColor(Color.WHITE); InterfaceTypography.body(choice);
            age.addView(choice,new RadioGroup.LayoutParams(0,-2,1));
        }
        age.check(1); panel.addView(age);
        age.setOnCheckedChangeListener((group,id)->refreshSelection());
        TextView label=new TextView(this);label.setText("Player model");label.setTextColor(Color.WHITE);
        InterfaceTypography.body(label);panel.addView(label);
        modelMode=new Spinner(this,Spinner.MODE_DROPDOWN);
        ArrayAdapter<String> models=new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,
                new String[]{"Original Link","PAK Importer"}) {
            private android.view.View style(android.view.View view) {
                TextView text=(TextView)view;text.setTextColor(Color.WHITE);text.setBackgroundColor(Color.rgb(24,34,48));
                InterfaceTypography.body(text);return text;
            }
            @Override public android.view.View getView(int position,android.view.View view,android.view.ViewGroup parent) {
                return style(super.getView(position,view,parent));
            }
            @Override public android.view.View getDropDownView(int position,android.view.View view,android.view.ViewGroup parent) {
                return style(super.getDropDownView(position,view,parent));
            }
        };
        modelMode.setAdapter(models);modelMode.setPopupBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.rgb(24,34,48)));
        panel.addView(modelMode);
        importedName=new TextView(this);importedName.setTextColor(Color.WHITE);InterfaceTypography.body(importedName);panel.addView(importedName);
        importButton=button(panel,"Import PAK file",()->{
            selectedAge=role();
            try { startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*")
                .addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                .putExtra(DocumentsContract.EXTRA_INITIAL_URI,DocumentsContract.buildDocumentUri("com.android.externalstorage.documents","primary:Download")),PICK); }
            catch (RuntimeException error) { message.setText("No file browser is available."); }
        });
        modelMode.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onNothingSelected(AdapterView<?> parent) { }
            @Override public void onItemSelected(AdapterView<?> parent,android.view.View view,int position,long id) {
                if(refreshing||busy)return;
                importButton.setVisibility(position==1?android.view.View.VISIBLE:android.view.View.GONE);
                boolean imported=position==1;
                if(imported==currentImported)return;
                if(imported&&!hasImported) { importedName.setText("No PAK model imported for this age. Choose Import PAK file.");return; }
                run(null,role(),imported);
            }
        });
        button(panel,"Return to Ocarina ReTuned",this::leave);
        refreshSelection();
    }
    private Button button(LinearLayout panel,String label,Runnable action) {
        Button button = new Button(this); button.setText(label); button.setAllCaps(false);
        InterfaceTypography.button(button,false); button.setOnClickListener(v->action.run());
        buttons.add(button); panel.addView(button);return button;
    }
    private void setBusy(boolean value) { busy=value;modelMode.setEnabled(!value); for(int i=0;i<age.getChildCount();i++)age.getChildAt(i).setEnabled(!value); for(Button b:buttons)b.setEnabled(!value); }
    @Override protected void onActivityResult(int request,int result,Intent intent) {
        super.onActivityResult(request,result,intent);
        if(request==PICK && result==RESULT_OK && intent!=null && intent.getData()!=null) run(intent,selectedAge);
    }
    private void run(Intent selection,String role) { run(selection,role,false); }
    private void run(Intent selection,String role,boolean useImported) {
        if(busy)return; setBusy(true); message.setText("Preparing player-model import…");
        new Thread(()->{
            File input = null;
            try (PreparationSession session=PreparationSession.acquire(new File(getFilesDir(),"native-data"))) {
                // No worker using this build can hold a Python transaction now.
                new File(getFilesDir(),"native-data/.rom-setup.lock").delete();
                if(selection!=null) {
                    input = File.createTempFile("player-model-",".pak",getCacheDir());
                    try(InputStream source=getContentResolver().openInputStream(selection.getData()); OutputStream out=new FileOutputStream(input)) {
                        if(source==null)throw new IOException("Cannot open selected model");
                        byte[] block=new byte[65536]; int count; long total=0;
                        while((count=source.read(block))!=-1) {
                            total+=count; if(total>32L*1024*1024)throw new IOException("Model package exceeds 32 MiB");
                            out.write(block,0,count);
                        }
                    }
                }
                File kit = PreparationKit.install(this);
                if(!Python.isStarted())Python.start(new AndroidPlatform(getApplicationContext()));
                File root=getExternalFilesDir(null);
                if(root==null)throw new IOException("Game storage is unavailable");
                Python.getInstance().getModule("retuned_models_entry").callAttr("change",kit.getAbsolutePath(),
                    root.getAbsolutePath(),new File(getFilesDir(),"native-data").getAbsolutePath(),input==null?null:input.getAbsolutePath(),role,useImported);
                runOnUiThread(()->{refreshSelection();message.setText(selection==null?(useImported?"Imported model selected.":"Original Link selected. Your PAK is retained."):"Player model imported. Return to the app to try it.");});
            } catch(Exception error) {
                // Python tracebacks may contain private paths. Keep them out of UI reports.
                runOnUiThread(()->message.setText("Model import could not finish. Choose a supported OoT child/adult human model. Your previous game setup is unchanged."));
            } finally {
                if(input!=null)input.delete();
                runOnUiThread(()->setBusy(false));
            }
        },"retuned-player-model").start();
    }
    private String role() { return age.getCheckedRadioButtonId()==1?"child":"adult"; }
    private org.json.JSONObject readJson(File file,int maximum) throws Exception {
        if(!file.isFile()||file.length()>maximum)throw new IOException("Invalid model settings");
        return new org.json.JSONObject(new String(java.nio.file.Files.readAllBytes(file.toPath()),java.nio.charset.StandardCharsets.UTF_8));
    }
    private void refreshSelection() {
        if(modelMode==null)return;
        refreshing=true;currentImported=false;hasImported=false;String name="No PAK model imported for this age.";
        try {
            File root=getExternalFilesDir(null);
            org.json.JSONArray args=readJson(new File(root,"native-launch.json"),1024*1024).getJSONArray("arguments");
            for(int i=0;i+1<args.length();i++) {
                if(!args.getString(i).equals("--a32-process-manifest"))continue;
                org.json.JSONObject manifest=readJson(new File(args.getString(i+1)),8*1024*1024);
                org.json.JSONObject active=manifest.optJSONObject("player_models");
                org.json.JSONObject available=manifest.optJSONObject("available_player_models");
                if(available==null)available=active;
                currentImported=active!=null&&active.has(role());hasImported=available!=null&&available.has(role());
                if(hasImported) {
                    org.json.JSONObject record=available.getJSONObject(role());name=record.optString("name","");
                    if(name.isEmpty()) {
                        File data=new File(record.getString("converted")).getParentFile();
                        if(!data.getCanonicalPath().startsWith(new File(root,"player-models").getCanonicalPath()+File.separator))throw new IOException("Invalid model settings");
                        name=readJson(new File(data,"import.json"),32768).getJSONObject("conversion").optString("source_name","Imported PAK model");
                    }
                    name="Imported: "+name.substring(0,Math.min(256,name.length()));
                }
                break;
            }
        } catch(Exception error) { name="Model status is unavailable. Return to startup and try again."; }
        modelMode.setSelection(currentImported?1:0);importedName.setText(name);
        importButton.setVisibility(currentImported?android.view.View.VISIBLE:android.view.View.GONE);
        refreshing=false;
    }
    private void leave() { if(busy)return; startActivity(new Intent(this,TriAevumActivity.class)); finish(); }
    @Override public void onBackPressed() { leave(); }
    @Override protected void onDestroy() {
        super.onDestroy();
        if(isFinishing())android.os.Process.killProcess(android.os.Process.myPid());
    }
}
