"""Offline, allow-listed mannequin hairstyle library; reloads when the index changes."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LIBRARY=Path(os.environ.get('COMFYUI_HAIRSTYLE_GALLERY_LIBRARY', ROOT/'library')).resolve()
FIELDS={'full':('full','.png'),'thumb':('thumb','.webp'),'preview':('preview','.webp')}
NAME_EN=json.loads((ROOT/'translations/names.en.json').read_text(encoding='utf-8'))
HAIR_EN={'ショート':'Short','ミディアム':'Medium','セミロング':'Medium-long','ロング':'Long'}

def localized(row):
 name=NAME_EN.get(row['name_zh'], HAIR_EN.get(row.get('hair'), 'Unknown')+' hairstyle')
 style=name if row.get('style') else ''
 return dict(row,name_en=name,style_en=style,hair_en=HAIR_EN.get(row.get('hair'),'Unknown'),section_en='Mannequin hairstyle',search=' '.join([row.get('search',''),name,HAIR_EN.get(row.get('hair'),'')]).lower())

ID_PATTERN=re.compile(r'[a-z0-9_-]{1,80}')

@lru_cache(maxsize=2)
def _read_library(path,modified,size):
 rows=json.loads(Path(path).read_text(encoding='utf-8'))
 if not isinstance(rows,list):raise ValueError('发型索引格式错误')
 seen=set()
 for row in rows:
  identity=row.get('id') if isinstance(row,dict) else None
  if not isinstance(identity,str) or not ID_PATTERN.fullmatch(identity) or identity in seen:raise ValueError('发型索引包含无效或重复ID')
  seen.add(identity)
  if row.get('section')!='hairstyle':raise ValueError('未知发型参考类型')
  if not isinstance(row.get('name_zh'),str) or not row['name_zh']:raise ValueError('发型名称缺失')
  for kind,(field,suffix) in FIELDS.items():
   if row.get(field)!=f'img/{kind}/{identity}{suffix}':raise ValueError('发型索引包含无效图片路径')
 return [localized(row) for row in rows]

def records():
 p=LIBRARY/'data/hairstyle-zh.json'
 if not p.is_file():raise FileNotFoundError('发型索引缺失：library/data/hairstyle-zh.json，请配置完整发型素材库。')
 stat=p.stat();return _read_library(str(p),stat.st_mtime_ns,stat.st_size)

def hairstyle(identity):
 if not isinstance(identity,str) or not ID_PATTERN.fullmatch(identity):raise ValueError('无效发型ID')
 row=next((r for r in records() if r['id']==identity),None)
 if row is None:raise ValueError('未知发型ID：'+identity)
 return row

def asset(kind,filename):
 if kind not in FIELDS or Path(filename).name!=filename or '\\' in filename:raise ValueError('无效发型图片路径')
 row=hairstyle(Path(filename).stem);field,suffix=FIELDS[kind]
 relative=Path('img')/kind/filename;target=(LIBRARY/relative).resolve()
 if Path(filename).suffix!=suffix or row[field]!=relative.as_posix() or not target.is_relative_to(LIBRARY):raise ValueError('图片不在发型图库允许范围内')
 if not target.is_file():raise FileNotFoundError('发型原图缺失：library/'+str(relative)+'，请检查完整素材库。')
 return target

def browser_payload():
 rows=[dict(r,**{field:f'assets/{kind}/{r["id"]}{suffix}' for kind,(field,suffix) in FIELDS.items()}) for r in records()]
 labels={'ショート':'短发','ミディアム':'中发','セミロング':'中长发','ロング':'长发'}
 ranking={'cats':list(labels),'labels':labels,'top':{h:[r['id'] for r in rows if r['hair']==h][:10] for h in labels}}
 return {'records':rows,'meta':{'total':len(rows),'target':893,'sections':{'hairstyle':len(rows)}},'ranking':ranking}
