// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
public final class SaveFilesCoreCheck {
    static void require(boolean value){if(!value)throw new AssertionError();}
    interface Checked {void run()throws Exception;}
    static void rejects(Checked action)throws Exception{try{action.run();throw new AssertionError("Invalid input accepted");}catch(IOException expected){}}
    static byte[] data(String name,int value){byte[] b=new byte[SaveFilesCore.size(name)];Arrays.fill(b,(byte)value);return b;}
    static Map<String,byte[]> set(int v)throws Exception{Map<String,byte[]> m=new TreeMap<>();SaveFilesCore.add(m,"save00.bin",data("save00.bin",v));SaveFilesCore.add(m,"system.dat",data("system.dat",v));return m;}
    static byte[] zip(String name,byte[] bytes)throws Exception{ByteArrayOutputStream out=new ByteArrayOutputStream();try(ZipOutputStream z=new ZipOutputStream(out)){z.putNextEntry(new ZipEntry(name));z.write(bytes);z.closeEntry();}return out.toByteArray();}
    public static void main(String[] args)throws Exception{
        Map<String,byte[]> first=set(1),second=set(2);ByteArrayOutputStream out=new ByteArrayOutputStream();SaveFilesCore.writeZip(first,out);
        require(SaveFilesCore.digest(SaveFilesCore.readZip(new ByteArrayInputStream(out.toByteArray()))).equals(SaveFilesCore.digest(first)));
        rejects(()->SaveFilesCore.readZip(new ByteArrayInputStream(zip("../save00.bin",data("save00.bin",1)))));
        rejects(()->SaveFilesCore.readZip(new ByteArrayInputStream(zip("/save00.bin",data("save00.bin",1)))));
        rejects(()->SaveFilesCore.readZip(new ByteArrayInputStream(zip("save00.bin",new byte[1000000]))));
        rejects(()->SaveFilesCore.readZip(new ByteArrayInputStream(zip("state.bin",new byte[5340]))));
        rejects(()->SaveFilesCore.add(first,"save00.bin",data("save00.bin",1)));
        rejects(()->SaveFilesCore.add(new TreeMap<>(),"system.dat",new byte[35]));
        Path parent=Files.createTempDirectory("retuned-save-tests-");File root=parent.resolve("saves").toFile();
        SaveFilesCore.install(root,first);Files.write(new File(root,"save02.bin").toPath(),data("save02.bin",7));Files.write(new File(root,"keep.txt").toPath(),new byte[]{42});
        File backup=SaveFilesCore.install(root,second);require(backup!=null&&backup.isDirectory());require(Arrays.equals(Files.readAllBytes(new File(backup,"save00.bin").toPath()),data("save00.bin",1)));
        require(Arrays.equals(Files.readAllBytes(new File(root,"save02.bin").toPath()),data("save02.bin",7)));require(Files.readAllBytes(new File(root,"keep.txt").toPath())[0]==42);
        String before=SaveFilesCore.digest(SaveFilesCore.local(root));Map<String,byte[]> bad=new TreeMap<>();bad.put("save01.bin",new byte[3]);rejects(()->SaveFilesCore.install(root,bad));require(before.equals(SaveFilesCore.digest(SaveFilesCore.local(root))));
        Files.createSymbolicLink(new File(root,"save01.bin").toPath(),parent.resolve("elsewhere"));rejects(()->SaveFilesCore.local(root));rejects(()->SaveFilesCore.install(root,first));
        String base=SaveFilesCore.digest(first);require(SaveFilesCore.mayPublish(base,first,second));require(!SaveFilesCore.mayPublish(base,set(3),second));require(SaveFilesCore.mayPublish(base,second,second));
        System.out.println("Save ZIP, validation, traversal/size limits, slot preservation, recovery copies, link rejection, and conflict checks passed");
    }
}
