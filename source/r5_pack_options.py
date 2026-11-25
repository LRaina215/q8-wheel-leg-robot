from pathlib import Path
p=Path('r5_portable.py');p.write_text(p.read_text(encoding='utf8').replace('pg.IncludeDrawings=False;','pg.IncludeDrawings=False;pg.IncludeSuppressed=True;'),encoding='utf8')

