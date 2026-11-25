from common import *
from geometry import shape
import zlib,base64
p=ROOT/'data/legmesh.bin';ms=json.loads(zlib.decompress(p.read_bytes()))
for k in ['M01','Rotor4310']:
 s=shape(leg.PARTS[k]);pts,i=s.tessellate(.09,.17)
 ms[k]=[base64.b64encode(np.array(a,dtype=t).tobytes()).decode('ascii') for a,t in [([v.toTuple() for v in pts],'<f4'),(i,'<u4')]]
p.write_bytes(zlib.compress(json.dumps(ms,separators=(',',':')).encode(),7))

