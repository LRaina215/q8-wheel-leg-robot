import loads
from common import ROOT,write
base=loads.budget
def reduced(opt):
    m,c,C,rows=base(opt)
    # Hypothetical sprung mass removed at the hip-frame origin on both centre lines.
    return 6.0,c*m/6.0,C,rows
loads.csvwrite=lambda *args:None
loads.budget=reduced
r=loads.report(False)
n=r['heaviest']
write(ROOT/'data'/'reference_6kg.json',dict(assumption='hypothetical removal of sprung mass at the four-hip centre, retaining all wheel assemblies and first moments in X,Y',nominal_mass=6,heaviest=n,static=r['static']['-7'],at22V2=r['cases']['22V2'][n],tyre_clearance=r['brake']['clearance'],worst=r['cases']['loss_diagonal'][n]))
