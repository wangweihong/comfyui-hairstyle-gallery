#!/usr/bin/env python3
"""Resume-safe single-flight extraction using the user's FLUX Klein hairstyle graph."""
import argparse, copy, csv, fcntl, hashlib, json, os, shutil, time, urllib.request, urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIBRARY=Path('/media/wwhvw/备份/comfyui/发型')
SOURCE=ROOT.parent/'comfyui-portrait-gallery/library'
API='http://127.0.0.1:8188'
OUTPUT=Path('/media/wwhvw/备份/comfyui/output')
SEED=295046273850143

def atomic(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(path)
def request(path,data=None):
 req=urllib.request.Request(API+path, data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)
 except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode()) from e

def graph(identity):
 source=json.loads((LIBRARY/'workflows/source_flux-klein-提取发型.json').read_text());sub=source['definitions']['subgraphs'][0]
 prompt=next(n for n in source['nodes'] if n['id']==445)['widgets_values_named']['text']
 if (LIBRARY/'workflows/extraction_prompt.txt').exists():prompt=(LIBRARY/'workflows/extraction_prompt.txt').read_text()
 resize=next(n for n in sub['nodes'] if n['id']==172)['widgets_values_named']
 g={}
 def n(i,typ,title,**inputs):g[str(i)]={'class_type':typ,'inputs':inputs,'_meta':{'title':typ+' - '+title}}
 n(1,'PortraitGallery','读取正脸原图',portrait_id=identity)
 n(2,'UNETLoader','加载原工作流Klein 9B',unet_name='image2image/flux2/flux-2-klein-9b.safetensors',weight_dtype='default')
 n(3,'LoraLoaderModelOnly','保留原一致性LoRA',model=['2',0],lora_name='klein/Klein-consistency.safetensors',strength_model=0.8)
 n(4,'CLIPLoader','加载原文本编码器',clip_name='qwen_3_8b_fp8mixed.safetensors',type='flux2',device='default')
 n(5,'VAELoader','加载原Flux2 VAE',vae_name='flux2/flux2-vae.safetensors')
 n(6,'LayerUtility: ImageScaleByAspectRatio V2','沿用原工作流最短边1080',image=['1',0],**resize)
 n(7,'GetImageSize','读取参考宽高',image=['6',0])
 n(8,'VAEEncode','编码发型参考',pixels=['6',0],vae=['5',0])
 n(9,'CLIPTextEncode','原始提取发型提示词',clip=['4',0],text=prompt)
 n(10,'ConditioningZeroOut','空负向条件',conditioning=['9',0])
 n(11,'ReferenceLatent','正向发型参考',conditioning=['9',0],latent=['8',0])
 n(12,'ReferenceLatent','负向参考结构',conditioning=['10',0],latent=['8',0])
 n(13,'CFGGuider','沿用CFG1',model=['3',0],positive=['11',0],negative=['12',0],cfg=1.0)
 n(14,'RandomNoise','沿用固定种子',noise_seed=SEED)
 n(15,'KSamplerSelect','沿用Euler',sampler_name='euler')
 n(16,'Flux2Scheduler','沿用4步调度',steps=4,width=['7',0],height=['7',1])
 n(17,'EmptyFlux2LatentImage','按参考宽高创建潜空间',width=['7',0],height=['7',1],batch_size=1)
 n(18,'SamplerCustomAdvanced','提取发型并生成无脸假人',noise=['14',0],guider=['13',0],sampler=['15',0],sigmas=['16',0],latent_image=['17',0])
 n(19,'VAEDecode','解码假人发型',samples=['18',0],vae=['5',0])
 n(20,'SaveImage','保存独立发型原图',images=['19',0],filename_prefix='images/hairstyle-gallery/'+identity)
 return g

