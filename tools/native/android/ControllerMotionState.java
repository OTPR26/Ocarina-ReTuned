package org.triaevum.android;

/** A complete, recent controller sample in SDL units and controller coordinates. */
final class ControllerMotionState {
    private final double[] values=new double[8];
    private final long[] eventTimes=new long[2];
    void clear(){java.util.Arrays.fill(values,0);java.util.Arrays.fill(eventTimes,0);}
    void update(boolean gyro,float[] input,long timestamp,long receivedAt,boolean switchAxes) {
        if(input.length<3 || timestamp<=0 || receivedAt<=0)return;
        for(int i=0;i<3;i++)if(!Float.isFinite(input[i]))return;
        int slot=gyro?3:0, time=gyro?7:6;
        int sensor=gyro?1:0;
        if(timestamp<=eventTimes[sensor] || receivedAt<values[time])return;
        if(switchAxes){values[slot]=-input[1];values[slot+1]=input[2];values[slot+2]=-input[0];}
        else for(int i=0;i<3;i++)values[slot+i]=input[i];
        eventTimes[sensor]=timestamp;
        // Controller hardware timestamps can have a different epoch or rate.
        // Use them for ordering only; freshness and consumers use arrival time.
        values[time]=receivedAt;
    }
    double[] sample(long now) {
        for(int i=6;i<8;i++)if(values[i]<=0 || now<values[i] || now-values[i]>250_000_000L)return null;
        return values.clone();
    }
}
