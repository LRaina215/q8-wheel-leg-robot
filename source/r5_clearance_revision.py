from pathlib import Path
def edit(f,changes):
 p=Path(__file__).with_name(f);s=p.read_text(encoding='utf-8-sig')
 for a,b in changes:
  if a not in s:raise ValueError((f,a))
  s=s.replace(a,b)
 p.write_text(s,encoding='utf8')
edit('r5_parts.py',[
 ("traypts=[(x+dx,y) for x,y in drivers for dx in [-35,35]]","traypts=[(x+dx,y+34) for x,y in drivers for dx in [-18,18]]"),
 ("(0,0,64,63),(0,0,80,10)","(0,0,64,63),(-18,31.5,10,14),(18,31.5,10,14)"),
 ("[(-35,0),(35,0)]","[(-18,34),(18,34)]"),
 ("(109,-30)","(107.5,-30)"),("(48,-17)","(46.5,-17)"),
 ("op('M4_hex_capture_AF7p3'","holes('MID_head_and_tool_passages',midpts,8.2,21,12),op('M4_hex_capture_AF7p3'"),
 ("op('Retention_strap_slots'","holes('Top_screw_head_reliefs',[(-25,-9),(25,-9)],6.4,4,3.7),op('Retention_strap_slots'")])
edit('r5_instances.py',[("[(x+dx,y) for x,y in drivers for dx in [-35,35]]","[(x+dx,y+34) for x,y in drivers for dx in [-18,18]]"),("(109,-30)","(107.5,-30)")])
edit('r5_rack.py',[("Q8_R5_Equipment.SLDASM","Q8_R5_设备机架.SLDASM"),("(-35,0,1.7)","(-18,34,1.7)"),
 ("abs(y-T[n]['pos'][1]));p=(x-T[parent]['pos'][0],0,1.7)","abs(y-34-T[n]['pos'][1]));p=(x-T[parent]['pos'][0],34,1.7)")])
edit('r5_static.py',[("(48,-17)","(46.5,-17)"),("[(-35,0),(35,0)]","[(-18,34),(18,34)]")])

