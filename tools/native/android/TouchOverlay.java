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
    private boolean menu=true, shown=true, configured=true, ready=false, blockedByMenu=false, floating=true, extras=false, itemIcons=false;
    private int faceLayout=0, jumpMode=0;
    private boolean layoutEditing=false, dual=false;
    private TouchLayout placement=new TouchLayout(), savedPlacement;
    private String profile="single";
    private final RectF dpadBounds=new RectF();
    private final RectF[] editButtons={new RectF(),new RectF(),new RectF()};
    private Control dragged;
    private int dragPointer=-1;
    private float dragX,dragY;
    private String selected="";

    public void startEditing() {
        if (layoutEditing) return;
        cancelInputs();
        savedPlacement=placement.copy();
        layoutEditing=true;
        selected="";
        layoutControls();invalidate();
        announceForAccessibility("Drag controls to move them. Save, Cancel, and Reset are at the top.");
    }
    public boolean cancelEditing() {
        if(!layoutEditing)return false;
        finishEditing(false);return true;
    }
    public void suspendEditing() {
        cancelInputs();
        if(layoutEditing)finishEditing(false);
    }
    private void finishEditing(boolean save) {
        if (save) getContext().getSharedPreferences("touch-layouts",Context.MODE_PRIVATE)
            .edit().putString(profile,placement.encode()).apply();
        else placement=savedPlacement;
        layoutEditing=false;dragged=null;dragPointer=-1;
        layoutControls();invalidate();
    }
    private static String key(Control c) {
        if(c.shape==2)return c.id==0?"move":"look";
        if(c.shape==3)return "dpad";
        switch(c.id) {
        case 0:return "a";case 1:return "b";case 2:return "x";case 3:return "y";
        case 9:return "l";case 10:return "r";case 104:return "zl";case 105:return "zr";
        case 6:return "start";case 4:return "settings";case 15:return "map";
        default:return "visibility";
        }
    }
    private void placeControls(float w,float h) {
        float[] pad=placement.get("dpad");
        if(pad!=null) {
            float x=Math.max(left+dpadBounds.width()/2,Math.min(w-right-dpadBounds.width()/2,pad[0]*w));
            float y=Math.max(top+dpadBounds.height()/2,Math.min(h-bottom-dpadBounds.height()/2,pad[1]*h));
            float dx=x-dpadBounds.centerX(),dy=y-dpadBounds.centerY();
            dpadBounds.offset(dx,dy);
            for(Control c:controls)if(c.shape==3)c.bounds.offset(dx,dy);
        }
        for(Control c:controls) {
            if(c.shape==3)continue;
            float[] center=placement.get(key(c));
            if(c.shape==2) {
                c.cx=c.id==0?left+75*unit:w*.62f;
                c.cy=c.id==0?h-bottom-75*unit:h*.62f;
            }
            if(center==null&&!layoutEditing)continue;
            float bw=c.shape==2?150*unit:c.bounds.width(),bh=c.shape==2?150*unit:c.bounds.height();
            float x=center!=null?center[0]*w:c.shape==2?c.cx:c.bounds.centerX();
            float y=center!=null?center[1]*h:c.shape==2?c.cy:c.bounds.centerY();
            x=Math.max(left+bw/2,Math.min(w-right-bw/2,x));
            y=Math.max(top+bh/2,Math.min(h-bottom-bh/2,y));
            c.bounds.set(x-bw/2,y-bh/2,x+bw/2,y+bh/2);c.cx=x;c.cy=y;
        }
    }
    private boolean editTouch(MotionEvent event) {
        int action=event.getActionMasked(),index=event.getActionIndex();
        if(action==MotionEvent.ACTION_DOWN) {
            float x=event.getX(),y=event.getY();
            for(int i=0;i<editButtons.length;i++)if(editButtons[i].contains(x,y)) {
                if(i==0)finishEditing(true);
                else if(i==1)finishEditing(false);
                else {placement.clear();selected="";layoutControls();}
                return true;
            }
            dragged=null;
            for(Control c:controls)if(c.shape!=2&&(c.shape==3?dpadBounds:c.bounds).contains(x,y)){dragged=c;break;}
            if(dragged==null)for(Control c:controls)if(c.shape==2&&c.bounds.contains(x,y)){dragged=c;break;}
            if(dragged!=null) {
                RectF bounds=dragged.shape==3?dpadBounds:dragged.bounds;
                selected=key(dragged);dragPointer=event.getPointerId(index);
                dragX=x-bounds.centerX();dragY=y-bounds.centerY();
            }
        } else if(action==MotionEvent.ACTION_MOVE&&dragged!=null) {
            int pointer=event.findPointerIndex(dragPointer);
            if(pointer>=0) {
                placement.set(selected,(event.getX(pointer)-dragX)/getWidth(),(event.getY(pointer)-dragY)/getHeight());
                layoutControls();
            }
        } else if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_CANCEL) {
            dragged=null;dragPointer=-1;
        }
        invalidate();return true;
    }
    private void drawEditor(Canvas canvas) {
        paint.setStyle(Paint.Style.FILL);paint.setColor(0xee08090f);
        canvas.drawRect(0,0,getWidth(),getHeight(),paint);
        paint.setTypeface(android.graphics.Typeface.create("sans-serif-medium",0));paint.setTextAlign(Paint.Align.CENTER);
        paint.setTextSize(14*unit);paint.setStrokeWidth(2*unit);
        for(Control c:controls) {
            if(c.shape==3&&c.id!=11)continue;
            RectF b=c.shape==3?dpadBounds:c.bounds;
            paint.setStyle(Paint.Style.STROKE);paint.setColor(key(c).equals(selected)?0xffffcf64:0xccffffff);
            if(c.shape==2||c.shape==0)canvas.drawOval(b,paint);
            else canvas.drawRoundRect(b,8*unit,8*unit,paint);
            paint.setStyle(Paint.Style.FILL);
            String name=key(c);if(name.equals("visibility"))name="Eye";if(name.equals("dpad"))name="D-pad";if(name.length()==1||name.equals("zl")||name.equals("zr"))name=name.toUpperCase(java.util.Locale.ROOT);
            canvas.drawText(name,b.centerX(),b.centerY()-(paint.ascent()+paint.descent())/2,paint);
        }
        float width=82*unit,gap=8*unit,x=getWidth()/2-(3*width+2*gap)/2,y=top;
        String[] labels={"Save","Cancel","Reset"};
        for(int i=0;i<3;i++) {
            RectF b=editButtons[i];b.set(x+i*(width+gap),y,x+i*(width+gap)+width,y+34*unit);
            paint.setColor(0xff253746);canvas.drawRoundRect(b,6*unit,6*unit,paint);
            paint.setColor(0xffffffff);canvas.drawText(labels[i],b.centerX(),b.centerY()-(paint.ascent()+paint.descent())/2,paint);
        }
        paint.setTextSize(12*unit);paint.setColor(0xffffffff);
        canvas.drawText((dual?"Dual-screen":"Single-screen")+" layout · Drag controls to move",getWidth()/2,y+55*unit,paint);
    }
    private float controlSize=1;
    private float unit=1, left=0, right=0, bottom=0, top=0;
    private int lastState=-1;
    private float lastOpacity=-1;
    private ColorMatrixColorFilter opacityFilter;
    private final Drawable cross,crossItems;
    private Drawable image(String name) {return getContext().getDrawable(getResources().getIdentifier("retuned_touch_"+name,"drawable",getContext().getPackageName())).mutate();}
    private boolean usesItemIcon(int id, int shape) {
        if (!itemIcons) return false;
        if (id == 105 && jumpMode == 2) return true;
        return shape == 0 && id >= 0 && id < 4 && !(id == 2 && jumpMode == 2);
    }
    private String artworkFor(int id, int shape) {
        if (shape == 0) return usesItemIcon(id, shape) ? "face_items" : "face";
        if (id == 104 || id == 9) return "left";
        if (id == 105 || id == 10) return usesItemIcon(id, shape) ? "right_items" : "right";
        return "system";
    }
    private final class Control {
        final int id; final String label; final RectF bounds; final int shape;
        final Drawable drawable;
        boolean down; int pointer=-1; float cx,cy,x,y;
        Control(int id,String label,float x,float y,float w,float h,int shape) {
            this.id=id;this.label=label;this.bounds=new RectF(x,y,x+w,y+h);this.shape=shape;
            cx=bounds.centerX();cy=bounds.centerY();
            drawable = shape == 2 || shape == 3 ? null : image(artworkFor(id, shape));
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
        setFocusable(false);setDefaultFocusHighlightEnabled(false);setContentDescription("Touch controller");
        try{displayMetrics(getResources().getDisplayMetrics().density,getResources().getDisplayMetrics().heightPixels);}catch(UnsatisfiedLinkError ignored){}
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
        if(blockedByMenu&&!layoutEditing)return;
        if(shown||layoutEditing) {
            {
                float sw=63*unit,sh=34.5f*unit,gap=10*unit;
                boolean pair=extras||jumpMode!=0||layoutEditing;
                if(pair)add(104,"",left,top,sw,sh,1);
                add(9,"",left,top+(pair?sh+gap:0),sw,sh,1);
                if(pair)add(105,"",w-right-sw,top,sw,sh,1);
                add(10,"",w-right-sw,top+(pair?sh+gap:0),sw,sh,1);
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
            dpadBounds.set(cx,cy,cx+cross,cy+cross);
            add(15,"",cx+cross+12*unit,cy+cross/3,36*unit,36*unit,0);
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
        if((shown&&!menu)||layoutEditing)add(4,"Settings",w/2-138*unit,h-bottom-30*unit,76*unit,30*unit,1);
        if(configured||layoutEditing)add(-1,"◉",w-right-30*unit,h-bottom-30*unit,30*unit,30*unit,0);
        placeControls(w,h);
        hudDisplay(w,h);
        for(Control c:controls){int slot=c.shape==0&&c.id>=0&&c.id<4?c.id:c.shape==3?c.id-7:-1;if(c.id==105)slot=8;if(slot>=0)hudAnchor(slot,c.bounds.centerX()/w,c.bounds.centerY()/h);}

    }
    @Override protected void onSizeChanged(int w,int h,int ow,int oh) {cancelInputs();try{displayMetrics(getResources().getDisplayMetrics().density,h);}catch(UnsatisfiedLinkError ignored){}layoutControls();}
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        try {
            int current=state();
            float scale=size();
            if(current!=lastState || controlSize!=scale) {
                displayMetrics(getResources().getDisplayMetrics().density,getHeight());
                jumpMode=(current>>10)&3;itemIcons=(current&256)!=0;extras=(current&128)!=0;controlSize=scale;blockedByMenu=(current&32)!=0;floating=(current&64)!=0;faceLayout=(current>>3)&3;
                boolean nextDual=(current&4096)!=0;
                if(nextDual!=dual||lastState==-1) {
                    if(layoutEditing)finishEditing(false);
                    dual=nextDual;profile=dual?"dual":"single";
                    placement=TouchLayout.decode(getContext().getSharedPreferences("touch-layouts",Context.MODE_PRIVATE).getString(profile,""));
                }
                if(layoutEditing&&!blockedByMenu)finishEditing(false);
                cancelInputs();lastState=current;ready=(current&1)!=0;menu=(current&2)!=0;shown=(current&4)!=0;configured=(current&512)!=0;layoutControls();
            }
        } catch(UnsatisfiedLinkError notLoaded) {postInvalidateOnAnimation();return;}
        if(layoutEditing){drawEditor(canvas);postInvalidateOnAnimation();return;}
        if(!ready||blockedByMenu){postInvalidateOnAnimation();return;}
        float alpha=opacity();
        if(alpha!=lastOpacity){lastOpacity=alpha;opacityFilter=new ColorMatrixColorFilter(new ColorMatrix(new float[]{1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,alpha/.28f,0}));}
        paint.setTypeface(android.graphics.Typeface.create("sans-serif-medium",android.graphics.Typeface.NORMAL));
        paint.setTextAlign(Paint.Align.CENTER);paint.setTextSize(14*unit);
        for(Control c:controls) {
            if(c.shape==2) {
                if(!c.down){if(floating||c.id!=0)continue;}
                paint.setColor(0x20ffffff);
                paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2*unit);canvas.drawCircle(c.cx,c.cy,75*unit,paint);
                canvas.drawCircle(c.cx+c.x*51*unit,c.cy+c.y*51*unit,24*unit,paint);continue;
            }
            if(c.shape==3) {
                if(c.id==11) {
                    int cx=Math.round(dpadBounds.left),cy=Math.round(dpadBounds.top);
                    Drawable dpad=itemIcons?crossItems:cross;
                    dpad.setBounds(cx,cy,Math.round(cx+96*unit),Math.round(cy+96*unit));dpad.setColorFilter(opacityFilter);dpad.draw(canvas);
                }
                continue;
            }
            c.drawable.setState(c.down?new int[]{android.R.attr.state_pressed}:new int[]{});
            c.drawable.setBounds(Math.round(c.bounds.left),Math.round(c.bounds.top),Math.round(c.bounds.right),Math.round(c.bounds.bottom));c.drawable.setColorFilter(opacityFilter);c.drawable.draw(canvas);
            paint.setStyle(Paint.Style.FILL);paint.setColor((Math.min(255,Math.round(37*alpha/.28f))<<24)|0xffffff);
            if(c.id==15) {
                paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1.5f*unit);
                float x=c.bounds.left+10*unit,y=c.bounds.top+10*unit;
                android.graphics.Path map=new android.graphics.Path();
                map.moveTo(x,y+2*unit);map.lineTo(x+5*unit,y);map.lineTo(x+11*unit,y+3*unit);map.lineTo(x+16*unit,y+unit);
                map.lineTo(x+16*unit,y+15*unit);map.lineTo(x+11*unit,y+17*unit);map.lineTo(x+5*unit,y+14*unit);map.lineTo(x,y+16*unit);map.close();
                canvas.drawPath(map,paint);canvas.drawLine(x+5*unit,y,x+5*unit,y+14*unit,paint);canvas.drawLine(x+11*unit,y+3*unit,x+11*unit,y+17*unit,paint);
                paint.setStyle(Paint.Style.FILL);
            }
            String label=c.label;
            if(c.shape==3)label=c.id==11?"▲":c.id==12?"▼":c.id==13?"◀":"▶";
            boolean faceIcon = usesItemIcon(c.id, c.shape);
            paint.setTextSize((faceIcon?10:14)*unit);
            canvas.drawText(label,faceIcon?c.bounds.left+c.bounds.width()*.8f:c.bounds.centerX(),(faceIcon?c.bounds.top+c.bounds.height()*.8f:c.bounds.centerY())-(paint.ascent()+paint.descent())/2,paint);
        }
        postInvalidateOnAnimation();
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        if(layoutEditing)return editTouch(event);
        if(!ready||blockedByMenu)return false;
        int action=event.getActionMasked(),index=event.getActionIndex(),id=event.getPointerId(index);
        if(action==MotionEvent.ACTION_DOWN||action==MotionEvent.ACTION_POINTER_DOWN) {
            float x=event.getX(index),y=event.getY(index);Control chosen=null;
            // Buttons must win over the full-screen floating-stick touch regions.
            for(Control c:controls)if(c.shape!=2&&c.pointer<0&&c.bounds.contains(x,y)){chosen=c;break;}
            if(chosen==null)for(Control c:controls)if(c.shape==2&&c.pointer<0&&c.bounds.contains(x,y)&&!(menu&&y<getHeight()*.72f)){chosen=c;break;}
            if(chosen==null)return fingers.size()>0;
            if(chosen.id==-1){cancelInputs();enabled(!shown);shown=!shown;layoutControls();return true;}
            chosen.pointer=id;chosen.down=true;fingers.put(id,chosen);
            if(chosen.shape==2){chosen.cx=(floating||chosen.id!=0)?x:chosen.cx;chosen.cy=(floating||chosen.id!=0)?y:chosen.cy;chosen.move(x,y);}
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
