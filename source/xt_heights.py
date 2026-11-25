from common import ROOT,write
import loads
def for_kits(keys):
    return {key:loads.report(opt,target_h=.020,emit=False) for key,opt in zip(keys,[False,True])}
table=for_kits(['base','mid'])
# as_sliced applies measured slicer-path masses to print objects for both kits.
import as_sliced
table.update(for_kits(['slice','slice_mid']))
write(ROOT/'data'/'四配置20mm动作.json',table)

