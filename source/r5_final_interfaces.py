from pathlib import Path
p=Path(__file__).with_name('r5_parts.py')
s=p.read_text(encoding='utf-8-sig').replace('(-81,-37,31),(60,-30,98),','(-81,-37,31),')
s=s.replace("holes('Deck_M4_clearance',deckpts", "holes('Power_tray_M3',[(11,-30),(109,-30),(54,52)],3.4,-50,7),holes('Deck_M4_clearance',deckpts")
s=s.replace("parts['Deck'].append(op('Jetson_longitudinal_stops'", "parts['Deck'].append(op('Logic_and_FFC_strap_slots',31,6,R((5.8,-20,3.2,6),(42.2,-20,3.2,6),(68,-8.6,6,3.2),(68,22.6,6,3.2)),True))\nparts['Deck'].append(op('Jetson_longitudinal_stops'")
s=s.replace('(0,0,5,67),(-1,-17,102,8)', '(0,0,5,67),(-1,-17,102,8),(-7,61,10,17)')
s=s.replace(",(-50,-17,3.1,4.2),(48,-17,3.1,4.2),(21,56,3.1,4.2)",'')
s=s.replace("op('Under_strap_recess'", "holes('Floor_M3', [(-50,-17),(48,-17),(-7,65)],3.4,-1,6),op('Under_strap_recess'")
p.write_text(s,encoding='utf8')

