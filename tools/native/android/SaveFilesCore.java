// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

/** Save-format and local transaction code shared by Android and JVM tests. */
public final class SaveFilesCore {
    private SaveFilesCore() {}
    public static final List<String> NAMES=Collections.unmodifiableList(Arrays.asList(
        "save00.bin","save01.bin","save02.bin","save03.bin","save04.bin","save05.bin","system.dat"));
    public static int size(String name) { return name.equals("system.dat") ? 34 : NAMES.contains(name) ? 5340 : -1; }
    public static byte[] read(InputStream input, int limit) throws IOException {
        if(input==null)throw new IOException("Cannot open save file");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] block=new byte[4096];int n;
        while((n=input.read(block))!=-1){if(n>limit-bytes.size())throw new IOException("Save file is too large");bytes.write(block,0,n);}return bytes.toByteArray();
    }
    public static void add(Map<String,byte[]> files,String name,byte[] bytes)throws IOException {
        if(size(name)<0)throw new IOException("Choose save00.bin–save05.bin, system.dat, or a save ZIP");
        if(bytes.length!=size(name))throw new IOException("Invalid size for "+name+". Use expanded Ocarina of Time 3D in-game saves, not save states.");
        if(files.putIfAbsent(name,bytes.clone())!=null)throw new IOException("Duplicate save filename: "+name);
    }
    public static Map<String,byte[]> readZip(InputStream input)throws IOException {
        Map<String,byte[]> files=new TreeMap<>();
        try(ZipInputStream zip=new ZipInputStream(input)) {
            ZipEntry entry;int count=0;
            while((entry=zip.getNextEntry())!=null){
                String path=entry.getName();if(++count>128||path.startsWith("/")||path.contains("\\")||path.contains(":"))throw new IOException("Invalid save ZIP");
                for(String component:path.split("/"))if(component.equals("..")||component.equals("."))throw new IOException("Unsafe ZIP path");
                if(entry.isDirectory())continue;
                String name=path.substring(path.lastIndexOf('/')+1);
                // Do not expand arbitrary unrelated files or accept entire emulator backups.
                if(size(name)<0)throw new IOException("Save ZIP contains an unsupported file: "+name);
                add(files,name,read(zip,size(name)));
            }
        }
        if(files.isEmpty())throw new IOException("No supported game saves found");return files;
    }
    public static void writeZip(Map<String,byte[]> files,OutputStream output)throws IOException {
        if(files.isEmpty())throw new IOException("No in-game saves to export yet");
        try(ZipOutputStream zip=new ZipOutputStream(output)) {for(String name:new TreeSet<>(files.keySet())){ZipEntry e=new ZipEntry(name);zip.putNextEntry(e);zip.write(files.get(name));zip.closeEntry();}}
    }
    public static String digest(Map<String,byte[]> files) {
        try{MessageDigest hash=MessageDigest.getInstance("SHA-256");for(String name:new TreeSet<>(files.keySet())){hash.update(name.getBytes(StandardCharsets.UTF_8));hash.update((byte)0);hash.update(files.get(name));}StringBuilder result=new StringBuilder();for(byte b:hash.digest())result.append(String.format(Locale.ROOT,"%02x",b&255));return result.toString();}catch(Exception e){throw new IllegalStateException(e);}
    }
    public static Map<String,byte[]> local(File root)throws IOException {
        Map<String,byte[]> files=new TreeMap<>();
        if(Files.isSymbolicLink(root.toPath()))throw new IOException("Save folder cannot be a link");
        for(String name:NAMES){Path p=new File(root,name).toPath();if(!Files.exists(p,LinkOption.NOFOLLOW_LINKS))continue;
            if(!Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS))throw new IOException("Save file is not a regular file");
            try(InputStream in=Files.newInputStream(p)){add(files,name,read(in,size(name)));}}
        return files;
    }
    public static boolean mayPublish(String baseline,Map<String,byte[]> remote,Map<String,byte[]> outgoing) {
        return digest(remote).equals(baseline)||digest(remote).equals(digest(outgoing));
    }
    /** Merge an import without deleting other slots. Keep the previous directory as a recovery copy. */
    public static File install(File root,Map<String,byte[]> incoming)throws IOException {
        if(incoming.isEmpty())throw new IOException("No supported saves to import");
        Map<String,byte[]> checked=new TreeMap<>();for(Map.Entry<String,byte[]> e:incoming.entrySet())add(checked,e.getKey(),e.getValue());
        Path directory=root.toPath().toAbsolutePath(),parent=directory.getParent();Files.createDirectories(parent);
        if(Files.isSymbolicLink(directory))throw new IOException("Save folder cannot be a link");
        Path stage=Files.createTempDirectory(parent,".save-stage-");Path backup=parent.resolve("save-backup-"+UUID.randomUUID());boolean moved=false;
        try {
            if(Files.exists(directory)){
                Files.walkFileTree(directory,new SimpleFileVisitor<Path>(){
                    public FileVisitResult preVisitDirectory(Path p,java.nio.file.attribute.BasicFileAttributes a)throws IOException{Files.createDirectories(stage.resolve(directory.relativize(p)));return FileVisitResult.CONTINUE;}
                    public FileVisitResult visitFile(Path p,java.nio.file.attribute.BasicFileAttributes a)throws IOException{if(!a.isRegularFile())throw new IOException("Save folder contains a link or special file");Files.copy(p,stage.resolve(directory.relativize(p)));return FileVisitResult.CONTINUE;}
                });
            }
            for(Map.Entry<String,byte[]> e:checked.entrySet())try(FileOutputStream out=new FileOutputStream(stage.resolve(e.getKey()).toFile())){out.write(e.getValue());out.getFD().sync();}
            if(Files.exists(directory)){Files.move(directory,backup,StandardCopyOption.ATOMIC_MOVE);moved=true;}
            try{Files.move(stage,directory,StandardCopyOption.ATOMIC_MOVE);}catch(IOException e){if(moved)Files.move(backup,directory,StandardCopyOption.ATOMIC_MOVE);throw e;}
            return moved?backup.toFile():null;
        }finally{if(Files.exists(stage))Files.walkFileTree(stage,new SimpleFileVisitor<Path>(){public FileVisitResult visitFile(Path p,java.nio.file.attribute.BasicFileAttributes a)throws IOException{Files.delete(p);return FileVisitResult.CONTINUE;}public FileVisitResult postVisitDirectory(Path p,IOException e)throws IOException{Files.delete(p);return FileVisitResult.CONTINUE;}});}
    }
}
