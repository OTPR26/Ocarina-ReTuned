// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;
import android.database.*;
import android.os.*;
import android.provider.*;
import java.io.*;
import java.nio.file.*;

/** Instrumentation-only provider; never packaged in the release app. */
public final class SaveTestProvider extends DocumentsProvider {
    static File root;static volatile boolean denied=false,readOnly=false;static volatile int renameFailure=-1;
    public boolean onCreate(){root=new File(getContext().getFilesDir(),"test-documents");return root.isDirectory()||root.mkdirs();}
    public boolean isChildDocument(String parent,String child){return parent.equals("root")&&!child.equals("root")&&!child.contains("/")&&!child.equals("..");}
    private File file(String id)throws FileNotFoundException{if(denied)throw new SecurityException("Revoked test grant");if(id.equals("root"))return root;if(id.contains("/")||id.equals(".."))throw new FileNotFoundException();return new File(root,id);}
    public Cursor queryRoots(String[] projection){String[] columns={DocumentsContract.Root.COLUMN_ROOT_ID,DocumentsContract.Root.COLUMN_DOCUMENT_ID,DocumentsContract.Root.COLUMN_TITLE,DocumentsContract.Root.COLUMN_FLAGS};MatrixCursor c=new MatrixCursor(columns);c.addRow(new Object[]{"root","root","ReTuned test folder",DocumentsContract.Root.FLAG_SUPPORTS_CREATE});return c;}
    private MatrixCursor cursor(String[] projection){return new MatrixCursor(projection==null?new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_FLAGS}:projection);}
    private void row(MatrixCursor c,File file){MatrixCursor.RowBuilder r=c.newRow();for(String column:c.getColumnNames()){if(column.equals(DocumentsContract.Document.COLUMN_DOCUMENT_ID))r.add(file.equals(root)?"root":file.getName());else if(column.equals(DocumentsContract.Document.COLUMN_DISPLAY_NAME))r.add(file.getName());else if(column.equals(DocumentsContract.Document.COLUMN_MIME_TYPE))r.add(file.isDirectory()?DocumentsContract.Document.MIME_TYPE_DIR:"application/octet-stream");else if(column.equals(DocumentsContract.Document.COLUMN_FLAGS))r.add(DocumentsContract.Document.FLAG_SUPPORTS_WRITE|DocumentsContract.Document.FLAG_SUPPORTS_RENAME|DocumentsContract.Document.FLAG_SUPPORTS_DELETE|DocumentsContract.Document.FLAG_DIR_SUPPORTS_CREATE);else r.add(null);}}
    public Cursor queryDocument(String id,String[] projection)throws FileNotFoundException{MatrixCursor c=cursor(projection);row(c,file(id));return c;}
    public Cursor queryChildDocuments(String parent,String[] projection,String sort)throws FileNotFoundException{File directory=file(parent);MatrixCursor c=cursor(projection);File[] children=directory.listFiles();if(children!=null)for(File f:children)row(c,f);return c;}
    public ParcelFileDescriptor openDocument(String id,String mode,CancellationSignal cancel)throws FileNotFoundException{if(readOnly&&!mode.equals("r"))throw new FileNotFoundException("Read-only test provider");return ParcelFileDescriptor.open(file(id),ParcelFileDescriptor.parseMode(mode));}
    public String createDocument(String parent,String mime,String name)throws FileNotFoundException{if(readOnly)throw new FileNotFoundException("Read only");file(parent);File f=file(name);try{if(!f.createNewFile())throw new IOException("Already exists");return name;}catch(IOException e){throw new FileNotFoundException(e.toString());}}
    public String renameDocument(String id,String name)throws FileNotFoundException{if(renameFailure==0){renameFailure=-1;throw new FileNotFoundException("Injected rename failure");}if(renameFailure>0)--renameFailure;try{Files.move(file(id).toPath(),file(name).toPath());return name;}catch(IOException e){throw new FileNotFoundException(e.toString());}}
    public void deleteDocument(String id)throws FileNotFoundException{if(!file(id).delete())throw new FileNotFoundException("Delete failed");}
}
