"""Install this local node into the active Docker ComfyUI, with no queued job interrupted."""
from pathlib import Path
import os,signal,time,json,subprocess,importlib.util,shutil
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('batch',ROOT/'scripts/batch_extract.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
pid=int((b.LIBRARY/'batch.pid').read_text())
try:os.kill(pid,signal.SIGTERM)
except ProcessLookupError:pass
for _ in range(120):
 q=b.request('/queue')
 if not q['queue_running'] and not q['queue_pending']:break
 time.sleep(1)
else:raise RuntimeError('Queue not empty; did not restart ComfyUI')
state=json.loads((b.LIBRARY/'data/generation-state.json').read_text());rows=json.loads((b.LIBRARY/'data/source-faces.json').read_text());byid={r['id']:r for r in rows}
for sid,event in state['items'].copy().items():
 if event.get('status')=='submitted':
  history=b.request('/history/'+event['prompt_id']).get(event['prompt_id'])
  if not history or history['status']['status_str']!='success':raise RuntimeError('Pending result not recoverable: '+sid)
  b.atomic(b.LIBRARY/f'jobs/{sid}.history.json',history);result=b.collect(byid[sid],history);result['prompt_id']=event['prompt_id'];state['items'][sid]=result
b.rebuild(rows,state)
installed=Path('/home/wwhvw/.local/share/comfyui-custom/tests/cu130-megapak-pt211/storage-nodes/custom_nodes/comfyui-hairstyle-gallery')
if installed.exists() and any(installed.iterdir()):raise RuntimeError('Installation path is not empty; inspect before replacing')
shutil.copytree(ROOT,installed,dirs_exist_ok=True,ignore=shutil.ignore_patterns('library','__pycache__','.git','tests'))
(installed/'library').symlink_to('/root/ComfyUI/output/hairstyle-gallery-library',target_is_directory=True)
print('Installed',installed,flush=True)
subprocess.run(['docker','restart','comfyui-test-cu130-megapak-pt211'],check=True)
for _ in range(300):
 try:
  info=b.request('/object_info/HairstyleGallery')
  if 'HairstyleGallery' in info:break
 except Exception:pass
 time.sleep(1)
else:raise RuntimeError('Server did not expose HairstyleGallery')
print('NODE AVAILABLE',flush=True)
with (b.LIBRARY/'batch.log').open('a') as f:
 proc=subprocess.Popen(['python3','-u',str(ROOT/'scripts/batch_extract.py')],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(b.LIBRARY/'batch.pid').write_text(str(proc.pid));print('Resumed batch PID',proc.pid,flush=True)
