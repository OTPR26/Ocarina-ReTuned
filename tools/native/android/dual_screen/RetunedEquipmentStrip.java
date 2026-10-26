/* SPDX-License-Identifier: GPL-2.0-or-later */
package org.triaevum.android;
import android.content.Context;
import android.graphics.*;
import android.view.*;
import java.io.File;

/** Locally prepared UI artwork; game ownership and pulse come from JNI. */
final class RetunedEquipmentStrip extends View {
 private static native int state();
 static native boolean panelEnabled();
 private static native void select(int action);
 private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
 private final RectF[] cells={new RectF(),new RectF(),new RectF()};
 private int snapshot=0,pressed=-1;private float top=0;
 private final Bitmap[] boots=new Bitmap[3],tunics=new Bitmap[3];
 private Bitmap skin,stone,agony;
 private File artworkDirectory() {
  File root=getContext().getExternalFilesDir(null);
  try {
   File profile=new File(root,"native-launch.json");
   org.json.JSONArray args=new org.json.JSONObject(new String(java.nio.file.Files.readAllBytes(profile.toPath()),java.nio.charset.StandardCharsets.UTF_8)).getJSONArray("arguments");
   for(int i=0;i+1<args.length();i++)if("--a32-process-manifest".equals(args.getString(i))) {
    File directory=new File(new File(args.getString(i+1)).getParentFile(),"lower-equipment");
    if(directory.isDirectory())return directory;
   }
  } catch(Exception error) {android.util.Log.w("ReTunedEquipment","Using existing artwork cache",error);}
  return new File(getContext().getFilesDir(),"lower-equipment");
 }
 private Bitmap art(String name){return BitmapFactory.decodeFile(new File(artworkDirectory(),name+".png").getPath());}
 RetunedEquipmentStrip(Context context){super(context);setFocusable(false);
  setContentDescription("Quick boots, tunic, and Shard of Agony");
  skin=art("button");stone=art("stone");agony=art("agony");
  for(int i=0;i<3;i++){boots[i]=art("boots-"+(i+1));tunics[i]=art("tunic-"+(i+1));}
 }
 private boolean enabled(int n){return (snapshot&1)!=0&&n<2&&
  Integer.bitCount((snapshot>>(n==0?8:11))&7)+(n==0&&((snapshot>>8)&1)==0?1:0)>1;}
 @Override protected void onDraw(Canvas c){
  snapshot=state();float w=getWidth(),h=getHeight(),fit=Math.min(w,h*4f/3f)*3f/4f;
  top=fit;float spare=h-fit;
  if(!panelEnabled()||spare<48||(snapshot&16384)==0||skin==null||stone==null){postInvalidateDelayed(33);return;}
  p.setAlpha(255);p.setFilterBitmap(true);
  // Same uninterrupted gray stone used behind the native Items buttons.
  c.drawBitmap(stone,null,new RectF(0,top,w,h),p);
  // A shallow upper bevel separates the footer from the native menu.
  // Scale with the strip, capped well below the side-column bevel width.
  float bevel=Math.max(1f,Math.min(3f,spare*.02f));
  p.setColor(Color.argb(90,0,0,0));c.drawRect(0,top,w,top+bevel,p);
  p.setColor(Color.argb(40,255,255,255));c.drawRect(0,top+bevel,w,top+bevel+1f,p);
  p.setColor(Color.WHITE);
  float cell=Math.min(w/3,spare*1.65f),start=(w-cell*3)/2,edge=spare*.90f;
  for(int n=0;n<3;n++){
   RectF r=cells[n];r.set(start+n*cell,top,start+(n+1)*cell,h);
   boolean shard=n==2,owned=!shard||(snapshot&2)!=0;if(!owned)continue;
   boolean active=shard?(snapshot&4)!=0:enabled(n);
   RectF button=new RectF(r.centerX()-edge/2,top+(spare-edge)/2,r.centerX()+edge/2,top+(spare+edge)/2);
   p.setAlpha(255);c.drawBitmap(skin,null,button,p);
   int member=(snapshot>>(n==0?4:6))&3;
   Bitmap icon=shard?agony:(n==0?boots:tunics)[Math.max(0,Math.min(2,member-1))];
   if(icon!=null){float inset=edge*.15f;RectF inside=new RectF(button);inside.inset(inset,inset);
    p.setAlpha(shard?(active?255:185):active?255:130);c.drawBitmap(icon,null,inside,p);}
   if(shard&&active){p.setAlpha(255);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);p.setColor(Color.rgb(160,235,255));c.drawRoundRect(button,10,10,p);p.setStyle(Paint.Style.FILL);}
  }
  p.setAlpha(255);
  postInvalidateDelayed(33);
 }
 @Override public boolean onTouchEvent(MotionEvent e){
  if(e.getActionMasked()==MotionEvent.ACTION_DOWN){
   if(!panelEnabled()||e.getY()<top||(snapshot&16384)==0)return false;pressed=-1;
   for(int n=0;n<2;n++)if(cells[n].contains(e.getX(),e.getY())&&enabled(n))pressed=n;
   return true;
  }
  if(e.getActionMasked()==MotionEvent.ACTION_UP){
   if(pressed>=0&&cells[pressed].contains(e.getX(),e.getY())&&enabled(pressed))select(pressed+1);
   pressed=-1;performClick();return true;
  }
  if(e.getActionMasked()==MotionEvent.ACTION_CANCEL)pressed=-1;
  return true;
 }
 @Override public boolean performClick(){super.performClick();return true;}
}
