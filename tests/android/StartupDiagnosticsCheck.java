package org.triaevum.android;
import android.app.*;
import android.content.*;
import android.os.Bundle;
/** Runs in an isolated test package; crash mode is supplied only by the private harness. */
public final class StartupDiagnosticsCheck extends Instrumentation {
    private Bundle args;
    @Override public void onCreate(Bundle arguments){args=arguments;start();}
    @Override public void onStart(){
        Bundle result=new Bundle();
        try {
            Context c=getTargetContext();
            if (args.getBoolean("launcher",false)) {
                StartupDiagnostics.prefs(c).edit().putBoolean("pending",false).commit();
                Activity screen=startActivitySync(new Intent(c,TriAevumActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                if(!"ROM chooser ready".equals(StartupDiagnostics.prefs(c).getString("stage",""))) throw new AssertionError("chooser did not initialize");
                runOnMainSync(()->screen.finish());
            } else if (args.getBoolean("recovery",false)) {
                if(!StartupDiagnostics.prefs(c).getBoolean("pending",false))throw new AssertionError("failure not retained");
                if(!StartupDiagnostics.report(c).contains(args.getString("expect","Java")))throw new AssertionError(StartupDiagnostics.report(c));
                Activity screen=startActivitySync(new Intent(c,StartupDiagnosticsActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                if(screen==null)throw new AssertionError("recovery screen missing");
                runOnMainSync(()->screen.finish());
            } else {
                StartupDiagnostics.stage(c,"library test");StartupDiagnostics.failure(c,new UnsatisfiedLinkError("private /storage/ROM.3ds"));
                String report=StartupDiagnostics.report(c);
                if(report.contains("/storage/")||report.contains("ROM.3ds")||!report.contains("UnsatisfiedLinkError"))throw new AssertionError(report);
                StartupDiagnostics.prefs(c).edit().putBoolean("pending",false).commit();
            }
            result.putString("result","PASS");finish(Activity.RESULT_OK,result);
        }catch(Throwable error){result.putString("failure",error.toString());finish(Activity.RESULT_CANCELED,result);}
    }
}
