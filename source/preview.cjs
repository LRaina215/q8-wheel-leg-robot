const {chromium} = require('C:/Users/Li/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs'),path=require('path'),url=require('url'),os=require('os');
const root=path.resolve(__dirname,'..'), dest=path.join(os.tmpdir(),'q8_whole_frames');
(async()=>{
fs.mkdirSync(dest,{recursive:true});
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--disable-dev-shm-usage']});
try{
const page=await browser.newPage({viewport:{width:1250,height:920},deviceScaleFactor:1});let errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto(url.pathToFileURL(path.join(root,'整车动作与载荷.html')).href);
await page.waitForFunction(()=>window.q8 && window.q8.ready,{},{timeout:20000});
// Exercise both picking directions, including moving legs, hidden equipment, and ledger-only entries.
const part=id=>page.locator('#partDirectory button[data-part="'+id+'"]');
await page.locator('#partSearch').fill('12V');await part('Daygreen_B30').click();
if(await page.locator('#open').getAttribute('aria-pressed')!=='true'||!(await page.locator('#partJob').innerText()).includes('DRI0041'))throw Error('lower bay identification');
await page.locator('#soloPart').click();
if(await page.evaluate(()=>render.domElement.clientWidth<=0 || rig.children.filter(x=>x.visible && x.isMesh).length!==1))throw Error('isolate hidden converter');
await page.locator('#soloPart').click();await page.locator('#clearPart').click();await page.locator('#open').click();
await page.locator('#partSearch').fill('');
await part('M01').click();await page.selectOption('#partInstance',{label:'右后轮腿'});
if(await page.locator('#partInstance option:checked').innerText()!=='右后轮腿')throw Error('corner');
await page.evaluate(()=>q8.set(780));
if(!await page.locator('#pinLayer g.active:visible').count())throw Error('pose pin');
await page.locator('#clearPart').click();
await part('MID360').click();
if(await page.locator('#kit').inputValue()!=='slice_mid')throw Error('selected optional kit');
await page.selectOption('#kit','slice');
if(await page.locator('#partDetails').isVisible())throw Error('suppressed radar selection');
await page.locator('#partSearch').fill('SSD');await part('SSD').click();
if(!(await page.locator('#partPlace').innerText()).includes('未单独建模')||await page.locator('#soloPart').isVisible())throw Error('unmodelled item');
await page.locator('#clearPart').click();await page.locator('#partSearch').fill('');await page.evaluate(()=>q8.set(0));
const point=await page.evaluate(()=>{
  const box=render.domElement.getBoundingClientRect(),ray=new THREE.Raycaster(),all=[];
  rig.traverse(o=>{if(o.userData.partId&&o.visible)all.push(o)});
  // Pick a visible patch of tyre with the actual mouse; avoid leader-label rectangles at the scene edges.
  for(let y=40;y<box.height-28;y+=8)for(let x=118;x<box.width-118;x+=8){
    ray.setFromCamera(new THREE.Vector2(2*x/box.width-1,1-2*y/box.height),cam);
    const hit=ray.intersectObjects(all,false)[0];if(hit?.object.userData.partId==='XT100_Tyre')return [box.x+x,box.y+y];
  }
});
if(!point)throw Error('visible tyre');await page.mouse.move(...point);await page.waitForFunction(()=>!document.querySelector('#partHint').hidden);
await page.mouse.click(...point);
if(!(await page.locator('#partName').innerText()).includes('轮胎')||!(await page.locator('#partFacts').innerText()).includes('合计约 78'))throw Error('mesh picking');
await page.mouse.move(...point);await page.mouse.down();await page.mouse.move(point[0]+28,point[1]+18,{steps:6});await page.mouse.up();
if(!(await page.locator('#partName').innerText()).includes('轮胎'))throw Error('drag changed selection');
await page.locator('#clearPart').click();await page.locator('[data-view=iso]').click();
const svgTag=page.locator('#pinLayer g:visible').filter({hasText:'XT-M60'});await svgTag.locator('text').click();
if(!(await page.locator('#partName').innerText()).includes('XT-M60'))throw Error('label picking');
await page.locator('#clearPart').click();
const priceReport=JSON.parse(fs.readFileSync(path.join(root,'data','首车造价.json'),'utf8'));
const wheelRow=page.locator('#buy tr').filter({hasText:'B30-24-12A'});
const wheelPrice=wheelRow.locator('input');
if(await wheelPrice.inputValue()!=='78')throw Error('30 A quote');
await wheelPrice.fill('79');
if(!(await page.locator('#quote').innerText()).includes((priceReport.total+1).toFixed(2)))throw Error('quote sum');
await wheelPrice.fill('78');
await page.selectOption('#height','20');if(!(await page.locator('#limits').innerText()).includes('20 mm'))throw Error('20 mm trajectory');await page.selectOption('#height','30');
const details=()=>page.locator('#tag').innerText();
for(const t of [0,490,670,845,1000]){await page.evaluate(t=>q8.set(t),t);console.log(t,await details());}
await page.evaluate(()=>{q8.set(485);document.activeElement.blur();window.scrollTo({top:0,behavior:'instant'});});await page.screenshot({path:path.join(root,'data','HTML_整车桌面.png')});
const analysis=JSON.parse(fs.readFileSync(path.join(root,'data','analysis.json'),'utf8'));
await page.selectOption('#kit','mid');if(!(await page.locator('#mass').innerText()).includes(analysis.mid.mass.toFixed(2)))throw Error('kit');
await page.locator('#open').click();await page.locator('[data-view=top]').click();
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(dest,'mobile.png')});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('mobile overflow');
await page.selectOption('#kit','slice_mid');if(!(await page.locator('#mass').innerText()).includes(analysis.slice_mid.mass.toFixed(2)))throw Error('sliced kit');await page.selectOption('#kit','slice');await page.locator('#open').click();await page.locator('[data-view=iso]').click();await page.setViewportSize({width:960,height:800});await page.evaluate(()=>q8.set(0));
await page.locator('#play').click();await page.waitForTimeout(260);await page.locator('#play').click();if(+(await page.locator('#range').inputValue())<=0)throw Error('play');
for(let k=0;k<35;k++){await page.evaluate(t=>q8.set(t),Math.round(1000*k/34));await page.locator('#scene').screenshot({path:path.join(dest,'f'+String(k).padStart(2,'0')+'.png')});}
if(errors.length)throw Error(errors.join('; '));console.log('verified webgl renderer, all poses, mobile, kit, views, play and frames, table rows',await page.locator('#buy tr').count());
} finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
