// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import java.io.*;
import java.util.*;

/** Only the seven known save filenames are read or changed in a user-granted tree. */
final class SaveDocumentStore {
    final ContentResolver resolver;final Uri tree;
    SaveDocumentStore(Context context,Uri tree){resolver=context.getContentResolver();this.tree=tree;}
    Uri directory(){return DocumentsContract.buildDocumentUriUsingTree(tree,DocumentsContract.getTreeDocumentId(tree));}
    Map<String,Uri> list()throws IOException {
        Map<String,Uri> result=new TreeMap<>();
        String[] columns={DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE};
        try(Cursor c=resolver.query(DocumentsContract.buildChildDocumentsUriUsingTree(tree,DocumentsContract.getTreeDocumentId(tree)),columns,null,null,null)){
            if(c==null)throw new IOException("The selected save folder is unavailable");int count=0;
            while(c.moveToNext()){
                if(++count>256)throw new IOException("Choose a dedicated save folder, not an entire storage volume");
                String name=c.getString(1);if(name==null)continue;
                if(name.contains("sync-conflict")&&(name.startsWith("save0")||name.startsWith("system")))throw new IOException("Resolve the Syncthing conflict files before syncing saves");
                if(!SaveFilesCore.NAMES.contains(name))continue;
                if(DocumentsContract.Document.MIME_TYPE_DIR.equals(c.getString(2)))throw new IOException("A save filename is a folder");
                if(result.put(name,DocumentsContract.buildDocumentUriUsingTree(tree,c.getString(0)))!=null)throw new IOException("Duplicate save filename in folder");
            }
        }catch(SecurityException e){throw new IOException("Save folder permission was lost. Choose the folder again.",e);}return result;
    }
    Map<String,byte[]> read()throws IOException {
        Map<String,byte[]> result=new TreeMap<>();for(Map.Entry<String,Uri> e:list().entrySet())try(InputStream input=resolver.openInputStream(e.getValue())){SaveFilesCore.add(result,e.getKey(),SaveFilesCore.read(input,SaveFilesCore.size(e.getKey())));}return result;
    }
    void probe()throws IOException {
        Uri probe=null;
        try{probe=DocumentsContract.createDocument(resolver,directory(),"application/octet-stream",".retuned-write-check-"+UUID.randomUUID());if(probe==null)throw new IOException("Folder is not writable");try(OutputStream out=resolver.openOutputStream(probe,"wt")){if(out==null)throw new IOException("Folder is not writable");out.write(1);}
            probe=rename(probe,".retuned-write-check-renamed-"+UUID.randomUUID());}
        finally{if(probe!=null)try{DocumentsContract.deleteDocument(resolver,probe);}catch(Exception ignored){}}
    }
    private Uri rename(Uri file,String name)throws IOException {
        Uri result=DocumentsContract.renameDocument(resolver,file,name);if(result==null)throw new IOException("This folder provider cannot safely replace save files. Choose a local Documents folder.");return result;
    }
    private void requireName(Uri file,String name)throws IOException {
        try(Cursor c=resolver.query(file,new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null)){if(c==null||!c.moveToFirst()||!name.equals(c.getString(0)))throw new IOException("Folder provider changed the requested filename");}
    }
    /** Stage every file before changing originals, check for external edits, then retain originals until completion. */
    void publish(Map<String,byte[]> outgoing,String expected)throws IOException {
        if(outgoing.isEmpty())return;
        Map<String,byte[]> before=read();if(!SaveFilesCore.mayPublish(expected,before,outgoing))throw new IOException("Save conflict: the selected folder changed during play. Return to startup to choose which saves to keep.");
        if(SaveFilesCore.digest(before).equals(SaveFilesCore.digest(outgoing)))return;
        Map<String,Uri> original=list(),staged=new TreeMap<>(),backups=new TreeMap<>(),installed=new TreeMap<>();String token=UUID.randomUUID().toString();boolean complete=false;
        try {
            for(Map.Entry<String,byte[]> e:outgoing.entrySet()){
                Uri file=DocumentsContract.createDocument(resolver,directory(),"application/octet-stream",".retuned-stage-"+token+"-"+e.getKey());if(file==null)throw new IOException("Cannot create a save in this folder");staged.put(e.getKey(),file);
                try(OutputStream out=resolver.openOutputStream(file,"wt")){if(out==null)throw new IOException("Cannot write a save in this folder");out.write(e.getValue());}
                try(InputStream in=resolver.openInputStream(file)){if(!Arrays.equals(e.getValue(),SaveFilesCore.read(in,e.getValue().length)))throw new IOException("Save write verification failed");}
            }
            if(!SaveFilesCore.digest(read()).equals(SaveFilesCore.digest(before)))throw new IOException("Save folder changed during sync. Existing saves were left untouched.");
            for(String name:outgoing.keySet()){
                if(original.containsKey(name)){
                    backups.put(name,rename(original.get(name),".retuned-backup-"+token+"-"+name));
                    try(InputStream in=resolver.openInputStream(backups.get(name))){if(!Arrays.equals(before.get(name),SaveFilesCore.read(in,SaveFilesCore.size(name))))throw new IOException("Save changed while publishing; recovering original files");}
                }
                if(list().containsKey(name))throw new IOException("A save appeared during publishing; existing files were preserved");
                Uri ready=rename(staged.get(name),name);staged.remove(name);installed.put(name,ready);requireName(ready,name);
            }
            Map<String,byte[]> written=read();for(Map.Entry<String,byte[]> e:outgoing.entrySet())if(!Arrays.equals(e.getValue(),written.get(e.getKey())))throw new IOException("Save folder changed before sync verification completed");
            complete=true;
        }catch(Exception error){
            // Do not delete someone else's later edit while rolling back.
            for(Map.Entry<String,Uri> e:installed.entrySet())try(InputStream in=resolver.openInputStream(e.getValue())){
                if(!Arrays.equals(outgoing.get(e.getKey()),SaveFilesCore.read(in,outgoing.get(e.getKey()).length)))throw new IOException("Save changed during recovery");
                DocumentsContract.deleteDocument(resolver,e.getValue());
            }catch(Exception ignored){}
            for(Map.Entry<String,Uri> e:backups.entrySet())try{if(!list().containsKey(e.getKey()))rename(e.getValue(),e.getKey());}catch(Exception ignored){}
            throw new IOException("Save folder update failed. App saves are preserved; recovery copies may remain in the selected folder. "+(error.getMessage()==null?"":error.getMessage()),error);
        }finally{
            for(Uri file:staged.values())try{DocumentsContract.deleteDocument(resolver,file);}catch(Exception ignored){}
            if(complete)for(Uri file:backups.values())try{DocumentsContract.deleteDocument(resolver,file);}catch(Exception ignored){}
        }
    }
}
