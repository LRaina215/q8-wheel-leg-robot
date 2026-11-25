from r5_vehicle import *
from PIL import Image
dest=ROOT/'交付'/'SolidWorks'
cfg=read(ROOT/'data/R5_pack.json')
m=open_doc(dest/cfg['main'],2);activate(m);m.ShowConfiguration2('Motion');m.ShowNamedView2('*Isometric',7);m.ViewZoomtofit2();m.GraphicsRedraw2()
bmp=ROOT/'data/R5_SolidWorks.bmp'
assert m.SaveBMP(str(bmp),1400,900) and bmp.exists()
with Image.open(bmp) as im:im.save(ROOT/'data/R5_SolidWorks.png')
