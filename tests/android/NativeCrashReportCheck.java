package org.triaevum.android;

import java.io.*;
import java.nio.charset.StandardCharsets;

public final class NativeCrashReportCheck {
    static byte[] number(long value) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        do { int next=(int)(value & 127); value >>>= 7; out.write(value == 0 ? next : next | 128); } while(value != 0);
        return out.toByteArray();
    }
    static byte[] join(byte[]... values) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for(byte[] value:values)out.write(value);
        return out.toByteArray();
    }
    static byte[] scalar(int field,long value)throws IOException{return join(number(field<<3),number(value));}
    static byte[] message(int field,byte[] value)throws IOException{return join(number((field<<3)|2),number(value.length),value);}
    static byte[] text(int field,String value)throws IOException{return message(field,value.getBytes(StandardCharsets.UTF_8));}
    static String report(byte[] bytes){return NativeCrashReport.read(new ByteArrayInputStream(bytes));}
    static void require(boolean value){if(!value)throw new AssertionError();}

    public static void main(String[] args)throws Exception {
        byte[] frame=join(scalar(1,0x1234),scalar(2,0xabcdef),text(4,"private_function_name"),
            text(6,"/data/user/0/private-account/install/triaevum_title_aot.so"),text(8,"aabbccdd"));
        byte[] thread=join(scalar(1,42),text(2,"private-thread"),message(4,frame),text(7,"private-note"),
            message(5,text(1,"private-memory")));
        byte[] tombstone=join(text(2,"private-fingerprint"),text(9,"private@example.test"),scalar(6,42),
            message(10,join(scalar(1,11),scalar(3,1),text(2,"private-signal-name"))),
            text(14,"private-abort-message"),message(16,join(scalar(1,42),message(2,thread))));
        String output=report(tombstone);
        require(output.contains("signal=11, code=1") && output.contains("pc 1234 triaevum_title_aot.so build=aabbccdd"));
        require(!output.contains("private") && !output.contains("abcdef") && !output.contains("/data/") && !output.contains("@"));
        byte[] other=message(4,join(scalar(1,32),text(6,"/storage/secret-name.so"),text(8,"private-build-id")));
        output=report(join(scalar(6,42),message(16,join(scalar(1,42),message(2,other)))));
        require(output.contains("other native library") && !output.contains("secret") && !output.contains("private"));
        ByteArrayOutputStream many=new ByteArrayOutputStream();
        for(int i=0;i<50;i++)many.write(message(4,frame));
        output=report(join(scalar(6,42),message(16,join(scalar(1,42),message(2,many.toByteArray())))));
        require(output.contains("#11") && !output.contains("#12") && output.length()<4096);
        require(report(new byte[]{(byte)0x80}).equals("Native trace could not be decoded."));
        require(report(new byte[]{(byte)0x82,1,(byte)0xff,0x7f}).equals("Native trace could not be decoded."));
        require(report(new byte[2*1024*1024+1]).equals("Native trace exceeds report limit."));
        require(NativeCrashReport.read(null).equals("Native trace unavailable."));
        System.out.println("PASS: native frames, redaction, unknown modules, malformed input, and bounds");
    }
}
