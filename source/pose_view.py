from vehicle_sw import *
from PIL import Image
def camera(m):
    eye=np.array([.76,.90,.69]);eye/=np.linalg.norm(eye)
    right=np.cross([0,0,1],eye);right/=np.linalg.norm(right)
    up=np.cross(eye,right)
    view=asif(m.ActiveView,api.IModelView)
    view.Orientation3=xf([0,0,0],np.array([right,up,eye]))
    m.ViewZoomtofit2();m.GraphicsRedraw2()
def main():
    p=OUT/'Q8_Full_Vehicle.SLDASM';m=open_doc(p,2);activate(m)
    for name in ['Crouch','Liftoff','Ride_MID360','Ride']:
        m.ShowConfiguration2(name);camera(m)
        imfile=ROOT/'data'/('SW_'+name+'.bmp');m.SaveBMP(str(imfile),1100,780)
        im=Image.open(imfile).convert('RGB');im.thumbnail((820,600));im.save(imfile.with_suffix('.png'),optimize=True)
    m.NameView('Q8_Z_UP');save(m,p);sw.CloseDoc(m.GetTitle())
if __name__=='__main__':main()
