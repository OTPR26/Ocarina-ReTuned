/* SPDX-License-Identifier: GPL-2.0-or-later */
package org.triaevum.android;

import android.content.Context;
import android.graphics.*;
import android.view.*;
import java.io.File;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

/** Save access in the native lower-screen sidebar, independent of the equipment panel. */
final class RetunedSaveButton extends View {
 private static native boolean visible();
 private static native void open();
 private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
 private final RectF button=new RectF();
 private Bitmap skin;
 private boolean pressed;
 RetunedSaveButton(Context context) {
  super(context);setFocusable(false);setContentDescription("Save game");
  File root=context.getExternalFilesDir(null),directory=null;
  try {
   org.json.JSONArray args=new org.json.JSONObject(new String(java.nio.file.Files.readAllBytes(new File(root,"native-launch.json").toPath()),java.nio.charset.StandardCharsets.UTF_8)).getJSONArray("arguments");
   for(int i=0;i+1<args.length();i++)if("--a32-process-manifest".equals(args.getString(i)))
    directory=new File(new File(args.getString(i+1)).getParentFile(),"lower-equipment");
  } catch(Exception error) {android.util.Log.w("ReTunedSave","Using existing artwork cache",error);}
  if(directory==null||!directory.isDirectory())directory=new File(context.getFilesDir(),"lower-equipment");
  skin=BitmapFactory.decodeFile(new File(directory,"save.png").getPath());
  if(skin==null) {
   final File installation=directory.getParentFile();
   new Thread(()->{
    try {
     File kit=PreparationKit.install(context);
     synchronized(Python.class){if(!Python.isStarted())Python.start(new AndroidPlatform(context.getApplicationContext()));}
     String path=Python.getInstance().getModule("retuned_lower_art_entry").callAttr("ensure_save",kit.getAbsolutePath(),installation.getAbsolutePath()).toString();
     Bitmap image=BitmapFactory.decodeFile(path);
     post(()->{skin=image;invalidate();});
    } catch(Exception error){android.util.Log.w("ReTunedSave","Save artwork unavailable",error);}
   },"ReTuned Save artwork").start();
  }
 }
 private void updateBounds() {
  float width=Math.min(getWidth(),getHeight()*4f/3f),height=width*3f/4f;
  float x=(getWidth()-width)/2,y=RetunedEquipmentStrip.panelEnabled()?0:(getHeight()-height)/2;
  button.set(x+width*8/320,y+height*64/240,x+width*48/320,y+height*98/240);
 }
 private boolean shown(){return skin!=null&&visible();}
 @Override protected void onDraw(Canvas canvas) {
  updateBounds();
  if(shown()) {
   paint.setColor(Color.WHITE);
   float height=button.width()*skin.getHeight()/skin.getWidth();
   canvas.drawBitmap(skin,null,new RectF(button.left,button.centerY()-height/2,button.right,button.centerY()+height/2),paint);
  } else pressed=false;
  postInvalidateDelayed(33);
 }
 @Override public boolean onTouchEvent(MotionEvent event) {
  updateBounds();
  if(event.getActionMasked()==MotionEvent.ACTION_DOWN) {
   pressed=shown()&&button.contains(event.getX(),event.getY());return pressed;
  }
  if(event.getActionMasked()==MotionEvent.ACTION_UP) {
   boolean activate=pressed&&shown()&&button.contains(event.getX(),event.getY());pressed=false;
   if(activate)performClick();return true;
  }
  if(event.getActionMasked()==MotionEvent.ACTION_CANCEL)pressed=false;
  return true;
 }
 @Override public boolean performClick(){super.performClick();if(shown())open();return true;}
}
