const {chromium}=require('C:/Users/Li/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path=require('path'),url=require('url'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 try{
  const page=await browser.newPage({viewport:{width:1370,height:1010}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url.pathToFileURL(path.join(root,'整车动作与载荷.html')).href);
  await page.waitForFunction(()=>window.q8?.ready,null,{timeout:25000});
  assert.equal(await page.locator('#wireList option').count(),72);
  await page.screenshot({path:path.join(root,'data','HTML_整车线束.png')});
  await page.selectOption('#wireGroup','腿部活动束');assert.equal(await page.locator('#wireList option').count(),5);
  const hit=await page.evaluate(()=>{
    const box=render.domElement.getBoundingClientRect(),wires=rig.children.filter(o=>o.userData.wire&&o.visible);
    const line=wires.find(o=>o.userData.wire.id==='W50'),positions=line.geometry.attributes.position,ray=new THREE.Raycaster();
    for(let i=70;i<positions.count;i+=21){
      const v=new THREE.Vector3().fromBufferAttribute(positions,i).applyMatrix4(line.matrixWorld).project(cam);
      ray.setFromCamera(new THREE.Vector2(v.x,v.y),cam);
      if(ray.intersectObjects(wires,false)[0]?.object===line)return [box.left+(v.x+1)*box.width/2,box.top+(1-v.y)*box.height/2];
    }
  });
  assert.ok(hit);await page.mouse.click(...hit);assert.equal(await page.locator('#wireList').inputValue(),'W50');
  await page.selectOption('#wireList','W50');await page.click('#wireSolo');
  assert.match(await page.locator('#wireEnds').innerText(),/FL/);
  const tail=async t=>page.evaluate(t=>{q8.set(t);return rig.children.find(o=>o.userData.wire?.id==='W50').userData.tail;},t);
  const travel=[];for(const t of [0,240,400,540,620,700,780,860,950])travel.push(await tail(t));
  const span=Math.max(...travel.map(p=>p[2]))-Math.min(...travel.map(p=>p[2]));assert.ok(span>85,'modeled moving-end stroke '+span);
  const count=await page.evaluate(()=>rig.children.filter(o=>o.userData.wire&&o.visible).length);assert.equal(count,1);
  await page.screenshot({path:path.join(root,'data','HTML_活动束.png')});
  await page.click('#wireSolo');await page.selectOption('#wireGroup','');await page.selectOption('#kit','slice_mid');assert.equal(await page.locator('#wireList option').count(),78);
  await page.locator('#wireSearch').fill('MID');assert.ok((await page.locator('#wireList option').count())>=5);
  await page.selectOption('#kit','slice');await page.locator('#wireSearch').fill('');
  await page.click('#partTab');await page.locator('#partSearch').fill('优信');await page.locator('#partDirectory button[data-part="YourCee20"]').click();
  assert.equal(await page.locator('#partInstance option').count(),2);
  await page.locator('#soloPart').click();
  assert.equal(await page.evaluate(()=>rig.children.filter(o=>o.visible&&o.userData.partId==='YourCee20').length),1);
  await page.click('#partWires');assert.equal(await page.locator('#wireList option').count(),5);
  assert.ok(await page.locator('#wirePartReset').isVisible());await page.click('#wirePartReset');
  assert.equal(await page.locator('#wireList option').count(),72);
  await page.selectOption('#height','20');assert.match(await page.locator('#limits').innerText(),/20 mm/);
  await page.locator('#play').click();await page.waitForTimeout(250);await page.locator('#play').click();
  const price=page.locator('#buy tr').filter({hasText:'优信双路'}).locator('input');
  assert.equal(await price.inputValue(),'16');
  await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<innerWidth+2));
  assert.deepEqual(errors,[]);console.log('Offline WebGL, 71/77 circuits, four moving harnesses, optional kit, category filters, module instances, pose slider, playback, narrow display and pricing verified.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
