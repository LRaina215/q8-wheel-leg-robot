from r5_bundle import *
todo=[refpath,topfile];seen=set()
while todo:
 x=todo.pop()
 if x in seen:continue
 seen.add(x)
 if not x.is_relative_to(OUT):print('external',x.is_file(),x,flush=True)
 if x.is_file() and x.suffix.upper() in ['.SLDASM','.SLDPRT']:todo.extend(references(x))
print('count',len(seen))
