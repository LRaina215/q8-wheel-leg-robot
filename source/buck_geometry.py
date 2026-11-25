"""Purchased YourCee envelope and a strap-retained A1 tray. Vehicle frame, mm."""
def add_pair(define,put,box,cyl,fuse):
    # Negative X input, positive X output. Port side/origin is estimated from the photo.
    board=box(58,51,1.6)
    for x in [-25,25]:
        for y in [-22,22]:
            board=board.cut(cyl(x,y,-1,1.65,4))
    for sign in [-1,1]:
        board=board.fuse(box(59,2.4,14,0,sign*18,1.6))
        board=board.fuse(box(60,9.8,2.2,0,sign*21.6,13.4))
        for x in [-28,-22,-16,-10,-4,2,8,14,20,26]:
            board=board.fuse(box(1.5,9.8,14.5,x,sign*21.6,15.5))
        block=box(11,17,12,sign*24,0,1.6)
        for y in [-4,4]:
            block=block.cut(cyl(sign*24,y,11,2.0,4))
        board=board.fuse(block)
    board=board.fuse(cyl(-1,0,1.6,9.6,17))
    for x,y in [(-14,10),(-14,-10),(14,-10),(14,10)]:
        board=board.fuse(cyl(x,y,1.6,4.2,12))
    define('YourCee20','优信 12 V 绿端子降压板','接口简模',board.clean(),'#3f9276','商品图外廓，端子和安装孔为定位估计；质量参考同类板',.090,.080,.100)
    # Nominal board centers (61,-45) and (61,19); tray local origin at x=61, y=-13.
    # Two low ledges support each PCB with four edge stops; two straps go over fin banks.
    from functools import reduce
    geom=[]
    for yy in [-32,32]:
        for x in [-28,28]:
            geom.append(box(6,58,3,x,yy))
            geom.append(box(2,22,4.6,(-31.2 if x<0 else 31.2),yy))
        for dy in [-24,24]:
            cross=box(69,7,3,0,yy+dy)
            for xx in [-32,32]:
                cross=cross.cut(box(2.9,4.2,6,xx,yy+dy,-1))
            geom.append(cross)
        for dy in [-28,28]:
            for xx in [-18,18]:geom.append(box(6,2,4.7,xx,yy+dy))
    geom.extend([box(5,67,3,0,0),box(102,8,3,-1,-17)])
    tray=reduce(lambda a,b:a.fuse(b),geom).clean()
    for yy in [-56,-8,8,56]:
        tray=tray.cut(box(67,3.2,1.3,0,yy,-.15))
    # Slots above existing floor slots at X11/109, Y-30; third anchor above front vent.
    for x in [-50,48]:tray=tray.cut(box(3.1,4.2,6,x,-17,-1))
    tray=tray.cut(box(3.1,4.2,6,21,56,-1))
    define('BuckTray','双降压板绝缘托架','PETG',tray.clean(),'#329088','A1 PETG HF；两组边挡与穿带槽，利用底盆原槽及前通风孔固定')
    put('BuckTray',61,-13,-45)
    put('YourCee20',61,-45,-42,name='Buck_rear')
    put('YourCee20',61,19,-42,name='Buck_front')
