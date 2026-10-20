package org.triaevum.android;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.drawable.Drawable;
import android.graphics.RectF;
import android.util.SparseArray;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowInsets;
import java.util.ArrayList;

/** Native-resolution presentation matching the Ship mobile controller layout. */
public final class TouchOverlay extends View {
    private static native void button(int button, boolean down);
    private static native void axis(int axis, int value);
    private static native float opacity();
    private static native void hudAnchor(int slot,float x,float y);
    private static native void hudDisplay(float width,float height);
    private static native float size();
    private static native void enabled(boolean enabled);
    private static native void displayMetrics(float density,float height);
    private static native int state(); // ready, menu, configured visibility
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final ArrayList<Control> controls=new ArrayList<>();
    private final SparseArray<Control> fingers=new SparseArray<>();
    private boolean menu=true, shown=true, ready=false, editor=false, floating=true, extras=false, itemIcons=false;
    private int faceLayout=0;
    private float controlSize=1;
    private float unit=1, left=0, right=0, bottom=0, top=0;
    private int lastState=-1;
    private float lastOpacity=-1;
    private ColorMatrixColorFilter opacityFilter;
    private final Drawable cross,crossItems;
    private Drawable image(String name) {return getContext().getDrawable(getResources().getIdentifier("retuned_touch_"+name,"drawable",getContext().getPackageName())).mutate();}
    private final class Control {
        final int id; final String label; final RectF bounds; final int shape;
        final Drawable drawable;
        boolean down; int pointer=-1; float cx,cy,x,y;
        Control(int id,String label,float x,float y,float w,float h,int shape) {
            this.id=id;this.label=label;this.bounds=new RectF(x,y,x+w,y+h);this.shape=shape;
            cx=bounds.centerX();cy=bounds.centerY();
            drawable=shape==2||shape==3?null:image(shape==0?(itemIcons&&id>=0&&id<4?"face_items":"face"):id==104||id==9?"left":id==105||id==10?"right":"system");
        }
        void release() {
            if(shape==2) {axis(id,0);axis(id+1,0);}
            else if(id>=100)axis(id-100,-32768);
            else if(id>=0)button(id,false);
            down=false;pointer=-1;x=y=0;
        }
        void move(float px,float py) {
            float radius=75*unit*.68f;
            x=(px-cx)/radius;y=(py-cy)/radius;
            float length=(float)Math.hypot(x,y);if(length>1){x/=length;y/=length;}
            axis(id,Math.round(x*32767));axis(id+1,Math.round(y*32767));
        }
    }
    public TouchOverlay(Context context) {
        super(context);cross=image("cross");crossItems=image("cross_items");setBackgroundColor(android.graphics.Color.TRANSPARENT);
        setFocusable(false);setContentDescription("Touch controller");
    }
    public void cancelInputs() {
        for(int i=0;i<fingers.size();i++)fingers.valueAt(i).release();fingers.clear();
    }
    private void add(int id,String label,float x,float y,float w,float h,int shape) {
        controls.add(new Control(id,label,x,y,w,h,shape));
    }
    private void layoutControls() {
        controls.clear();float w=getWidth(),h=getHeight();
        unit=controlSize*Math.max(.82f,Math.min(1.35f,h/(390*getResources().getDisplayMetrics().density)))*getResources().getDisplayMetrics().density;
        left=right=bottom=top=16*unit;
        WindowInsets insets=getRootWindowInsets();
        if(insets!=null&&android.os.Build.VERSION.SDK_INT>=30) {
            android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
            left+=safe.left;right+=safe.right;bottom+=safe.bottom;top+=safe.top;
        }
        if(editor)return;
        if(shown) {
            {
                if(extras)add(104,"ZL",left,top,84*unit,46*unit,1);
                add(9,"L",left,top+(extras?56:0)*unit,84*unit,46*unit,1);
                if(extras)add(105,"ZR",w-right-84*unit,top,84*unit,46*unit,1);
                add(10,"R",w-right-84*unit,top+(extras?56:0)*unit,84*unit,46*unit,1);
            }
            float fx=w-right-93*unit,fy=h-bottom-93*unit,fs=44*unit;
            if(faceLayout==2) {
                add(0,"A",fx+12*unit-fs*.675f,fy+20*unit-fs*.675f,fs*1.35f,fs*1.35f,0);
                add(1,"B",fx-44*unit-fs/2,fy+28.6f*unit-fs/2,fs,fs,0);
                add(2,"X",fx+44*unit-fs/2,fy-24.2f*unit-fs/2,fs,fs,0);
                add(3,"Y",fx-8*unit-fs/2,fy-44*unit-fs/2,fs,fs,0);
            } else {
                add(0,"A",fx+(faceLayout==0?44:0)*unit-fs/2,fy+(faceLayout==0?0:44)*unit-fs/2,fs,fs,0);
                add(1,"B",fx+(faceLayout==0?0:44)*unit-fs/2,fy+(faceLayout==0?44:0)*unit-fs/2,fs,fs,0);
                add(2,"X",fx+(faceLayout==0?0:-44)*unit-fs/2,fy+(faceLayout==0?-44:0)*unit-fs/2,fs,fs,0);
                add(3,"Y",fx+(faceLayout==0?-44:0)*unit-fs/2,fy+(faceLayout==0?0:-44)*unit-fs/2,fs,fs,0);
            }
            {
                add(6,"Start",w/2+62*unit,h-bottom-30*unit,76*unit,30*unit,1);
            }
            float cross=96*unit,cx=left,cy=Math.max(top+(extras?114:58)*unit,h-bottom-252*unit);
            add(11,"",cx+cross/3,cy,cross/3,cross/3,3);
            add(12,"",cx+cross/3,cy+2*cross/3,cross/3,cross/3,3);
            add(13,"",cx,cy+cross/3,cross/3,cross/3,3);
            add(14,"",cx+2*cross/3,cy+cross/3,cross/3,cross/3,3);
            {
                // Floating sticks sit behind buttons and do not steal their touches.
                add(0,"",0,0,w*.46f,h,2);
                add(2,"",w*.52f,0,w*.48f,h,2);
            }
        }
        if(shown&&!menu)add(4,"Settings",w/2-138*unit,h-bottom-30*unit,76*unit,30*unit,1);
        hudDisplay(w,h);
        for(Control c:controls){int slot=c.shape==0&&c.id>=0&&c.id<4?c.id:c.shape==3?c.id-7:-1;if(slot>=0)hudAnchor(slot,c.bounds.centerX()/w,c.bounds.centerY()/h);}
        add(-1,"◉",w-right-30*unit,h-bottom-30*unit,30*unit,30*unit,0);
    }
    @Override protected void onSizeChanged(int w,int h,int ow,int oh) {cancelInputs();try{displayMetrics(getResources().getDisplayMetrics().density,h);}catch(UnsatisfiedLinkError ignored){}layoutControls();}
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        try {
            int current=state();
            float scale=size();
            if(current!=lastState || controlSize!=scale) {
                displayMetrics(getResources().getDisplayMetrics().density,getHeight());
                itemIcons=(current&256)!=0;extras=(current&128)!=0;controlSize=scale;editor=(current&32)!=0;floating=(current&64)!=0;faceLayout=(current>>3)&3;
                cancelInputs();lastState=current;ready=(current&1)!=0;menu=(current&2)!=0;shown=(current&4)!=0;layoutControls();
            }
        } catch(UnsatisfiedLinkError notLoaded) {postInvalidateOnAnimation();return;}
        if(!ready||editor){postInvalidateOnAnimation();return;}
        float alpha=opacity();
        if(alpha!=lastOpacity){lastOpacity=alpha;opacityFilter=new ColorMatrixColorFilter(new ColorMatrix(new float[]{1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,alpha/.28f,0}));}
        paint.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.NORMAL));
        paint.setTextAlign(Paint.Align.CENTER);paint.setTextSize(14*unit);
        for(Control c:controls) {
            if(c.shape==2) {
                if(!c.down){if(floating||c.id!=0)continue;c.cx=left+75*unit;c.cy=getHeight()-bottom-75*unit;}
                paint.setStyle(Paint.Style.FILL);paint.setColor(0x20ffffff);canvas.drawCircle(c.cx,c.cy,75*unit,paint);
                paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2*unit);canvas.drawCircle(c.cx,c.cy,75*unit,paint);
                paint.setStyle(Paint.Style.FILL);canvas.drawCircle(c.cx+c.x*51*unit,c.cy+c.y*51*unit,24*unit,paint);continue;
            }
            if(c.shape==3) {
                if(c.id==11) {
                    int cx=Math.round(c.bounds.left-32*unit),cy=Math.round(c.bounds.top);
                    Drawable dpad=itemIcons?crossItems:cross;
                    dpad.setBounds(cx,cy,Math.round(cx+96*unit),Math.round(cy+96*unit));dpad.setColorFilter(opacityFilter);dpad.draw(canvas);
                }
                continue;
            }
            c.drawable.setState(c.down?new int[]{android.R.attr.state_pressed}:new int[]{});
            c.drawable.setBounds(Math.round(c.bounds.left),Math.round(c.bounds.top),Math.round(c.bounds.right),Math.round(c.bounds.bottom));c.drawable.setColorFilter(opacityFilter);c.drawable.draw(canvas);
            paint.setStyle(Paint.Style.FILL);paint.setColor((Math.min(255,Math.round(37*alpha/.28f))<<24)|0xffffff);
            String label=c.label;
            if(c.shape==3)label=c.id==11?"▲":c.id==12?"▼":c.id==13?"◀":"▶";
            boolean faceIcon=itemIcons&&c.shape==0&&c.id>=0&&c.id<4;
            paint.setTextSize((faceIcon?10:14)*unit);
            canvas.drawText(label,faceIcon?c.bounds.left+c.bounds.width()*.8f:c.bounds.centerX(),(faceIcon?c.bounds.top+c.bounds.height()*.8f:c.bounds.centerY())-(paint.ascent()+paint.descent())/2,paint);
        }
        postInvalidateOnAnimation();
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        if(!ready||editor)return false;
        int action=event.getActionMasked(),index=event.getActionIndex(),id=event.getPointerId(index);
        if(action==MotionEvent.ACTION_DOWN||action==MotionEvent.ACTION_POINTER_DOWN) {
            float x=event.getX(index),y=event.getY(index);Control chosen=null;
            for(Control c:controls)if(c.pointer<0&&c.bounds.contains(x,y)&&!(menu&&c.shape==2&&y<getHeight()*.72f)){chosen=c;break;}
            if(chosen==null)return fingers.size()>0;
            if(chosen.id==-1){cancelInputs();enabled(!shown);shown=!shown;layoutControls();return true;}
            chosen.pointer=id;chosen.down=true;fingers.put(id,chosen);
            if(chosen.shape==2){chosen.cx=(floating||chosen.id!=0)?x:(chosen.id==0?left+75*unit:getWidth()-right-75*unit);chosen.cy=(floating||chosen.id!=0)?y:getHeight()-bottom-75*unit;chosen.move(x,y);}
            else if(chosen.id>=100)axis(chosen.id-100,32767);else button(chosen.id,true);
            return true;
        }
        if(action==MotionEvent.ACTION_MOVE) {
            for(int i=0;i<event.getPointerCount();i++) {
                Control c=fingers.get(event.getPointerId(i));if(c!=null&&c.shape==2)c.move(event.getX(i),event.getY(i));
            }
            return fingers.size()>0;
        }
        if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_POINTER_UP) {
            Control c=fingers.get(id);if(c!=null){c.release();fingers.remove(id);return true;}
        }
        if(action==MotionEvent.ACTION_CANCEL){cancelInputs();return true;}
        return fingers.size()>0;
    }
}
