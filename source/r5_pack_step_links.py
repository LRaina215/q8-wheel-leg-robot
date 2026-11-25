from pathlib import Path
s=Path(__file__).with_name('r5_bundle.py');t=s.read_text(encoding='utf-8-sig').replace("assert p.is_relative_to(OUT) and p.is_file(),p","assert p.is_file() and (p.is_relative_to(OUT) or p.suffix.lower() in ['.step','.stp']),p").replace("children=references(p);graph[p]=children;todo.extend(children)","children=references(p) if p.suffix.upper() in ['.SLDPRT','.SLDASM'] else [];graph[p]=children;todo.extend(children)")
s.write_text(t,encoding='utf8')
