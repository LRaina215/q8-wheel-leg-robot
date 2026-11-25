from pathlib import Path
S=Path(__file__).parent
for file in [S/'r5_view.html',S.parent/'R5_装配与运动审阅.html']:
 t=file.read_text(encoding='utf-8-sig')
 a='<button id="ride">巡航</button>'
 b='<button id="crouch">下蹲</button>'+a+'<button id="extend">蹬伸终点</button><button id="single">左前抬腿</button>'
 if 'id="crouch"' not in t:
  assert a in t
  t=t.replace(a,b,1);old="get('ride').onclick="
  t=t.replace(old,"for(const [id,qs] of Object.entries({crouch:[-36,-36,-36,-36],extend:[22,22,22,22],single:[-36,-7,-7,-7]})){get(id).onclick=()=>{stop();angles=qs.slice();draw()}}"+old,1)
  file.write_text(t,encoding='utf8')
p=S/'r5_preview.cjs';t=p.read_text(encoding='utf-8-sig')
if "page.click('#single')" not in t:
 t=t.replace("await page.click('#diag');","await page.click('#single');assert.deepEqual(await page.locator('output').allTextContents(),['-36°','-7°','-7°','-7°']);await page.click('#crouch');await page.click('#extend');assert.deepEqual(await page.locator('output').allTextContents(),['22°','22°','22°','22°']);await page.click('#diag');")
 p.write_text(t,encoding='utf8')
p=S/'r5_delivery.py';t=p.read_text(encoding='utf-8-sig')
t=t.replace("for k,v in mo['reopened'].items():","for k,v in {**mo['reopened'],**read(ROOT/'data/R5_pose_reference.json')}.items():")
t=t.replace('默认配置为 Motion。HTML 可在本地浏览器独立打开。','默认配置为 Motion。单独的 '+ "'+pack['pose']+'" +' 提供可切换的五个参考姿态。HTML 可在本地浏览器独立打开。')
t=t.replace('44 个连接配合，另有 4 个姿态距离配合。在 Motion 与 Motion_MID 中压缩这 4 个距离配合，保留手动拖动自由度。','44 个有效连接配合。在 Motion 与 Motion_MID 中保留四条腿的独立拖动自由度。')
t=t.replace("'R5_pack','R5_native_audit'","'R5_pack','R5_pose_reference','R5_drag_validation','R5_native_audit'")
p.write_text(t,encoding='utf8')
