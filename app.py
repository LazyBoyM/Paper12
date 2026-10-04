"""Local academic demonstration of official MPRNet inference (no remote uploads)."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import base64,io,json,time,uuid,threading,hashlib,zipfile,traceback,os
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,unquote
from concurrent.futures import ThreadPoolExecutor
from importlib.util import spec_from_file_location,module_from_spec
import numpy as np
from PIL import Image,ImageOps,UnidentifiedImageError
import torch
import torch.nn.functional as F

Image.MAX_IMAGE_PIXELS=16_000_000
torch.set_num_threads(min(4,os.cpu_count() or 1))
DEVICE='cuda' if torch.cuda.is_available() else 'cpu'
TASKS={'denoising':'Khử nhiễu','deblurring':'Khử nhòe','deraining':'Loại bỏ vệt mưa'}
JOBS={};GUARD=threading.Lock();POOL=ThreadPoolExecutor(max_workers=1)
CACHE={}

def open_image(data):
    if not isinstance(data,str) or ',' not in data:raise ValueError('Tệp ảnh không hợp lệ.')
    try:
        raw=base64.b64decode(data.split(',',1)[1],validate=True)
        if len(raw)>12*1024*1024:raise ValueError('Ảnh phải nhỏ hơn 12 MB.')
        with Image.open(io.BytesIO(raw)) as im:
            if im.width*im.height>16_000_000:raise ValueError('Ảnh tối đa 16 triệu điểm ảnh.')
            if min(im.size)<32:raise ValueError('Chiều nhỏ nhất của ảnh cần ít nhất 32 pixel.')
            return ImageOps.exif_transpose(im).convert('RGB')
    except (UnidentifiedImageError,Image.DecompressionBombError) as exc:
        raise ValueError('Không đọc được ảnh. Hãy dùng PNG hoặc JPEG.') from exc

def model_for(task):
    if task in CACHE:return CACHE[task]
    checkpoint=ROOT/'weights'/f'{task}.pth'
    if not checkpoint.exists():raise ValueError('Chưa có trọng số cho tác vụ này. Chạy download_models.py trước.')
    CACHE.clear()
    if DEVICE=='cuda':torch.cuda.empty_cache()
    spec=spec_from_file_location('official_'+task,ROOT/'models'/f'{task}.py');module=module_from_spec(spec);spec.loader.exec_module(module)
    model=module.MPRNet()
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    state=state.get('state_dict',state)
    state={k.removeprefix('module.'):v for k,v in state.items()}
    model.load_state_dict(state,strict=True);model.to(DEVICE).eval();CACHE[task]=model
    return model

def image_tensor(im):
    a=np.asarray(im,dtype=np.float32)/255.
    return torch.from_numpy(a.copy()).permute(2,0,1).unsqueeze(0)

def quality(im,ref):
    x=image_tensor(im);y=image_tensor(ref)
    mse=float(torch.mean((x-y)**2));psnr=None if mse==0 else float(-10*np.log10(mse))
    # Wang SSIM: 11x11 Gaussian, sigma=1.5, valid window; RGB channel average, L=1.
    g=torch.arange(11,dtype=torch.float32)-5;g=torch.exp(-(g*g)/(2*1.5**2));g/=g.sum()
    kernel=(g[:,None]*g[None,:]).expand(3,1,11,11)
    mx=F.conv2d(x,kernel,groups=3);my=F.conv2d(y,kernel,groups=3)
    vx=torch.clamp(F.conv2d(x*x,kernel,groups=3)-mx*mx,min=0)
    vy=torch.clamp(F.conv2d(y*y,kernel,groups=3)-my*my,min=0)
    cov=F.conv2d(x*y,kernel,groups=3)-mx*my
    s=((2*mx*my+.01**2)*(2*cov+.03**2))/((mx*mx+my*my+.01**2)*(vx+vy+.03**2))
    return {'psnr':psnr,'perfect_match':mse==0,'ssim':float(s.mean())}

def set_job(key,**updates):
    with GUARD:JOBS[key].update(updates)

def run_job(key,payload):
    try:
        task=payload['task']
        if task not in TASKS:raise ValueError('Tác vụ không hợp lệ.')
        set_job(key,message='Đang đọc ảnh và chuẩn bị mô hình…')
        image=open_image(payload['image']);original=image.size
        requested=payload.get('size',256)
        if requested!='original':
            edge=int(requested)
            if edge not in [256,384,512]:raise ValueError('Kích thước xử lý không hợp lệ.')
            image.thumbnail((edge,edge),Image.Resampling.LANCZOS)
        if min(image.size)<32:raise ValueError('Tỉ lệ ảnh quá dài. Hãy cắt ảnh để chiều nhỏ nhất sau thu gọn ≥ 32 pixel.')
        reference=None
        if payload.get('reference'):
            reference=open_image(payload['reference'])
            if reference.size!=original:raise ValueError('Ảnh sạch tham chiếu phải cùng kích thước với ảnh đầu vào.')
            reference=reference.resize(image.size,Image.Resampling.LANCZOS)
        set_job(key,message='Đang tải trọng số MPRNet…')
        model=model_for(task)
        x=image_tensor(image).to(DEVICE);h,w=x.shape[-2:]
        x=F.pad(x,(0,(-w)%8,0,(-h)%8),mode='reflect')
        set_job(key,message=f'MPRNet đang phục hồi ảnh {w} × {h}…')
        if DEVICE=='cuda':torch.cuda.synchronize()
        started=time.perf_counter()
        with torch.inference_mode():predictions=model(x)
        if DEVICE=='cuda':torch.cuda.synchronize()
        elapsed=time.perf_counter()-started
        folder=ROOT/'results'/key;folder.mkdir(parents=True)
        image.save(folder/'input.png')
        stages=[]
        # Official forward returns [stage3, stage2, stage1].
        for number,tensor in enumerate(reversed(predictions),start=1):
            a=tensor[0,:,:h,:w].clamp(0,1).permute(1,2,0).cpu().numpy()
            im=Image.fromarray(np.rint(a*255).astype(np.uint8));im.save(folder/f'stage{number}.png')
            stages.append({'stage':number,'url':f'/results/{key}/stage{number}.png','metrics':quality(im,reference) if reference else None})
        if reference:reference.save(folder/'reference.png')
        weights=json.loads((ROOT/'weights'/'manifest.json').read_text(encoding='utf8'))[task]
        result={'task':task,'task_label':TASKS[task],'device':DEVICE,'seconds':round(elapsed,3),'resolution':[w,h],'original_resolution':list(original),'resized':image.size!=original,'input_url':f'/results/{key}/input.png','stages':stages,'baseline_metrics':quality(image,reference) if reference else None,'reference_url':f'/results/{key}/reference.png' if reference else None,'metrics_protocol':'RGB [0,1]; PSNR from MSE; SSIM Gaussian 11×11, σ=1.5, valid window; computed on saved 8-bit outputs at processing resolution. Not the paper deraining Y-channel protocol.','weights_sha256':weights['sha256'],'paper':'https://arxiv.org/abs/2102.02808','download_url':f'/results/{key}/bundle.zip'}
        if payload.get('demo_metadata'):result['demo_metadata']=payload['demo_metadata']
        (folder/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        with zipfile.ZipFile(folder/'bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
            for f in folder.iterdir():
                if f.name!='bundle.zip':z.write(f,f.name)
        set_job(key,state='done',message='Đã phục hồi ảnh.',result=result)
    except Exception as exc:
        traceback.print_exc();set_job(key,state='error',message=str(exc))

class Handler(BaseHTTPRequestHandler):
    def json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        route=unquote(urlparse(self.path).path)
        if route=='/api/status':return self.json({'device':DEVICE,'tasks':{k:(ROOT/'weights'/f'{k}.pth').exists() for k in TASKS},'model':'MPRNet / CVPR 2021'})
        if route.startswith('/api/job/'):
            with GUARD:job=dict(JOBS.get(route.rsplit('/',1)[-1],{}))
            return self.json(job if job else {'message':'Không tìm thấy phiên xử lý.'},200 if job else 404)
        file=ROOT/'static'/'index.html' if route=='/' else ROOT/route.lstrip('/')
        allowed=[ROOT/'static',ROOT/'samples',ROOT/'results']
        if not any(file.resolve().is_relative_to(p.resolve()) for p in allowed) or not file.is_file():return self.send_error(404)
        raw=file.read_bytes();self.send_response(200)
        typ={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.png':'image/png','.jpg':'image/jpeg','.json':'application/json','.zip':'application/zip'}.get(file.suffix,'application/octet-stream')
        self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff')
        if file.suffix=='.zip':self.send_header('Content-Disposition','attachment; filename="MPRNet-ket-qua.zip"')
        self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.path!='/api/restore':return self.send_error(404)
        origin=self.headers.get('Origin')
        if origin and urlparse(origin).hostname not in ['127.0.0.1','localhost']:return self.json({'message':'Chỉ chấp nhận thao tác từ giao diện cục bộ.'},403)
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=34*1024*1024:raise ValueError('Dung lượng yêu cầu quá lớn.')
            payload=json.loads(self.rfile.read(size))
            if payload.get('task') not in TASKS:raise ValueError('Hãy chọn tác vụ hợp lệ.')
            with GUARD:
                if any(j['state']=='running' for j in JOBS.values()):return self.json({'message':'Đang xử lý một ảnh. Vui lòng chờ.'},409)
                key=uuid.uuid4().hex;JOBS[key]={'state':'running','message':'Đang chuẩn bị…'}
                if len(JOBS)>40:
                    old=next(iter(JOBS));JOBS.pop(old,None)
            POOL.submit(run_job,key,payload);self.json({'id':key},202)
        except (ValueError,TypeError) as exc:self.json({'message':str(exc)},400)
    def log_message(self,fmt,*args):print(fmt%args,flush=True)

if __name__=='__main__':
    import argparse,webbrowser
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8770);parser.add_argument('--open-browser',action='store_true');args=parser.parse_args()
    url=f'http://127.0.0.1:{args.port}'
    print(f'MPRNet Demo ({DEVICE}): {url}',flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    if args.open_browser:threading.Timer(1,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();POOL.shutdown(wait=False)


