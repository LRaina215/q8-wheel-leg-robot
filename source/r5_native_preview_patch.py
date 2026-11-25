from pathlib import Path
p=Path('r5_portable.py');s=p.read_text(encoding='utf8').replace('save(m,f);activate(m)','''save(m,f);activate(m);m.GraphicsRedraw2()
 preview=ROOT/'data/R5_SolidWorks.bmp'
 if m.SaveBMP(str(preview),1400,900) and preview.is_file():
  from PIL import Image
  with Image.open(preview) as im:im.save(ROOT/'data/R5_SolidWorks.png')''');p.write_text(s,encoding='utf8')
p=Path('r5_delivery.py');s=p.read_text(encoding='utf8').replace(" dst=ROOT/'Q8_R5_配合与运动审阅.zip'", " if (ROOT/'data/R5_SolidWorks.png').exists():shutil.copy2(ROOT/'data/R5_SolidWorks.png',assets/'R5_SolidWorks.png')\n dst=ROOT/'Q8_R5_配合与运动审阅.zip'");p.write_text(s,encoding='utf8')