def rebuild(rows,state):
 complete=[]
 for source in rows:
  sid=source['id'];event=state['items'].get(sid,{})
  if event.get('status')!='complete':continue
  record=dict(source);identity='h-'+sid
  record.update(id=identity,source_id=sid,source_section='face',section='hairstyle',section_zh='假人发型',
   full=f'img/full/{identity}.png',thumb=f'img/thumb/{identity}.webp',
   preview=f'img/preview/{identity}.webp',name_zh=source['style_zh'] or source['hair_zh']+'发型',
   name_ja=source['style'] or source['hair'],name_source='source_style' if source['style'] else 'source_length_fallback',
   title=source['style_zh'] or source['hair_zh']+'发型',
   w=event['width'],h=event['height'],bytes=event['bytes'],thumb_w=event['thumb_w'],thumb_h=event['thumb_h'],
   seed=SEED,workflow='flux-klein-提取发型',prompt_sha256=hashlib.sha256((LIBRARY/'workflows/extraction_prompt.txt').read_bytes()).hexdigest(),sha256=event['sha256'])
  record['search']=' '.join(str(record[k]) for k in ['id','source_id','name_zh','name_ja','hair_zh','hair','style_zh','style']).lower()
  complete.append(record)
 atomic(LIBRARY/'data/hairstyle-zh.json',complete)
 atomic(LIBRARY/'data/meta-zh.json',{'total':len(complete),'target':len(rows),'lengths':{h:sum(r['hair_zh']==h for r in complete) for h in ['短发','中发','中长发','长发']},'workflow':'flux-klein-提取发型'})
 with (LIBRARY/'data/hairstyles.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['id','name_zh','name_ja','name_source','hair_zh','source_id','full','thumb','preview','w','h','seed','sha256'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(complete)
 atomic(LIBRARY/'data/generation-state.json',state)
 mirror=OUTPUT/'hairstyle-gallery-library';(mirror/'data').mkdir(parents=True,exist_ok=True)
 for name in ['hairstyle-zh.json','meta-zh.json','hairstyles.csv']:
  target=mirror/'data'/name
  temp=target.with_suffix(target.suffix+'.linktmp')
  if temp.exists():temp.unlink()
  os.link(LIBRARY/'data'/name,temp);temp.replace(target)

def collect(row,event):
 from PIL import Image,ImageOps
 images=event['outputs'].get('20',{}).get('images',[])
 if len(images)!=1:raise RuntimeError('Expected one saved result: '+str(event.get('outputs')))
 img=images[0];src=(OUTPUT/img['subfolder']/img['filename']).resolve()
 if not src.is_relative_to(OUTPUT) or img['type']!='output':raise RuntimeError('Invalid output path')
 identity='h-'+row['id'];dst=LIBRARY/f'img/full/{identity}.png'
 with Image.open(src) as im:im.verify()
 if not dst.exists():
  try:os.link(src,dst)
  except OSError:shutil.copy2(src,dst)
 with Image.open(dst) as im:
  image=ImageOps.exif_transpose(im).convert('RGB');width,height=image.size
  thumb=image.copy();thumb.thumbnail((400,500));thumb.save(LIBRARY/f'img/thumb/{identity}.webp',quality=88,method=6)
  preview=image.copy();preview.thumbnail((800,1000));preview.save(LIBRARY/f'img/preview/{identity}.webp',quality=90,method=6)
  tw,th=thumb.size
 for kind,suffix in [('full','.png'),('thumb','.webp'),('preview','.webp')]:
  target=OUTPUT/f'hairstyle-gallery-library/img/{kind}/{identity}{suffix}';target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():os.link(LIBRARY/f'img/{kind}/{identity}{suffix}',target)
 return {'status':'complete','width':width,'height':height,'thumb_w':tw,'thumb_h':th,'bytes':dst.stat().st_size,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'output':img,'completed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}

def main():
 p=argparse.ArgumentParser();p.add_argument('--samples',action='store_true');p.add_argument('--limit',type=int)
 p.add_argument('--library',type=Path,default=LIBRARY);p.add_argument('--source',type=Path,default=SOURCE)
 p.add_argument('--output',type=Path,default=OUTPUT);p.add_argument('--api',default=API);a=p.parse_args()
 globals().update(LIBRARY=a.library.resolve(),SOURCE=a.source.resolve(),OUTPUT=a.output.resolve(),API=a.api.rstrip('/'))
 LIBRARY.mkdir(parents=True,exist_ok=True)
 lock=(LIBRARY/'batch.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for f in ['data','img/full','img/thumb','img/preview','jobs','workflows']:(LIBRARY/f).mkdir(parents=True,exist_ok=True)
 rows=[r for r in json.loads((SOURCE/'data/portrait-zh.json').read_text()) if r['section']=='face']
 atomic(LIBRARY/'data/source-faces.json',rows)
 statefile=LIBRARY/'data/generation-state.json'
 state=json.loads(statefile.read_text()) if statefile.exists() else {'target':len(rows),'items':{}}
 state['status']='running'
 atomic(LIBRARY/'SOURCE.json',{'source_project':'comfyui-portrait-gallery','original_source':'https://ai-portrait-gallery.pages.dev/','source_records':len(rows),'section':'face','generated_with':'flux-klein-提取发型.json','seed':SEED,'name_policy':'Original Chinese/Japanese hairstyle description; length fallback when absent. No inferred extra labels.'})
 selected=rows
 if a.samples:selected=[next(r for r in rows if r['hair_zh']==h) for h in ['短发','中发','中长发','长发']]
 if a.limit:selected=selected[:a.limit]
 atomic(LIBRARY/'workflows/flux-klein-hairstyle.api.json',graph(selected[0]['id']))
 for row in selected:
  sid=row['id'];previous=state['items'].get(sid,{})
  if previous.get('status')=='complete' and (LIBRARY/f'img/full/h-{sid}.png').exists():continue
  for attempt in range(2):
   try:
    if previous.get('status')=='submitted':pid=previous['prompt_id']
    else:
     g=graph(sid);result=request('/prompt',{'prompt':g,'client_id':'hairstyle-gallery-batch'});pid=result['prompt_id']
     atomic(LIBRARY/f'jobs/{sid}.api.json',g)
     state['items'][sid]={'status':'submitted','prompt_id':pid,'attempt':attempt+1};rebuild(rows,state)
     print('SUBMITTED',sid,pid,flush=True)
    began=time.monotonic()
    while True:
     event=request('/history/'+pid).get(pid)
     if event and event.get('status',{}).get('completed'):break
     if event and event.get('status',{}).get('status_str')=='error':raise RuntimeError(str(event['status']))
     if time.monotonic()-began>1800:raise RuntimeError('No result within 30 minutes; submitted job retained for resume')
     time.sleep(1)
    if event['status']['status_str']!='success':raise RuntimeError(str(event['status']))
    atomic(LIBRARY/f'jobs/{sid}.history.json',event)
    result=collect(row,event);result['prompt_id']=pid;state['items'][sid]=result;rebuild(rows,state)
    print('COMPLETE',sid,sum(x.get('status')=='complete' for x in state['items'].values()),'/',len(rows),f'{time.monotonic()-began:.1f}s',flush=True);break
   except Exception as exc:
    state['items'][sid]={'status':'failed','error':str(exc),'attempt':attempt+1};rebuild(rows,state);print('ERROR',sid,str(exc),flush=True)
    if attempt:raise
    previous={};time.sleep(3)
 state['status']='complete' if sum(x.get('status')=='complete' for x in state['items'].values())==len(rows) else 'sample_complete';rebuild(rows,state)
 print('DONE',state['status'],flush=True)
if __name__=='__main__':main()
