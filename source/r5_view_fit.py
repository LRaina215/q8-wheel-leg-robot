from pathlib import Path
p=Path('r5_view.html');s=p.read_text(encoding='utf-8-sig');s=s.replace('Math.max(260,320*H/W)','Math.max(303,432*H/W)').replace('cam.lookAt(0,0,-7)','cam.lookAt(0,0,-25)').replace('if(selected){if(selected.material','if(selected){const d=selected.userData;if(d.opt)get("mid").checked=true;if(d.line)get("wire").checked=true;if(d.bolt)get("screws").checked=true;if(d.deck)get("cover").checked=false;if(selected.material');p.write_text(s,encoding='utf8')

