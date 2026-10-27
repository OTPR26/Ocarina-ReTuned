package org.triaevum.android;
import java.io.File;
import java.io.IOException;

public final class PreparationSessionCheck {
    public static void main(String[] args) throws Exception {
        File root=new File(args[0]);
        if(args.length>1 && args[1].equals("hold")) {
            try(PreparationSession owner=PreparationSession.acquire(root)) {
                System.out.println("READY");System.out.flush();
                new java.io.BufferedReader(new java.io.InputStreamReader(System.in)).readLine();
            }
            return;
        }
        if(args.length>1 && args[1].equals("probe")) {
            try(PreparationSession unexpected=PreparationSession.acquire(root)) {
                throw new AssertionError("Another process acquired the session");
            } catch(IOException expected) { System.out.println("BLOCKED"); }
            return;
        }
        try(PreparationSession first=PreparationSession.acquire(root)) {
            boolean blocked=false;
            try(PreparationSession second=PreparationSession.acquire(root)) { }
            catch(IOException expected) { blocked=true; }
            if(!blocked)throw new AssertionError("Concurrent worker acquired the session");
        }
        try(PreparationSession next=PreparationSession.acquire(root)) { }
        if(!new File(root,".preparation-session.lock").isFile())throw new AssertionError("Session file was deleted");
        System.out.println("PASS");
    }
}
