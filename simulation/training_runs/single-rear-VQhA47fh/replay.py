"""Render an independently replayed successful held-out trial with the assembly CAD."""
import json,os,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco as mj
import numpy as np
import night_model
from single_rear import OUT,engine,cases,configuration,get_actor
from render_replay import cad_scene

def stamp(t):
    cs=round(t*100)
    return f'0:{cs//6000:02d}:{cs//100%60:02d}.{cs%100:02d}'
def run():
    night_model.SRC=Path(os.environ['PLATE_CODE'])
    successes=[]
    for seed in (8835173,1907419):
        for r in json.loads((OUT/f'approach_settle_{seed}.json').read_text()):
            if r['score']['stable'] and r['score']['reached']:successes.append((seed,r))
    md=np.median([r['score']['rear_margin_mm'] for _,r in successes])
    seed,r=min(successes,key=lambda item:abs(item[1]['score']['rear_margin_mm']-md))
    dom,case=r['domain'],r['case'];bank=cases('soft_up',12,seed+dom*129,0)
    c={k:v[case:case+1] for k,v in bank.items()}
    frames=[];orig=mj.mj_step
    def capture(m,d):
        orig(m,d)
        if round(d.time/.002)%10==0:frames.append((d.qpos.copy(),d.mocap_pos[0].copy(),float(d.time)))
    mj.mj_step=capture
    try:got=engine()('soft_up',configuration('soft_up',dom,True),c,get_actor('original'),get_actor('phase'),'phase','settle')
    finally:mj.mj_step=orig
    for k,v in r['score'].items():assert np.isclose(got['score'][k],v),k
    tree=ET.parse(os.environ['DISPLAY_XML']).getroot()
    tree.find(".//geom[@name='step']").set('size','.8 .46 .24')
    m=cad_scene(tree);d=mj.MjData(m)
    lead=r['lead'];other='RR' if lead=='RL' else 'RL'
    s=1 if lead=='RL' else -1
    cams=[]
    for az,el,dist in [(-92*s,-10,1.0),(-30*s,-29,.98)]:
        cam=mj.MjvCamera();cam.azimuth=az;cam.elevation=el;cam.distance=dist;cams.append(cam)
    ch=m.body('chassis').id
    sub=OUT/'video.ass'
    lines=['[Script Info]','ScriptType: v4.00+','PlayResX: 1024','PlayResY: 372','[V4+ Styles]',
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding, ScaleX, ScaleY',
           'Style: A,WenQuanYi Zen Hei,18,&H00FFFFFF,&H00FFFFFF,&H00202B2E,&H00202B2E,0,0,0,0,0,0,1,0,0,7,8,8,0,1,100,100','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    def label(x,y,t,end,txt):
        lines.append(f'Dialogue: 0,{stamp(t)},{stamp(end)},A,,0,0,0,,{{\\pos({x},{y})}}{txt}')
    end=len(frames)/25
    name='左后轮' if s==1 else '右后轮'
    label(12,2,0,end,'15 厘米直角台阶　｜　仿真侧视 · 半速回放')
    label(522,2,0,end,'后方斜视　｜　橙色为先行后轮，蓝色为另一后轮')
    edge=r['edge']
    for i,(q,mc,t) in enumerate(frames):
        d.qpos[:]=q;d.mocap_pos[0]=mc;mj.mj_forward(m,d)
        dx=[1000*(d.geom_xpos[m.geom(l+'_tyre').id,0]-edge) for l in (lead,other)]
        age=t-r['fork_s']
        phase='前轮接近、搭上台面'
        if age>=0:phase='调整俯仰和侧倾，抬起'+name
        if age>=r['second_command_s']:phase='先行后轮承重，收起另一条后腿'
        if age>=r['level_command_s']:phase='恢复对称姿态，减速停车'
        label(12,325,i/25,(i+1)/25,f'{t:.2f} s　{phase}')
        label(522,325,i/25,(i+1)/25,f'轮心相对台沿　先行 {dx[0]:+.0f} mm　另一只 {dx[1]:+.0f} mm')
    sub.write_text('\n'.join(lines),encoding='utf8')
    dest=OUT/'single_rear_15cm.mp4'
    enc=subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1024x372','-r','25','-i','-','-vf',f'ass={sub}','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdin=subprocess.PIPE)
    with mj.Renderer(m,292,512) as ren:
        for q,mc,t in frames:
            d.qpos[:]=q;d.mocap_pos[0]=mc;mj.mj_forward(m,d)
            canvas=np.full((372,1024,3),[26,44,47],np.uint8)
            for i,cam in enumerate(cams):
                cam.lookat[:]=[.84*d.xpos[ch,0]+.16*edge,d.xpos[ch,1],.55*d.xpos[ch,2]+.08]
                ren.update_scene(d,camera=cam)
                for leg,color in [(lead,[1,.47,.04,1]),(other,[.08,.64,1,1])]:
                    center=d.geom_xpos[m.geom(leg+'_tyre').id]
                    side=1. if leg=='RL' else -1.
                    pos=center+side*.029*d.xmat[ch].reshape(3,3)[:,1]
                    scene=ren.scene;g=scene.geoms[scene.ngeom]
                    mj.mjv_initGeom(g,mj.mjtGeom.mjGEOM_SPHERE,np.full(3,.014),pos,np.eye(3).reshape(-1),np.array(color,np.float32))
                    scene.ngeom+=1
                canvas[29:321,i*512:(i+1)*512]=ren.render()
            canvas[29:321,511:513]=[201,210,209]
            enc.stdin.write(canvas.tobytes())
    enc.stdin.close()
    if enc.wait():raise RuntimeError('encode')
    (OUT/'video_case.json').write_text(json.dumps(dict(seed=seed,domain=dom,case=case,fps=25,frames=len(frames),**{k:r[k] for k in ('fork_s','lead','lead_load_s','mate_load_s','second_command_s','level_command_s','score')})))
    print(seed,dom,case,len(frames),flush=True)
if __name__=='__main__':run()
