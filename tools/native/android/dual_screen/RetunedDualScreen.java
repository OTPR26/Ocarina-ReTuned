/* SPDX-License-Identifier: GPL-2.0-or-later */
package org.triaevum.android;
import android.app.Activity;
import android.app.Presentation;
import android.hardware.display.DisplayManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.*;
import android.widget.*;

/** Private hardware test: independent GPU output and lower-display touch. */
final class RetunedDualScreen implements DisplayManager.DisplayListener {
 private final Activity activity;private final DisplayManager manager;private Presentation lower;
 private final Handler handler=new Handler(Looper.getMainLooper());private boolean closed=false,wanted=true;
 static native void surface(Surface surface);static native boolean displayWanted();
 static native void touch(int x,int y,boolean down);
 RetunedDualScreen(Activity activity){this.activity=activity;manager=(DisplayManager)activity.getSystemService(Activity.DISPLAY_SERVICE);
  manager.registerDisplayListener(this,handler);refresh();
  handler.post(new Runnable(){public void run(){if(closed)return;boolean next=displayWanted();if(next!=wanted){wanted=next;refresh();}handler.postDelayed(this,250);}});
 }
 private void refresh(){if(closed)return;Display chosen=null;for(Display d:manager.getDisplays())if(wanted&&d.getDisplayId()!=activity.getDisplay().getDisplayId()&&d.getState()==Display.STATE_ON){chosen=d;break;}
  if(lower!=null&&(chosen==null||lower.getDisplay().getDisplayId()!=chosen.getDisplayId())){lower.dismiss();lower=null;}
  if(lower==null&&chosen!=null){android.util.Log.i("ReTunedDual","Opening lower display "+chosen.getDisplayId()+" "+chosen.getName());lower=new Lower(activity,chosen);lower.getWindow().addFlags(WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);lower.show();}
 }
 void close(){closed=true;manager.unregisterDisplayListener(this);touch(0,0,false);if(lower!=null){lower.dismiss();lower=null;}surface(null);}
 public void onDisplayAdded(int id){refresh();}public void onDisplayRemoved(int id){refresh();}public void onDisplayChanged(int id){refresh();}
 private static final class Lower extends Presentation implements SurfaceHolder.Callback {
  private SurfaceView view;
  Lower(Activity a,Display d){super(a,d);}
  protected void onCreate(Bundle b){super.onCreate(b);view=new SurfaceView(getContext());setContentView(view);
   getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
   view.getHolder().addCallback(this);view.setOnTouchListener((v,e)->{int action=e.getActionMasked();boolean down=action!=MotionEvent.ACTION_UP&&action!=MotionEvent.ACTION_CANCEL;
    float w=view.getWidth(),h=view.getHeight(),fitW=Math.min(w,h*4f/3f),fitH=fitW*3f/4f;
    float x=e.getX()-(w-fitW)/2,y=e.getY()-(h-fitH)/2;
    boolean inside=fitW>0&&fitH>0&&x>=0&&y>=0&&x<fitW&&y<fitH;
    touch(inside?(int)(x/fitW*320):0,inside?(int)(y/fitH*240):0,down&&inside);return true;});
  }
  public void surfaceCreated(SurfaceHolder h){surface(h.getSurface());}
  public void surfaceChanged(SurfaceHolder h,int f,int w,int height){surface(h.getSurface());}
  public void surfaceDestroyed(SurfaceHolder h){touch(0,0,false);surface(null);}
 }
}
