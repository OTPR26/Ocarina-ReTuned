package org.triaevum.android;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.hardware.input.InputManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.InputDevice;
import java.util.ArrayList;

/** Android's per-controller sensors, used only when SDL has no motion sample. */
final class ControllerMotion implements InputManager.InputDeviceListener {
    private final Handler main = new Handler(Looper.getMainLooper());
    private final InputManager input;
    private String name = "";
    private int vendor, product;
    private boolean active = true, closed;
    private SensorManager sensors;
    private SensorEventListener listener;
    private final ControllerMotionState state = new ControllerMotionState();

    ControllerMotion(Context context) {
        input = (InputManager)context.getSystemService(Context.INPUT_SERVICE);
        if(Build.VERSION.SDK_INT >= 31 && input != null) input.registerInputDeviceListener(this, main);
    }
    synchronized double[] sample(String requested, int vid, int pid) {
        if(Build.VERSION.SDK_INT < 31 || closed) return null;
        if(requested == null) requested = "";
        if(!requested.equals(name) || vendor != vid || product != pid) {
            name=requested;vendor=vid;product=pid;clear();main.post(this::refresh);
            android.util.Log.i("RetunedControllerMotion", "Selected controller: "+name+" vendor="+vid+" product="+pid);
        }
        // Use the same local clock for event arrival and freshness.
        long now=System.nanoTime();
        double[] result=active?state.sample(now):null;
        return result;
    }
    private void clear() { state.clear(); }
    synchronized void setActive(boolean enabled) {
        active=enabled;clear();main.post(this::refresh);
    }
    synchronized void close() {
        closed=true;active=false;clear();
        if(Build.VERSION.SDK_INT >= 31 && input != null) input.unregisterInputDeviceListener(this);
        refresh();
    }
    private static boolean gamepad(InputDevice device) {
        int sources=device.getSources();
        return (sources & InputDevice.SOURCE_GAMEPAD)==InputDevice.SOURCE_GAMEPAD ||
               (sources & InputDevice.SOURCE_JOYSTICK)==InputDevice.SOURCE_JOYSTICK;
    }
    private static String baseName(InputDevice device) {
        return device.getName().replaceFirst("(?i) IMU$", "").trim();
    }
    private static boolean hasSensors(InputDevice device) {
        SensorManager manager=device.getSensorManager();
        return manager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)!=null && manager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)!=null;
    }
    private synchronized void refresh() {
        if(sensors!=null && listener!=null) sensors.unregisterListener(listener);
        sensors=null;listener=null;clear();
        if(Build.VERSION.SDK_INT < 31 || closed || !active || name.isEmpty()) return;
        try {
            ArrayList<InputDevice> devices=new ArrayList<>();
            for(int id:InputDevice.getDeviceIds()){InputDevice d=InputDevice.getDevice(id);if(d!=null)devices.add(d);}
            InputDevice selected=null;
            for(InputDevice d:devices) if(gamepad(d) && d.getName().equals(name) && d.getVendorId()==vendor && d.getProductId()==product) {
                // SDL exposes name/VID/PID here, not Android's device ID. Ambiguous matches are unsafe.
                if(selected!=null)return;
                selected=d;
            }
            if(selected==null)return;
            InputDevice source=hasSensors(selected)?selected:null;
            if(source==null) {
                int controllers=0;
                for(InputDevice d:devices)if(gamepad(d)&&baseName(d).equalsIgnoreCase(baseName(selected)))controllers++;
                if(controllers!=1)return;
                for(InputDevice d:devices)if(d.getId()!=selected.getId() && (d.getVendorId()==vendor && d.getProductId()==product ||
                     vendor==0x2020 && product==0x0111 && d.getVendorId()==0x057e && d.getProductId()==0x2009) &&
                    baseName(d).equalsIgnoreCase(baseName(selected)) && hasSensors(d)) {
                    if(source!=null)return;
                    source=d;
                }
            }
            if(source==null)return;
            final boolean switchAxes=source.getVendorId()==0x057e && source.getProductId()==0x2009;
            sensors=source.getSensorManager();
            listener=new SensorEventListener() {
                public void onAccuracyChanged(Sensor sensor,int accuracy) {}
                public void onSensorChanged(SensorEvent event) {
                    synchronized(ControllerMotion.this) {
                        if(listener!=this || !active || closed || event.values.length<3)return;
                        boolean gyro=event.sensor.getType()==Sensor.TYPE_GYROSCOPE;
                        state.update(gyro,event.values,event.timestamp,System.nanoTime(),switchAxes);
                    }
                }
            };
            boolean gyro=sensors.registerListener(listener,sensors.getDefaultSensor(Sensor.TYPE_GYROSCOPE),10_000,main);
            boolean accel=sensors.registerListener(listener,sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER),10_000,main);
            if(!gyro || !accel){sensors.unregisterListener(listener);listener=null;clear();}
            android.util.Log.i("RetunedControllerMotion", "Controller sensors registered: "+(gyro&&accel));
        } catch(RuntimeException failure) {
            if(sensors!=null && listener!=null)sensors.unregisterListener(listener);
            listener=null;clear();
            android.util.Log.w("RetunedControllerMotion", "Controller sensors unavailable",failure);
        }
    }
    public void onInputDeviceAdded(int id){refresh();}
    public void onInputDeviceRemoved(int id){refresh();}
    public void onInputDeviceChanged(int id){refresh();}
}
