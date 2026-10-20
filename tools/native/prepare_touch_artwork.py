"""Translate Ship's Android D-pad vector into CoreGraphics paths for UIKit."""
from pathlib import Path
import math,re,sys,xml.etree.ElementTree as ET

def convert(data):
    tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',data)
    out=[];i=0;x=y=sx=sy=0.;cmd=''
    def emit(name,*values):out.append('CGPath'+name+'(p,nullptr,'+','.join(f'{v:.8f}' for v in values)+');')
    while i<len(tokens):
        if tokens[i].isalpha():cmd=tokens[i];i+=1
        op=cmd.upper();relative=cmd.islower()
        if op=='Z':out.append('CGPathCloseSubpath(p);');x,y=sx,sy;cmd='';continue
        count={'M':2,'L':2,'H':1,'V':1,'A':7}[op];v=list(map(float,tokens[i:i+count]));i+=count
        if op in ('M','L'):
            nx=v[0]+(x if relative else 0);ny=v[1]+(y if relative else 0)
            emit('MoveToPoint' if op=='M' else 'AddLineToPoint',nx,ny);x,y=nx,ny
            if op=='M':sx,sy=x,y;cmd='l' if relative else 'L'
        elif op=='H':x=v[0]+(x if relative else 0);emit('AddLineToPoint',x,y)
        elif op=='V':y=v[0]+(y if relative else 0);emit('AddLineToPoint',x,y)
        else:
            rx,ry,rotation,large,sweep,nx,ny=v;nx+=x if relative else 0;ny+=y if relative else 0
            if not rx or not ry:emit('AddLineToPoint',nx,ny);x,y=nx,ny;continue
            phi=math.radians(rotation);c=math.cos(phi);s=math.sin(phi)
            a=c*(x-nx)/2+s*(y-ny)/2;b=-s*(x-nx)/2+c*(y-ny)/2
            scale=max(1,math.sqrt(a*a/rx**2+b*b/ry**2));rx*=scale;ry*=scale
            k=(-1 if bool(large)==bool(sweep) else 1)*math.sqrt(max(0,(rx**2*ry**2-rx**2*b*b-ry**2*a*a)/(rx**2*b*b+ry**2*a*a)))
            cx0=k*rx*b/ry;cy0=-k*ry*a/rx;cx=c*cx0-s*cy0+(x+nx)/2;cy=s*cx0+c*cy0+(y+ny)/2
            t=math.atan2((b-cy0)/ry,(a-cx0)/rx);end=math.atan2((-b-cy0)/ry,(-a-cx0)/rx);delta=(end-t)%(2*math.pi)
            if not sweep:delta-=2*math.pi
            steps=max(1,math.ceil(abs(delta)/(math.pi/2)));step=delta/steps
            def point(q):return (cx+c*rx*math.cos(q)-s*ry*math.sin(q),cy+s*rx*math.cos(q)+c*ry*math.sin(q))
            def derivative(q):return (-c*rx*math.sin(q)-s*ry*math.cos(q),-s*rx*math.sin(q)+c*ry*math.cos(q))
            for _ in range(steps):
                p0=point(t);p1=point(t+step);d0=derivative(t);d1=derivative(t+step);f=4/3*math.tan(step/4)
                emit('AddCurveToPoint',p0[0]+f*d0[0],p0[1]+f*d0[1],p1[0]-f*d1[0],p1[1]-f*d1[1],*p1);t+=step
            x,y=nx,ny
    return '\n'.join(out)

def generate(destination):
    root=ET.parse(Path(__file__).parent/'android/drawable/retuned_touch_cross.xml').getroot()
    paths=[p.attrib['{http://schemas.android.com/apk/res/android}pathData'] for p in root]
    cases='\n'.join(f'case {i}:\n{convert(path)}\nbreak;' for i,path in enumerate(paths))
    Path(destination).write_text('#pragma once\n#include <CoreGraphics/CoreGraphics.h>\ninline CGPathRef RetunedDpadPath(unsigned part) {\nCGMutablePathRef p=CGPathCreateMutable();switch(part){\n'+cases+'\n}return p;\n}\n')
if __name__=='__main__':generate(sys.argv[1])
