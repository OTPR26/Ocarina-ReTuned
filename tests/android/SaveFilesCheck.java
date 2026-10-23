// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;
import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.provider.DocumentsContract;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public final class SaveFilesCheck extends Instrumentation {
    private Bundle options;
    @Override public void onCreate(Bundle args){options=args;super.onCreate(args);start();}
    interface Checked{void run()throws Exception;}
    static void require(boolean value){if(!value)throw new AssertionError();}
    static void rejects(Checked task)throws Exception{try{task.run();throw new AssertionError("Expected save operation failure");}catch(IOException expected){}}
    static Map<String,byte[]> saves(int value)throws Exception{Map<String,byte[]> m=new TreeMap<>();byte[] a=new byte[5340],b=new byte[34];Arrays.fill(a,(byte)value);Arrays.fill(b,(byte)value);SaveFilesCore.add(m,"save00.bin",a);SaveFilesCore.add(m,"system.dat",b);return m;}
    static void setExternal(Map<String,byte[]> files)throws Exception{for(Map.Entry<String,byte[]> e:files.entrySet())Files.write(new File(SaveTestProvider.root,e.getKey()).toPath(),e.getValue());}
    public void onStart(){Bundle result=new Bundle();try{
        Context c=getTargetContext();
        if(options!=null&&options.containsKey("picker-tree")){
            Uri chosen=Uri.parse(options.getString("picker-tree"));
            Activity activity=startActivitySync(new Intent(c,SaveFilesActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("return-to-caller",true));
            runOnMainSync(()->activity.startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).putExtra(DocumentsContract.EXTRA_INITIAL_URI,DocumentsContract.buildDocumentUriUsingTree(chosen,DocumentsContract.getTreeDocumentId(chosen))).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION),4622));
            Bundle ready=new Bundle();ready.putString("stream","Real folder picker ready\n");sendStatus(1,ready);
            long until=System.currentTimeMillis()+55000;while(SaveFiles.folder(c)==null&&System.currentTimeMillis()<until)Thread.sleep(100);
            require(SaveFiles.folder(c)!=null);require(DocumentsContract.getTreeDocumentId(SaveFiles.folder(c)).equals(DocumentsContract.getTreeDocumentId(chosen)));
            result.putString("stream","Real picker grant, folder selection, and initial ordinary-file publishing PASS\n");finish(Activity.RESULT_OK,result);return;
        }
        if(options!=null&&options.containsKey("shared-check")){
            Uri shared=SaveFiles.folder(c);require(shared!=null&&shared.getAuthority().equals("com.android.externalstorage.documents")&&(DocumentsContract.getTreeDocumentId(shared).startsWith("primary:Documents/ReTuned-Save-Transfer-Test-")||DocumentsContract.getTreeDocumentId(shared).startsWith("primary:ReTuned-Save-Transfer-Test-")));
            SaveDocumentStore store=new SaveDocumentStore(c,shared);SaveFiles.prepare(c);SaveFilesCore.install(SaveFiles.root(c),saves(3));SaveFiles.committed(c);SaveFiles.WORK.submit(()->{}).get(15,java.util.concurrent.TimeUnit.SECONDS);
            require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(saves(3))));
            store.publish(saves(4),SaveFilesCore.digest(saves(3)));SaveFiles.prepare(c);require(SaveFilesCore.digest(SaveFilesCore.local(SaveFiles.root(c))).equals(SaveFilesCore.digest(saves(4))));
            result.putString("stream","Persisted real-folder permission across restart, native-commit bridge, and external-folder pull PASS\n");finish(Activity.RESULT_OK,result);return;
        }
        Uri tree=DocumentsContract.buildTreeDocumentUri("io.github.otpr26.savefilestest.documents","root");SaveDocumentStore store=new SaveDocumentStore(c,tree);store.probe();
        for(File f:SaveTestProvider.root.listFiles())f.delete();
        Map<String,byte[]> empty=new TreeMap<>(),one=saves(1),two=saves(2),three=saves(3),four=saves(4);
        store.publish(one,SaveFilesCore.digest(empty));require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(one)));
        store.publish(two,SaveFilesCore.digest(one));require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(two)));
        setExternal(three);rejects(()->store.publish(four,SaveFilesCore.digest(two)));require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(three)));
        SaveTestProvider.renameFailure=2;rejects(()->store.publish(four,SaveFilesCore.digest(three)));require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(three)));
        SaveTestProvider.readOnly=true;rejects(store::probe);SaveTestProvider.readOnly=false;
        SaveFiles.prefs(c).edit().clear().commit();SaveFilesCore.install(SaveFiles.root(c),one);SaveFiles.useFolder(c,tree,false);
        require(SaveFilesCore.digest(SaveFilesCore.local(SaveFiles.root(c))).equals(SaveFilesCore.digest(three)));
        setExternal(four);SaveFiles.prepare(c);require(SaveFilesCore.digest(SaveFilesCore.local(SaveFiles.root(c))).equals(SaveFilesCore.digest(four)));
        SaveFilesCore.install(SaveFiles.root(c),one);SaveFiles.prepare(c);require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(one)));
        SaveFilesCore.install(SaveFiles.root(c),two);setExternal(three);rejects(()->SaveFiles.prepare(c));require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(three)));require(SaveFilesCore.digest(SaveFilesCore.local(SaveFiles.root(c))).equals(SaveFilesCore.digest(two)));
        SaveFiles.useFolder(c,tree,true);require(SaveFilesCore.digest(store.read()).equals(SaveFilesCore.digest(two)));
        SaveTestProvider.denied=true;rejects(()->SaveFiles.prepare(c));SaveTestProvider.denied=false;require(SaveFilesCore.digest(SaveFilesCore.local(SaveFiles.root(c))).equals(SaveFilesCore.digest(two)));
        SaveFiles.prefs(c).edit().clear().commit();
        startActivitySync(new Intent(c,SaveFilesActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("return-to-caller",true));
        result.putString("stream","Document staging, write verification, conflict refusal, partial-rename rollback, read-only/revoked grants, two-way startup/commit reconciliation, and save-manager launch PASS\n");finish(Activity.RESULT_OK,result);
    }catch(Throwable e){result.putString("stream",android.util.Log.getStackTraceString(e));finish(Activity.RESULT_CANCELED,result);}}
}
