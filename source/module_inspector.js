const inspector = (() => {
  const records = new Map();
  const audit = new Map(V.ledger.map(row => [row.id, row]));
  const optional = new Set(V.items.filter(t => t.optional).map(t => t.id));
  const bay = new Set(['Tattu_2200_6S','YourCee20','BuckTray','AuxBuck','ANS_H','Wago615','AuxDist','ZC7112A']);
  const covers = new Set(['Chassis','Deck','MID_fit']);
  const byMesh = new Map(), pickable = [], directoryButtons = new Map();
  const world = new THREE.Vector3(), ray = new THREE.Raycaster(), pointer = new THREE.Vector2();
  const pins = new Map();
  let selected = null, current = null, accent = null, isolated = false, labels = true;
  let hoverFrame = 0, lastPoint = null, gesture = null;

  for (const [group,entries] of Object.entries(V.modules)) {
    for (const [id,title,description] of entries) {
      const massId = ['XT100_Tyre','XT100_Rim'].includes(id) ? 'Wheel' : id;
      records.set(id,{id,title,description,group,row:audit.get(massId),instances:[]});
    }
  }

  function addMesh(object,id,place) {
    const record = records.get(id);
    const instance = {object,record,place};
    object.userData.partId=id;
    object.geometry.computeBoundingSphere();
    record.instances.push(instance);
    byMesh.set(object,instance);
    pickable.push(object);
  }

  function bodyPlace(t) {
    const [x,y,z] = t.pos;
    if (t.id==='Chassis') return '机身底部';
    if (t.id==='Deck') return '机身上方，向车头前伸';
    if (t.id.startsWith('B5')) return (y>0?'前':'后')+(x>0?'右侧':'左侧')+'髋座';
    const level = t.optional?'选装架':z<0?'下层机舱':'上层设备区';
    const lateral = Math.abs(x)<6?'中部':x>0?'右侧':'左侧';
    const lengthwise = Math.abs(y)<6?'中段':y>0?'前段':'后段';
    return level+' · '+lengthwise+lateral;
  }

  function instanceName(instance) {
    const peers = instance.record.instances.filter(x=>x.place===instance.place);
    return peers.length<2 ? instance.place : instance.place+' · 第 '+(peers.indexOf(instance)+1)+' 件';
  }

  function directory() {
    const query = $('partSearch').value.trim().toLowerCase();
    const list = $('partDirectory'), fragment = document.createDocumentFragment();
    directoryButtons.clear();
    let heading = '';
    for (const item of records.values()) {
      const text = [item.id,item.title,item.description,item.row.name,item.group].join(' ').toLowerCase().replace(/[-_\s]/g,'');
      if (query && !text.includes(query.replace(/[-_\s]/g,''))) continue;
      if (heading!==item.group) {
        const h=document.createElement('h3'); h.textContent=item.group; fragment.append(h); heading=item.group;
      }
      const button=document.createElement('button');
      button.type='button'; button.dataset.part=item.id; button.textContent=item.title;
      button.setAttribute('aria-pressed',String(item===selected));
      if (optional.has(item.id)) {
        const mark=document.createElement('small'); mark.textContent='选装'; button.append(mark);
        if(!cfg.endsWith('mid')) button.title='选择后显示加装 MID-360 的配置';
      }
      button.onclick=()=>choose(item);
      directoryButtons.set(item.id,button); fragment.append(button);
    }
    if (!directoryButtons.size) {
      const p=document.createElement('p'); p.textContent='没有匹配的部件，试试型号或用途。'; fragment.append(p);
    }
    list.replaceChildren(fragment);
  }

  function updateButton(reveal) {
    directoryButtons.forEach((button,key)=>button.setAttribute('aria-pressed',String(key===selected?.id)));
    if(!selected || !reveal) return;
    if(!directoryButtons.has(selected.id)) { $('partSearch').value=''; directory(); }
    const b=directoryButtons.get(selected.id), list=$('partDirectory');
    if(!b) return;
    const rect=b.getBoundingClientRect(), windowRect=list.getBoundingClientRect();
    if(rect.top<windowRect.top+22 || rect.bottom>windowRect.bottom) list.scrollTop+=rect.top-windowRect.top-list.clientHeight/2;
  }

  function panel() {
    $('partDetails').hidden=!selected;
    $('exploreHint').hidden=!!selected;
    if (!selected) return;
    $('partName').textContent=selected.title;
    $('partJob').textContent=selected.description;
    const related=harnessView.related(selected,current);
    $('partWires').hidden=!related.length;
    $('partWires').onclick=()=>harnessView.fromPart(selected.title,related);
    const row=selected.row;
    const wheel=['XT100_Tyre','XT100_Rim'].includes(selected.id);
    const mass=Number(row.g.toFixed(2));
    const qty=wheel?'4 套':(row.qty+' 件');
    $('partFacts').textContent=wheel?'胎与轮辋合计约 78 g/轮 · 商品标重 · 四轮':mass+' g/'+(selected.instances.length || row.qty>1?'件':'项')+' · '+row.grade+' · '+qty;
    const instances=$('partInstance');
    instances.replaceChildren();
    selected.instances.forEach((inst,index)=>instances.add(new Option(instanceName(inst),index)));
    if(current) instances.value=String(selected.instances.indexOf(current));
    $('partCopies').hidden=selected.instances.length<2 || !render;
    $('partPlace').textContent=current?instanceName(current):(!render?'使用目录查看部件说明':'质量账项目，未单独建模');
    $('partPlace').hidden=!!render && selected.instances.length>1;
    $('soloPart').hidden=!current || !render;
    $('soloPart').textContent=isolated?'返回总装':'只看此件';
    $('soloPart').setAttribute('aria-pressed',String(isolated));
  }

  function setAccent() {
    if(accent) { accent.parent.remove(accent); accent.material.dispose(); accent=null; }
    if(!current) return;
    const material=new THREE.MeshBasicMaterial({color:0xffb01e,transparent:true,opacity:.65,depthTest:false,depthWrite:false,side:THREE.DoubleSide});
    accent=new THREE.Mesh(current.object.geometry,material);
    accent.renderOrder=10;
    current.object.add(accent);
  }

  function setBay(value) {
    opened=value;
    $('open').classList.toggle('sel',value);
    $('open').setAttribute('aria-pressed',String(value));
    $('open').textContent=value?'合上机舱':'查看舱内';
  }

  function choose(item,instance=null,reveal=false) {
    if(!item) return;
    if(optional.has(item.id) && !cfg.endsWith('mid')) {
      cfg=cfg==='slice'?'slice_mid':'mid'; $('kit').value=cfg;
      summary();
    }
    if(bay.has(item.id)) setBay(true);
    if(covers.has(item.id)) setBay(false);
    selected=item;
    current=instance || item.instances[0] || null;
    if(!current) isolated=false;
    hideHover(); setAccent(); panel(); updateButton(reveal); draw();
  }

  function clear() {
    isolated=false; current=null; selected=null;
    hideHover(); setAccent(); panel(); updateButton(false); draw();
  }

  function toggleBay() {
    const next=!opened; isolated=false;
    if(selected && ((next && covers.has(selected.id)) || (!next && bay.has(selected.id)))) clear();
    setBay(next); panel(); draw();
  }

  function onKit() {
    if(selected && optional.has(selected.id) && !cfg.endsWith('mid')) clear();
    directory(); updateButton(true); draw();
  }

  function syncVisibility() {
    for(const instance of byMesh.values()) {
      const item=instance.record;
      instance.object.visible=isolated ? current===instance : ((!optional.has(item.id)||cfg.endsWith('mid'))&&(!opened||!covers.has(item.id)));
    }
  }

  function center(instance,target) {
    return target.copy(instance.object.geometry.boundingSphere.center).applyMatrix4(instance.object.matrixWorld);
  }

  function cameraFrame(defaultHalf,aspect) {
    const target = new THREE.Vector3(0,4,125);
    if(!isolated || !current) return {target,half:defaultHalf};
    center(current,target);
    const radius=Math.max(3,current.object.geometry.boundingSphere.radius);
    return {target,half:radius*1.48/Math.min(1,aspect)*soloZoomFactor};
  }

  let soloZoomFactor=1;
  function wheelZoom(delta) {
    if(!isolated) return false;
    soloZoomFactor=Math.max(.55,Math.min(3,soloZoomFactor*Math.exp(delta*.001)));
    return true;
  }

  function findAt(x,y) {
    if(!render) return null;
    const rect=render.domElement.getBoundingClientRect();
    pointer.set((x-rect.left)/rect.width*2-1,1-(y-rect.top)/rect.height*2);
    ray.setFromCamera(pointer,cam);
    const visible=pickable.filter(mesh=>mesh.visible);
    const hit=ray.intersectObjects(visible,false)[0];
    return hit ? byMesh.get(hit.object) : null;
  }

  function hideHover() {
    lastPoint=null;
    if(hoverFrame) cancelAnimationFrame(hoverFrame);
    hoverFrame=0; $('partHint').hidden=true; render?.domElement.classList.remove('over-part');
  }

  function hover(x,y) {
    if(harnessView.isActive())return;
    lastPoint=[x,y];
    if(hoverFrame) return;
    hoverFrame=requestAnimationFrame(()=>{
      hoverFrame=0;
      if(!lastPoint || gesture || run) { hideHover(); return; }
      const [px,py]=lastPoint, hit=findAt(px,py), tip=$('partHint');
      render.domElement.classList.toggle('over-part',!!hit);
      tip.hidden=!hit;
      if(!hit) return;
      tip.textContent=hit.record.title+' · '+instanceName(hit);
      const rect=$('scene').getBoundingClientRect();
      tip.style.left=Math.max(4,Math.min(rect.width-tip.offsetWidth-4,px-rect.left+12))+'px';
      tip.style.top=Math.max(4,Math.min(rect.height-tip.offsetHeight-4,py-rect.top+15))+'px';
    });
  }

  const svgNS='http://www.w3.org/2000/svg';
  function svg(tag) {return document.createElementNS(svgNS,tag);}
  function pin(id) {
    if(pins.has(id)) return pins.get(id);
    const group=svg('g'),line=svg('line'),dot=svg('circle'),rect=svg('rect'),title=svg('text');
    dot.setAttribute('r','3'); rect.setAttribute('rx','5'); rect.setAttribute('height','22'); title.setAttribute('dy','4');
    group.append(line,dot,rect,title);
    // Directory buttons provide the equivalent keyboard action for every marker.
    group.onpointerdown=e=>e.stopPropagation();
    group.onclick=e=>{e.stopPropagation(); const inst=group.instance; if(inst) choose(inst.record,inst,true);};
    $('pinLayer').append(group);
    const marker={group,line,dot,rect,title};
    pins.set(id,marker); return marker;
  }
  const outside=[['Jetson_Orin_Nano','Jetson'],['XT_M60','XT-M60'],['Astra_Pro_Plus','Astra Pro Plus'],['M01','髋电机'],['M02','轮电机'],['MC02','MC02']];
  const inside=[['Tattu_2200_6S','6S 电池'],['YourCee20','12 V 降压'],['AuxBuck','15 V 降压'],['ANS_H','主保险座'],['Wago615','主分线端子']];
  const scratch = new THREE.Vector3();

  function arrangePins(width,height) {
    for(const p of pins.values()) p.group.style.display='none';
    if(!labels || !render) return;
    const list=selected ? (current?[[selected.id,selected.title]]:[]) : [...(opened?inside:outside)];
    if(!selected && cfg.endsWith('mid') && !opened) list.push(['MID360','MID-360']);
    const sides=[[],[]];
    for (const [id,title] of list) {
      const item=records.get(id);
      const visible=item.instances.filter(it=>it.object.visible);
      if(!visible.length) continue;
      let best=visible[0],distance=Infinity;
      for(const it of visible) {
        const d=center(it,scratch).distanceToSquared(cam.position);
        if(d<distance) {distance=d;best=it;}
      }
      const inst=selected?current:best;
      const v=center(inst,world).project(cam), x=(v.x+1)*width/2,y=(1-v.y)*height/2;
      if(x<0||x>width||y<0||y>height) continue;
      sides[x<width/2?0:1].push({inst,title,x,y});
    }
    for(let side=0;side<2;side++) {
      const column=sides[side].sort((a,b)=>a.y-b.y);
      let last=6;
      column.forEach((p,index)=>{
        const upper=height-41-(column.length-index-1)*27;
        p.cy=Math.min(upper,Math.max(last+12,p.y)); last=p.cy+15;
      });
      for(const p of column) {
        const {group,line,dot,rect,title}=pin(p.inst.record.id);
        group.style.display='';group.instance=p.inst; group.classList.toggle('active',!!selected);
        title.textContent=p.title;
        const w=Math.min(width-16,Math.ceil(title.getComputedTextLength())+18);
        const left=side?width-w-9:9, edge=side?left:left+w;
        line.setAttribute('x1',p.x);line.setAttribute('y1',p.y);line.setAttribute('x2',edge);line.setAttribute('y2',p.cy);
        dot.setAttribute('cx',p.x);dot.setAttribute('cy',p.y);
        rect.setAttribute('x',left);rect.setAttribute('y',p.cy-11);rect.setAttribute('width',w);
        title.setAttribute('x',left+w/2);title.setAttribute('y',p.cy);
      }
    }
  }

  function bind() {
    directory(); panel();
    $('partSearch').oninput=directory;
    $('clearPart').onclick=clear;
    $('partInstance').onchange=e=>{
      if(selected) choose(selected,selected.instances[Number(e.target.value)]);
    };
    $('soloPart').onclick=()=>{isolated=!isolated;soloZoomFactor=1;hideHover();panel();draw();};
    $('open').onclick=toggleBay;
    $('pinToggle').onclick=()=>{
      labels=!labels;
      $('pinToggle').classList.toggle('sel',labels);$('pinToggle').setAttribute('aria-pressed',String(labels));draw();
    };
    if(!render) {
      $('pinToggle').disabled=$('open').disabled=true;
      $('viewerGuide').textContent='当前显示总装静态图。可在部件目录中搜索名称、型号并查看用途。';
      return;
    }
    const canvas=render.domElement;
    canvas.onpointerdown=e=>{
      if(!e.isPrimary || e.button!==0) return;
      hideHover(); canvas.setPointerCapture(e.pointerId);
      gesture={id:e.pointerId,startX:e.clientX,startY:e.clientY,x:e.clientX,y:e.clientY,moved:false};
    };
    canvas.onpointermove=e=>{
      if(!gesture) {if(e.pointerType==='mouse') hover(e.clientX,e.clientY); return;}
      if(e.pointerId!==gesture.id) return;
      const dx=e.clientX-gesture.x,dy=e.clientY-gesture.y;
      if(!gesture.moved && Math.hypot(e.clientX-gesture.startX,e.clientY-gesture.startY)<5) return;
      gesture.moved=true;gesture.x=e.clientX;gesture.y=e.clientY;
      canvas.classList.add('rotating');
      az-=dx*.009; el=Math.max(-.4,Math.min(1.56,el+dy*.009));draw();
    };
    canvas.onpointerup=e=>{
      if(!gesture || e.pointerId!==gesture.id) return;
      const clicked=!gesture.moved;gesture=null;canvas.classList.remove('rotating');
      if(clicked) {
        if(harnessView.pick(e.clientX,e.clientY))return;
        const hit=findAt(e.clientX,e.clientY);
        if(hit) choose(hit.record,hit,true); else if(selected) clear();
      }
    };
    canvas.onpointercancel=canvas.onlostpointercapture=()=>{gesture=null;canvas.classList.remove('rotating');};
    canvas.onpointerleave=hideHover;
    $('scene').addEventListener('wheel',e=>{
      e.preventDefault(); hideHover();
      if(!wheelZoom(e.deltaY)) zoom=Math.min(2.3,Math.max(.65,zoom*Math.exp(-e.deltaY*.001)));
      draw();
    },{passive:false});
  }

  function fromAudit(id) {
    const item=records.get(id==='Wheel'?'XT100_Tyre':id);
    if(item) {choose(item,null,true);$('viewer').scrollIntoView({block:'start'});}
  }

  return {resetForWires:()=>{setBay(false);clear();},addMesh,bodyPlace,bind,onKit,syncVisibility,cameraFrame,arrangePins,fromAudit,hideHover};
})();

