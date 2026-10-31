#!/usr/bin/env python3
"""Validate identity coverage, names, derivative images, dimensions and SHA-256."""
from pathlib import Path
import argparse,hashlib,json,collections
from PIL import Image

def main():
 p=argparse.ArgumentParser();p.add_argument('--library',type=Path,default=Path('/media/wwhvw/备份/comfyui/发型'));p.add_argument('--partial',action='store_true');a=p.parse_args();root=a.library
 rows=json.loads((root/'data/hairstyle-zh.json').read_text());sources=json.loads((root/'data/source-faces.json').read_text());state=json.loads((root/'data/generation-state.json').read_text());sourceids={r['id'] for r in sources}
 assert len(sourceids)==len(sources)==893
 assert len({r['id'] for r in rows})==len(rows)
 if not a.partial:assert len(rows)==893 and {r['source_id'] for r in rows}==sourceids
 errors=[];assets=[]
 for row in rows:
  try:
   assert row['id']=='h-'+row['source_id'] and row['source_id'] in sourceids
   assert row['name_zh'] and row['name_ja'] and row['name_source'] in ['source_style','source_length_fallback']
   assert state['items'][row['source_id']]['status']=='complete'
   for field,ext,limit in [('full','.png',None),('preview','.webp',(800,1000)),('thumb','.webp',(400,500))]:
    path=root/row[field];assert path.suffix==ext
    with Image.open(path) as im:
     im.verify()
    with Image.open(path) as im:
     w,h=im.size
     if field=='full':assert [w,h]==[row['w'],row['h']]
     if limit:assert w<=limit[0] and h<=limit[1] and abs(w/h-row['w']/row['h'])<.005
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if field=='full':assert digest==row['sha256']
    assets.append({'id':row['id'],'kind':field,'path':row[field],'bytes':path.stat().st_size,'sha256':digest})
  except Exception as exc:errors.append({'id':row.get('id'),'error':repr(exc)})
 report={'ok':not errors,'complete':len(rows)==893,'records':len(rows),'assets':len(assets),'lengths':dict(collections.Counter(r['hair_zh'] for r in rows)),'bytes':sum(x['bytes'] for x in assets),'errors':errors}
 (root/'data/audit-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (root/'data/asset-manifest.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
