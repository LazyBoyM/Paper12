"""Fetch only the official pretrained checkpoints linked by the MPRNet authors."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
(ROOT/'weights').mkdir(parents=True, exist_ok=True)
import gdown

IDS={'deblurring':'1QwQUVbk6YVOJViCsOKYNykCsdJSVGRtb','deraining':'1O3WEJbcat7eTY6doXWeorAbQ1l_WmMnM','denoising':'1LODPt9kYmxwU98g96UrRA0_Eh5HYcsRw'}
manifest={}
for task,id in IDS.items():
    p=ROOT/'weights'/f'{task}.pth'
    if not p.exists():
        print('Downloading',task,flush=True)
        result=gdown.download(id=id,output=str(p),quiet=False)
        if not result:raise RuntimeError(f'Download failed: {task}')
    manifest[task]={'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':f'https://drive.google.com/file/d/{id}/view','repository':'https://github.com/swz30/MPRNet'}
(ROOT/'weights'/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('Official checkpoints ready.',flush=True)

