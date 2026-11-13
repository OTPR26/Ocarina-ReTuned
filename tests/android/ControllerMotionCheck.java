package org.triaevum.android;
public final class ControllerMotionCheck {
    static void require(boolean ok){if(!ok)throw new AssertionError();}
    public static void main(String[] args){
        ControllerMotionState state=new ControllerMotionState();
        long time=1_000_000_000L;
        require(state.sample(time)==null);
        state.update(false,new float[]{1,2,3},time,time,false);
        require(state.sample(time)==null);
        state.update(true,new float[]{4,5,6},time,time,false);
        double[] v=state.sample(time);
        require(v[0]==1 && v[1]==2 && v[2]==3 && v[3]==4 && v[4]==5 && v[5]==6);
        v[0]=999;require(state.sample(time)[0]==1);
        require(state.sample(time-1)==null && state.sample(time+250_000_001L)==null);
        state.update(true,new float[]{Float.NaN,0,0},time+1,time+1,false);require(state.sample(time+1)[3]==4);
        state.clear();require(state.sample(time)==null);
        state.update(false,new float[]{1,2,3},time,time,true);
        state.update(true,new float[]{4,5,6},time,time,true);
        v=state.sample(time);require(v[0]==-2 && v[1]==3 && v[2]==-1 && v[3]==-5 && v[4]==6 && v[5]==-4);
        state.update(true,new float[]{9,9,9},time-1,time-1,false);require(state.sample(time)[3]==-5);
        // Reproduce the Odin's future hardware clock and different clock rate.
        state.clear();
        long hardware=time+46_000_000_000_000L;
        state.update(false,new float[]{1,2,3},hardware,time,false);
        state.update(true,new float[]{4,5,6},hardware,time,false);
        require(state.sample(time)!=null && state.sample(time)[7]==time);
        state.update(true,new float[]{7,8,9},hardware+20_000_000L,time+10_000_000L,false);
        require(state.sample(time+10_000_000L)[3]==7);
        // Duplicate/out-of-order events must not refresh a stopped sensor.
        state.update(true,new float[]{9,9,9},hardware+20_000_000L,time+200_000_000L,false);
        require(state.sample(time+260_000_001L)==null);
        state.clear();
        // A different epoch behind local time works too.
        state.update(false,new float[]{1,2,3},1,time,false);
        state.update(true,new float[]{4,5,6},1,time,false);
        require(state.sample(time)!=null);
        state.update(false,new float[]{Float.NaN,0,0},2,time+200_000_000L,false);
        state.update(true,new float[]{4,5,6},2,time+200_000_000L,false);
        require(state.sample(time+250_000_001L)==null);
    }
}
