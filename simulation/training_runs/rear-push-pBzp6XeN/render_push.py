"""Render a repeatable native success of the simultaneous tuck on held-out terrain."""
from pathlib import Path
import os,json,subprocess,xml.etree.ElementTree as ET
import numpy as np
import mujoco as mj
from rear_push import OUT,simulate,cases,get_actor,night_model
from render_replay import cad_scene

def ts(seconds):
    n=round(100*seconds)
    return f'0:{n//6000:02d}:{n//100%60:02d}.{n%100:02d}'
def run():
    night_model.SRC=Path(os.environ['PLATE_CODE'])
    seed=4619281
    name='near_tworear'
    saved=json.loads((OUT/f'{name}_{seed}.json').read_text())
    row=next(x for x in saved if x.get('synchronous_landing_command') and x['score']['reached'] and x['score']['stable'])
    dom=row['domain'];case=row['case']
    c={k:v[case:case+1] for k,v in cases('soft_up',12,seed+129*dom,0.).items()}
    frames=[];f=np.zeros(6);hist=np.zeros(4);step=mj.mj_step
    def capture(m,d):
        step(m,d)
        floor=m.geom('ground').id;platform=m.geom('step').id
        wheels=[m.geom(l+'_tyre').id for l in ('FL','FR','RL','RR')]
        for ci,ct in enumerate(d.contact):
            g,h=int(ct.geom1),int(ct.geom2)
            if h in (floor,platform):g,h=h,g
            if h not in wheels:continue
            i=wheels.index(h)
            if i<2 and (g!=platform or abs(ct.frame[2])<=.85):continue
            if i>=2 and g!=floor:continue
            mj.mj_contactForce(m,d,ci,f)
            hist[i]+=max(0.,f[0])/5.
        if round(d.time/.002)%5==0:
            frames.append((d.qpos.copy(),d.mocap_pos[0].copy(),float(d.time),hist.copy()))
            hist.fill(0)
    mj.mj_step=capture
    try: got=simulate(c,dom,get_actor('original'),get_actor('phase'),name)
    finally:mj.mj_step=step
    assert all(np.isclose(got['score'][k],v) for k,v in row['score'].items())
    assert np.isclose(got['thrust']['rear_floor_Jx'],row['thrust']['rear_floor_Jx'])
    tree=ET.parse(os.environ['DISPLAY_XML']).getroot()
    tree.find(".//geom[@name='step']").set('size','.8 .46 .24')
    m=cad_scene(tree);d=mj.MjData(m);ch=m.body('chassis').id
    cams=[]
    for az,el in [(-91,-7),(-31,-24)]:
        cam=mj.MjvCamera();cam.azimuth=az;cam.elevation=el;cam.distance=1.0;cams.append(cam)
    ass=OUT/'push.ass'
    lines=['[Script Info]','ScriptType: v4.00+','PlayResX: 1024','PlayResY: 385','[V4+ Styles]',
       'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
       'Style: A,WenQuanYi Zen Hei,19,&H00FFFFFF,&H00FFFFFF,&H00202B2E,&H00202B2E,0,0,0,0,100,100,0,0,1,0,0,7,8,8,0,1','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def label(x,y,b,e,txt):
        lines.append(f'Dialogue: 0,{ts(b)},{ts(e)},A,,0,0,0,,{{\\pos({x},{y})}}{txt}')
    end=len(frames)/25
    label(12,2,0,end,'15 厘米直角台阶　｜　整车侧视　·　四分之一速')
    label(522,2,0,end,'后方斜视　｜　两条后腿同步收起')
    for i,(q,mc,t,load) in enumerate(frames):
        d.qpos[:]=q;d.mocap_pos[0]=mc;mj.mj_forward(m,d)
        dx=[1000*(d.geom_xpos[m.geom(l+'_tyre').id,0]-row['edge']) for l in ('RL','RR')]
        age=t-row['push_s']
        if age<0:phase='前轮上台，向前牵引'
        elif age<.12:phase='两条后腿屈曲，准备蹬地'
        elif age<.28:phase='两条后腿蹬伸，前轮继续拉'
        elif t<max(row['rear_supported']):phase='两条后腿同步收起、向台面移送'
        else:phase='两后轮已建立支撑，四轮回正停车'
        label(12,325,i/25,(i+1)/25,f'{t:.2f} s　{phase}')
        label(522,325,i/25,(i+1)/25,f'后轮心越沿　左 {dx[0]:+.0f} mm　右 {dx[1]:+.0f} mm')
        label(12,352,i/25,(i+1)/25,f'后轮压下层地面　{sum(load[2:]):.0f} N　　　前轮压上层台面　{sum(load[:2]):.0f} N')
    ass.write_text('\n'.join(lines),encoding='utf8')
    dest=OUT/'双后腿蹬地.mp4'
    enc=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1024x385','-r','25','-i','-','-vf',f'ass={ass},pad=1024:386:0:0','-c:v','libx264','-threads','2','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdin=subprocess.PIPE)
    with mj.Renderer(m,292,512) as ren:
        for q,mc,t,load in frames:
            d.qpos[:]=q;d.mocap_pos[0]=mc;mj.mj_forward(m,d)
            img=np.full((385,1024,3),[26,44,47],np.uint8)
            for i,cam in enumerate(cams):
                cam.lookat[:]=[.84*d.xpos[ch,0]+.16*row['edge'],d.xpos[ch,1],.55*d.xpos[ch,2]+.08]
                ren.update_scene(d,camera=cam);img[29:321,i*512:(i+1)*512]=ren.render()
            img[29:321,511:513]=[201,210,209];enc.stdin.write(img.tobytes())
    enc.stdin.close()
    if enc.wait():raise RuntimeError('encoding')
    (OUT/'video_case.json').write_text(json.dumps(dict(seed=seed,frames=len(frames),**row),allow_nan=False))
if __name__=='__main__':run()
