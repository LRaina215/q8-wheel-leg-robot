"""Compare two controllers on an actual paired rollout, with CAD geometry for display."""
import json,os,subprocess,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco as mj
import numpy as np
from pull_test import ROOT,ARCHIVE,rollout,get_actor,cases,configuration
import night_model
from render_replay import cad_scene

def timestamp(t):
    centis=round(t*100)
    return f'0:{centis//6000:02d}:{centis//100%60:02d}.{centis%100:02d}'

def main():
    night_model.SRC=Path(os.environ['PLATE_CODE'])
    ref=json.loads((ROOT/'outline_baseline.json').read_text())
    group=[x for x in ref if x['fork_s'] is not None]
    med=np.median([x['com_net_advance_mm'] for x in group])
    r=min(group,key=lambda x:abs(x['com_net_advance_mm']-med))
    j,dom=r['case'],r['domain']
    start=r['fork_s']
    bank=cases('soft_up',12,6031441+129*dom,0)
    c={k:v[j:j+1] for k,v in bank.items()}
    arms=['baseline','lift_pull']
    tracks=[]
    for arm in arms:
        rows=[]
        orig=mj.mj_step
        def hook(m,d):
            orig(m,d)
            k=round(d.time/.002)
            if k%10==0 and start-.201<=d.time<=start+1.201:
                ids=[m.geom(l+'_tyre').id for l in ('RL','RR')]
                z=np.abs(d.geom_xmat[ids,8]).clip(0,1)
                bottom=1000*(d.geom_xpos[ids,2]-.0175*z-.05*np.sqrt(1-z*z))
                rows.append((d.qpos.copy(),d.mocap_pos[0].copy(),d.time,d.subtree_com[m.body('chassis').id,0],bottom.min()))
        mj.mj_step=hook
        try:
            res=rollout()('soft_up',configuration('soft_up',dom,True),c,get_actor('original'),get_actor('phase'),'phase',arm)
        finally:mj.mj_step=orig
        archived=next(x for x in json.loads((ROOT/f'outline_{arm}.json').read_text()) if x['case']==j and x['domain']==dom)
        assert res['fork_s']==start and np.isclose(res['com_net_advance_mm'],archived['com_net_advance_mm'])
        tracks.append(rows)
    assert len(tracks[0])==len(tracks[1]) and len(tracks[0])>=69
    tree=ET.parse(ROOT/'code'/'q8_r5_fitted.xml').getroot()
    tree.find(".//geom[@name='step']").set('size','.8 .46 .24')
    m=cad_scene(tree)
    d=mj.MjData(m)
    cam=mj.MjvCamera()
    cam.azimuth=96;cam.elevation=-9;cam.distance=.98
    cam.lookat[:]=[float(c['edge'][0])+.13,0,.16]
    # 50 simulation frames per second, replayed at 25 fps.
    duration=len(tracks[0])/25
    sub=ROOT/'motion.ass'
    text=['[Script Info]','ScriptType: v4.00+','PlayResX: 1024','PlayResY: 360','[V4+ Styles]',
          'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
          'Style: Label,WenQuanYi Zen Hei,19,&H00FFFFFF,&H00FFFFFF,&H00202B2E,&H00202B2E,0,0,0,0,100,100,0,0,1,0,0,7,10,10,0,1','[Events]',
          'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def line(x,y,start_t,end_t,txt):
        text.append(f'Dialogue: 0,{timestamp(start_t)},{timestamp(end_t)},Label,,0,0,0,,{{\\pos({x},{y})}}{txt}')
    for col,title in enumerate(('原攀爬策略','调整俯仰、后轮抬高时加牵引')):
        line(512*col+12,3,0,duration,title)
        rows=tracks[col]
        base=min(rows,key=lambda w:abs(w[2]-start))[3]
        for i,(_,_,t,cx,h) in enumerate(rows):
            line(512*col+12,326,i/25,(i+1)/25,f'卡阶 {t-start:+.2f} s    质心位移 {(cx-base)*1000:+.0f} mm    后胎底 {h:.0f} mm')
    sub.write_text('\n'.join(text),encoding='utf8')
    output=ROOT/'front_pull_replay.mp4'
    cmd=['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1024x360','-r','25','-i','-','-vf',f'ass={sub}','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    enc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    with mj.Renderer(m,292,512) as ren:
        for pair in zip(*tracks):
            canvas=np.full((360,1024,3),[26,44,47],np.uint8)
            for col,(q,mc,*_) in enumerate(pair):
                d.qpos[:]=q;d.mocap_pos[0]=mc;mj.mj_forward(m,d)
                ren.update_scene(d,camera=cam)
                canvas[29:321,512*col:512*(col+1)]=ren.render()
            canvas[29:321,511:513]=[205,217,215]
            enc.stdin.write(canvas.tobytes())
    enc.stdin.close()
    if enc.wait():raise RuntimeError('encoding')
    print('sample',dom,j,start,'frames',len(tracks[0]),flush=True)
if __name__=='__main__':main()
