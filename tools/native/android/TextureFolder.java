// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import java.io.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.json.JSONObject;

/** Read-only SAF access. The native index contains metadata and empty image placeholders, not texture copies. */
public final class TextureFolder {
 public static final int REQUEST=4612;
 private final Activity activity;
 private final SharedPreferences preferences;
 private final Map<String,String> documents=new ConcurrentHashMap<>();
 private volatile String selection="",status="";
 private volatile boolean busy=false;
 public TextureFolder(Activity activity){
  this.activity=activity;preferences=activity.getSharedPreferences("texture-folder",0);
  String active=preferences.getString("index","");
  if(!active.isEmpty())try{loadIndex(new File(active));updateStartupConfig(active);}catch(Exception e){status="Choose your texture folder again: "+message(e);}
 }
 private static String message(Exception e){return e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();}
 public void choose(){activity.runOnUiThread(()->{
  if(busy)return;busy=true;status="Choose a texture folder.";
  try{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);activity.startActivityForResult(i,REQUEST);}
  catch(Exception e){busy=false;status="Could not open folder picker: "+message(e);}
 });}
 public String take(){synchronized(this){String result=selection;selection="";return result;}}
 public String status(){return status;}
 public void result(int result,Intent data){
  if(result!=Activity.RESULT_OK||data==null||data.getData()==null){busy=false;status="Folder selection cancelled; your existing textures are unchanged.";return;}
  final Uri tree=data.getData();
  try{activity.getContentResolver().takePersistableUriPermission(tree,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(Exception e){busy=false;status="Could not keep folder permission: "+message(e);return;}
  status="Finding textures in all subfolders...";
  new Thread(()->{
   File index=new File(new File(activity.getFilesDir(),"retuned-texture-links"),UUID.randomUUID().toString());
   try{
    if(!index.mkdirs())throw new IOException("Cannot create texture index");
    Map<String,String> found=new HashMap<>();Set<String> visited=new HashSet<>();
    ArrayDeque<String[]> queue=new ArrayDeque<>();queue.add(new String[]{DocumentsContract.getTreeDocumentId(tree),"","0"});
    int entries=0,images=0;
    while(!queue.isEmpty()){
     String[] dir=queue.remove();if(!visited.add(dir[0]))continue;
     int depth=Integer.parseInt(dir[2]);if(depth>128)throw new IOException("Too many nested folders");
     Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(tree,dir[0]);
     String[] columns={DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE};
     try(Cursor cursor=activity.getContentResolver().query(children,columns,null,null,null)){
      if(cursor==null)throw new IOException("Cannot read the selected folder");
      while(cursor.moveToNext()){
       if(++entries>200000)throw new IOException("Too many files in selected folder");
       String id=cursor.getString(0),name=cursor.getString(1),mime=cursor.getString(2);
       if(name==null||name.isEmpty()||name.equals(".")||name.equals("..")||name.contains("/")||name.contains("\\"))continue;
       String relative=dir[1].isEmpty()?name:dir[1]+"/"+name;
       if(DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)){queue.add(new String[]{id,relative,Integer.toString(depth+1)});continue;}
       String lower=name.toLowerCase(Locale.ROOT);
       if(!(lower.endsWith(".png")||lower.endsWith(".dds")||lower.endsWith(".ktx")||lower.endsWith(".json")))continue;
       Uri uri=DocumentsContract.buildDocumentUriUsingTree(tree,id);File file=new File(index,relative);
       if(!file.getCanonicalPath().startsWith(index.getCanonicalPath()+File.separator))throw new IOException("Invalid texture path");
       if(!file.getParentFile().isDirectory()&&!file.getParentFile().mkdirs())throw new IOException("Cannot index subfolder");
       if(lower.endsWith(".json")){try(FileOutputStream output=new FileOutputStream(file)){output.write(readUri(uri,4*1024*1024));}}
       else{if(!file.createNewFile())throw new IOException("Duplicate texture filename");found.put(file.getAbsolutePath(),uri.toString());images++;}
      }
     }
    }
    if(images==0)throw new IOException("No texture images found in that folder");
    try(FileOutputStream output=new FileOutputStream(new File(index,".document-links"))){output.write(new JSONObject(found).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));}
    documents.putAll(found);preferences.edit().putString("index",index.getAbsolutePath()).putString("tree",tree.toString()).apply();
    synchronized(this){selection=index.getAbsolutePath();}
    status=images+" texture images found. Source files stay in your selected folder.";
   }catch(Exception e){status="Could not use texture folder: "+message(e)+". Existing textures are unchanged.";delete(index);}
   finally{busy=false;}
  },"texture-folder-index").start();
 }
 private byte[] readUri(Uri uri,int limit)throws IOException{
  try(InputStream input=activity.getContentResolver().openInputStream(uri);ByteArrayOutputStream output=new ByteArrayOutputStream()){
   if(input==null)throw new IOException("Cannot read selected texture");byte[] chunk=new byte[65536];int read;
   while((read=input.read(chunk))!=-1){if(output.size()>limit-read)throw new IOException("Texture file is too large");output.write(chunk,0,read);}return output.toByteArray();
  }
 }
 public byte[] read(String path){try{String uri=documents.get(path);if(uri==null)throw new IOException("Folder permission or index is missing");return readUri(Uri.parse(uri),256*1024*1024);}catch(Exception e){status="Texture access failed: "+message(e)+". Choose the folder again.";return null;}}
 private void loadIndex(File index)throws Exception{
  JSONObject links=new JSONObject(new String(java.nio.file.Files.readAllBytes(new File(index,".document-links").toPath()),java.nio.charset.StandardCharsets.UTF_8));
  for(Iterator<String> keys=links.keys();keys.hasNext();){String path=keys.next();documents.put(path,links.getString(path));}
 }
 private void updateStartupConfig(String path)throws Exception{
  File config=new File(activity.getExternalFilesDir(null),"config/native-game.json");if(!config.isFile())return;
  JSONObject root=new JSONObject(new String(java.nio.file.Files.readAllBytes(config.toPath()),java.nio.charset.StandardCharsets.UTF_8));
  JSONObject packs=root.optJSONObject("TexturePacks");if(packs==null){packs=new JSONObject();root.put("TexturePacks",packs);}
  JSONObject azahar=packs.optJSONObject("Azahar");if(azahar==null){azahar=new JSONObject();packs.put("Azahar",azahar);}
  if(path.equals(azahar.optString("LoadDirectory")))return;
  azahar.put("LoadDirectory",path);azahar.put("LoadCustomTextures",true);
  android.util.AtomicFile atomic=new android.util.AtomicFile(config);FileOutputStream output=atomic.startWrite();
  try{output.write(root.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8));atomic.finishWrite(output);}catch(Exception e){atomic.failWrite(output);throw e;}
 }
 private static void delete(File file){File[] children=file.listFiles();if(children!=null)for(File child:children)delete(child);file.delete();}
}
