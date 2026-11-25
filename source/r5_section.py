from common import *
from r5_parts import deckpts,midpts,jc,mc,xt,astra,traypts
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon
from matplotlib.font_manager import FontProperties
font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc');plt.rcParams['axes.unicode_minus']=False
fig,(a,b)=plt.subplots(1,2,figsize=(11.9,5.9),gridspec_kw={'width_ratios':[1.18,1]});fig.patch.set_facecolor('white')
a.add_patch(Polygon([(-118,-85),(118,-85),(118,85),(96,85),(96,148),(-96,148),(-96,85),(-118,85)],facecolor='#e7edeb',edgecolor='#4a6b60'))
for title,pts,col in [('上板至底盆 M4',deckpts,'#953e22'),('Jetson 压爪',jc,'#1d6652'),('XT 雷达隔柱',xt,'#38587c'),('MC02',mc,'#8a6b21'),('轮驱托盘',traypts,'#855685'),('Astra 托块',astra,'#346d83'),('MID 支柱',midpts,'#717a70')]:
 x,y=zip(*pts);a.scatter(x,y,s=44 if pts==deckpts else 28,color=col,label=title,edgecolor='white',linewidth=.65)
a.set_aspect('equal');a.set_xlim(-128,128);a.set_ylim(-94,158);a.set_xlabel('X / mm');a.set_ylabel('Y / mm');a.set_title('上板俯视 · 前方为 +Y',fontproperties=font,fontsize=14);a.legend(loc='upper center',bbox_to_anchor=(.5,-.15),ncol=3,prop=FontProperties(fname='C:/Windows/Fonts/msyh.ttc',size=8),frameon=False)
for x in [-9,2.25]:b.add_patch(Rectangle((x,32),6.75,4,color='#809b99'))
for x in [-9,2.25]:b.add_patch(Rectangle((x,25.4),6.75,6.6,color='#4a7768'))
for x in [-9,3.65]:b.add_patch(Rectangle((x,22),5.35,3.4,color='#4a7768'))
b.add_patch(Rectangle((-2,20),4,16,color='#9ea8ac'));b.add_patch(Rectangle((-3.5,36),7,4,color='#455761'))
for x in [-3.5,2]:b.add_patch(Rectangle((x,22.2),1.5,3.2,color='#c79b5e'))
for yy,y0,s in [(38,40,'M4×16 圆柱头螺钉'),(34,35.3,'上板厚 4 mm，通孔 Ø4.5'),(28.5,30.1,'底盆凸耳与上板贴合'),(24,25.2,'M4 螺母从下方装入'),(20,19.6,'螺杆端部露出约 2.2 mm')]:
 b.annotate(s,xy=(2.4,yy),xytext=(12,y0),fontproperties=font,fontsize=10,va='center',arrowprops=dict(arrowstyle='-',color='#596c63',lw=.8))
b.set_xlim(-10.2,46);b.set_ylim(17,43);b.axis('off');b.set_title('六处共用的 M4 固定截面',fontproperties=font,fontsize=14)
fig.subplots_adjust(left=.08,right=.99,top=.91,bottom=.22,wspace=.12);fig.savefig(ROOT/'R5_上板固定.png',dpi=155)

