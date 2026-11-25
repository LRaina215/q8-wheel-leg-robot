const harnessView = (() => {
  const data=V.wiring, colors={'6S 动力':0xb84027,'12V 轮驱':0xe58a15,'15V 设备':0x8d59b9,'控制与编码':0x25846a,'CAN':0x1d79b5,'USB / 以太网':0x345da1,'腿部活动束':0x7b4b31};
  let active=true,solo=false,chosen='',group='',partFilter=null,shown=[],markers=[],meshes=new Map(),lastPose=999;
  const ray=new THREE.Raycaster(), pointer=new THREE.Vector2(), rings=7;
  const label=n=>data.nodes[n].label;
  function tubeGeometry(points,r,flat){
    const g=new THREE.BufferGeometry(),indices=[];
    g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(points.length*rings*3),3));
    for(let i=0;i<points.length-1;i++)for(let k=0;k<rings;k++){
      const a=i*rings+k,b=i*rings+(k+1)%rings;
      indices.push(a,b,a+rings,b,b+rings,a+rings);
    }
    g.setIndex(indices);writeTube(g,points,r,flat);return g;
  }
  function writeTube(g,pts,r,flat){
    const p=g.attributes.position.array, axis=new THREE.Vector3(), a=new THREE.Vector3(), b=new THREE.Vector3(), up=new THREE.Vector3(0,0,1);
    for(let i=0;i<pts.length;i++){
      const prev=pts[Math.max(0,i-1)],next=pts[Math.min(pts.length-1,i+1)];
      axis.set(next[0]-prev[0],next[1]-prev[1],next[2]-prev[2]).normalize();
      if(i===0){
        if(flat)up.set(1,0,0);
        else if(Math.abs(axis.z)>.96)up.set(0,1,0);
        a.copy(up);
      }
      a.addScaledVector(axis,-a.dot(axis));
      if(a.lengthSq()<.000001)a.crossVectors(axis,Math.abs(axis.z)<.9?new THREE.Vector3(0,0,1):new THREE.Vector3(0,1,0));
      a.normalize();b.crossVectors(axis,a);
      for(let k=0;k<rings;k++){
        const t=2*Math.PI*k/rings, u=r*Math.cos(t), v=(flat?.35:r)*Math.sin(t),j=(i*rings+k)*3;
        p[j]=pts[i][0]+u*a.x+v*b.x;p[j+1]=pts[i][1]+u*a.y+v*b.y;p[j+2]=pts[i][2]+u*a.z+v*b.z;
      }
    }
    g.attributes.position.needsUpdate=true;g.computeBoundingSphere();
  }
  function init(){
    if(!rig)return;
    for(const route of data.routes){
      const geo=tubeGeometry(route.points,route.dia/2,route.stock==='FFC');
      const mat=new THREE.MeshBasicMaterial({color:colors[route.group],side:THREE.DoubleSide});
      const m=new THREE.Mesh(geo,mat);m.userData.wire=route;rig.add(m);meshes.set(route.id,m);
    }
    for(const col of [0xe64229,0x126bdb]){
      const ball=new THREE.Mesh(new THREE.SphereGeometry(4.2,12,8),new THREE.MeshBasicMaterial({color:col,depthTest:false}));ball.renderOrder=12;rig.add(ball);markers.push(ball);
    }
  }
  function list(){
    if(!$('wireList'))return;
    const query=$('wireSearch').value.trim().toLowerCase();
    shown=data.routes.filter(r=>(!r.optional||cfg.endsWith('mid'))&&(!group||r.group===group)&&(!partFilter||partFilter.ids.includes(r.id))&&[r.id,label(r.a),label(r.b),r.cores].join(' ').toLowerCase().includes(query));
    $('wirePartReset').hidden=!partFilter;
    if(partFilter)$('wirePartReset').textContent=partFilter.title+'　×';
    $('wireList').replaceChildren(new Option('浏览本组全部走线',''),...shown.map(r=>new Option(r.id+'　'+label(r.a)+' → '+label(r.b),r.id)));
    if(!shown.some(r=>r.id===chosen))chosen='';
    $('wireList').value=chosen;details();
  }
  function details(){
    const r=data.routes.find(x=>x.id===chosen);
    $('wireCount').textContent=shown.length+' 条路线';
    $('wireDetail').hidden=!r;$('wireSolo').disabled=!r;
    $('wireSolo').textContent=solo?'显示同组走线':'仅显示选线';
    if(!r)return;
    $('wireEnds').textContent=r.id+'　'+label(r.a)+' → '+label(r.b);
    $('wireSignal').textContent=r.cores;
    $('wireLength').textContent='中心线 '+r.fixed_mm+' mm　·　'+(r.stock==='随电池'?'电池原配线':r.stock==='FFC'||r.stock==='网线'||r.stock==='成品'||r.stock==='USB数据'?'整线长度／估值 '+r.fitted+' mm':'备线 '+r.cut+' mm');
    $('wireNote').textContent=[r.detail,r.wire_note].filter(Boolean).join('。');
  }
  function switchMode(on){
    active=on;
    $('pinToggle').hidden=active;
    $('wirePanel').hidden=!active;$('partPanel').hidden=active;
    $('wireTab').setAttribute('aria-pressed',String(active));$('partTab').setAttribute('aria-pressed',String(!active));
    $('wireTab').classList.toggle('sel',active);$('partTab').classList.toggle('sel',!active);
    if(active){inspector.resetForWires();list();}
    draw();
  }
  function bind(){
    $('wirePartReset').onclick=()=>{partFilter=null;solo=false;list();draw();};
    for(const [g,color] of Object.entries(colors)){
      $('wireGroup').add(new Option(g,g));
      const button=document.createElement('button'),swatch=document.createElement('i');
      button.type='button';swatch.style.background='#'+color.toString(16).padStart(6,'0');
      button.append(swatch,document.createTextNode(g));
      button.onclick=()=>{$('wireGroup').value=group===g?'':g;$('wireGroup').dispatchEvent(new Event('change'));};
      $('wireLegend').append(button);
    }
    $('wireTab').onclick=()=>switchMode(true);$('partTab').onclick=()=>switchMode(false);
    $('wireGroup').onchange=e=>{group=e.target.value;solo=false;list();draw();};
    $('wireSearch').oninput=()=>{solo=false;list();draw();};
    $('wireList').onchange=e=>{chosen=e.target.value;if(!chosen)solo=false;details();draw();};
    $('wireSolo').onclick=()=>{solo=!solo;details();draw();};
    $('wireGhost').onchange=draw; switchMode(true);
  }
  function update(deg){
    if(!rig)return;
    for(const [id,m] of meshes){
      const r=m.userData.wire;
      m.visible=active&&shown.includes(r)&&(!solo||!chosen||id===chosen);
      if(!m.visible)continue;
      if(r.frames && (Math.abs(deg-lastPose)>.01||!m.userData.initial||Math.abs(deg-m.userData.pose)>.01)){
        const f=Math.max(0,Math.min(69,deg+36)),a=Math.floor(f),t=f-a,b=Math.min(69,a+1);
        const pts=r.frames[a].map((v,j)=>v.map((x,k)=>x+(r.frames[b][j][k]-x)*t));
        writeTube(m.geometry,pts,r.dia/2,false);m.userData.tail=pts[pts.length-1];m.userData.initial=true;m.userData.pose=deg;
      }
      m.material.transparent=!!chosen && id!==chosen;m.material.opacity=m.material.transparent?.18:1;
      m.material.depthWrite=!m.material.transparent;m.renderOrder=id===chosen?5:1;
    }
    lastPose=deg;
    const m=meshes.get(chosen);markers.forEach((ball,i)=>{
      ball.visible=!!(active&&m?.visible);if(!ball.visible)return;
      const r=m.userData.wire,p=i===0?r.points[0]:(m.userData.tail||r.points[r.points.length-1]);ball.position.set(...p);
    });
    rig.traverse(o=>{
      if(!o.userData.partId)return;
      const ghost=active&&$('wireGhost').checked;
      if(ghost!==o.userData.ghost){
        o.userData.ghost=ghost;o.material.transparent=ghost;o.material.opacity=ghost?.19:1;o.material.depthWrite=!ghost;
      }
    });
    $('pinLayer').style.visibility=active?'hidden':'visible';
  }
  function pick(x,y){
    if(!active||!render)return false;
    const rect=render.domElement.getBoundingClientRect();pointer.set(2*(x-rect.left)/rect.width-1,1-2*(y-rect.top)/rect.height);
    ray.setFromCamera(pointer,cam);
    const hit=ray.intersectObjects([...meshes.values()].filter(m=>m.visible),false)[0];
    if(hit){chosen=hit.object.userData.wire.id;$('wireList').value=chosen;details();draw();}
    return true;
  }
  function part(id){switchMode(false);inspector.fromAudit(id);}
  function related(item,instance){
    const p=instance?.object.position||{x:0,y:0},place=instance?.place||'';
    const corner=(place.includes('前')?'F':'R')+(place.includes('左')?'L':'R');
    const pins={
      Tattu_2200_6S:/^(BAT|BAL|XT$)/,ANS_H:/^F40/,Wago615:p.y<60?/^HP/:/^HN/,AuxDist:p.x<30?/^AP/:/^AN/,
      ZC7112A:p.x<0?/^Fw/:/^Fe/,YourCee20:p.y<0?/^B[io]/:/^F[io]/,AuxBuck:/^A[io]/,
      Driver:p.x<0?/^L(V|M|ctrl)/:/^R(V|M|ctrl)/,TXS0108E:/^TX/,FFC24_65:/^(FFC1|Break|Bhdr)/,
      MC02:/^(MC|FFC1|[LR](pwm|can)$)/,Jetson_Orin_Nano:/^J(DC|LAN|USB)/,USBnet:/^Net/,
      Astra_Pro_Plus:/^AST$/,XT_M60:/^XT(tail|split)$/,MID360:/^MID/,
      M01:new RegExp('^'+corner+'([+-]|can)$'),M02:new RegExp('^'+corner+'(root|motor)$')
    };
    const re=pins[item.id];
    const rows=data.routes.filter(r=>re?(re.test(r.a)||re.test(r.b)):
      item.id==='LegHarness'?!!r.frames:item.id==='MidHarness'?r.optional:item.id==='Loom'?(!r.optional&&!r.frames):false);
    return rows.map(r=>r.id);
  }
  function fromPart(title,ids){
    chosen='';group='';solo=false;$('wireSearch').value='';$('wireGroup').value='';
    partFilter={title,ids};switchMode(true);
  }
  return {init,bind,list,update,pick,part,related,fromPart,isActive:()=>active};
})();
