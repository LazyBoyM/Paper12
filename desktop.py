"""MPRNet desktop application. Run: python desktop.py. No web server required."""
from pathlib import Path
import sys, io, base64, uuid, threading, shutil, json, os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import app as engine
from PIL import Image, ImageOps, ImageTk

ROOT = Path(__file__).resolve().parent
LABELS = {v: k for k, v in engine.TASKS.items()}
BG, INK, TEAL, MUTED = '#f3f6f7', '#173743', '#18596a', '#5e717b'

def encoded(im):
    buf = io.BytesIO(); im.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')

def read_file(path):
    if Path(path).stat().st_size > 12 * 1024 * 1024:
        raise ValueError('Ảnh tối đa 12 MB.')
    with Image.open(path) as im:
        if im.width * im.height > 16_000_000 or min(im.size) < 32:
            raise ValueError('Ảnh cần từ 32 pixel mỗi chiều và tối đa 16 triệu pixel.')
        return ImageOps.exif_transpose(im).convert('RGB')

class MPRNetApp:
    def __init__(self, root):
        self.root = root; root.title('MPRNet — Ứng dụng phục hồi ảnh Python')
        root.geometry('1180x800'); root.minsize(1000, 780); root.configure(bg=BG)
        self.source = None; self.source_path = None; self.reference = None
        self.result = None; self.key = None; self.running = False; self.closed = False
        self.photos = []; self.before = None; self.after_image = None
        self.task = tk.StringVar(value='Khử nhiễu'); self.size = tk.StringVar(value='512')
        self.stage = tk.IntVar(value=3)
        self.view = tk.StringVar(value='Cạnh nhau'); self.ratio = tk.DoubleVar(value=50)
        self.status = tk.StringVar(value='Mở ảnh của bạn để bắt đầu.')
        self.source_label = tk.StringVar(value='Chưa chọn ảnh'); self.ref_label = tk.StringVar(value='Chưa có ảnh sạch tham chiếu')
        self.metrics = tk.StringVar(value='PSNR —    SSIM —\nCần ảnh tham chiếu để tính chỉ số.')
        self.runtime = tk.StringVar(value=''); self.note = tk.StringVar(value='Chọn đúng tác vụ theo dạng suy giảm của ảnh.')
        self.controls = []; self.stage_buttons = []
        self.build()
        self.run_button.configure(state='disabled')
        root.protocol('WM_DELETE_WINDOW', self.close)

    def button(self, parent, text, command, **kw):
        b = ttk.Button(parent, text=text, command=command, **kw); self.controls.append(b); return b

    def build(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 10), padding=(7, 4))
        style.configure('Accent.TButton', background=TEAL, foreground='white', font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('Accent.TButton', background=[('active', '#26788a'), ('disabled', '#82959a')])
        style.configure('TCheckbutton', background='white', font=('Segoe UI', 10))
        style.configure('TRadiobutton', background='white', font=('Segoe UI', 10))
        header = tk.Frame(self.root, bg=INK, padx=24, pady=12); header.pack(fill='x')
        tk.Label(header, text='MPRNet', bg=INK, fg='white', font=('Segoe UI', 23, 'bold')).pack(side='left')
        tk.Label(header, text='PHỤC HỒI ẢNH ĐA GIAI ĐOẠN\nNhóm 13 · 74DCTT25', bg=INK, fg='#cde3e9', font=('Segoe UI', 10), justify='left').pack(side='left', padx=22)
        tk.Label(header, text=f'Python · PyTorch · {engine.DEVICE.upper()}\nTrọng số chính thức · Xử lý cục bộ', bg=INK, fg='#dbece4', font=('Segoe UI', 10), justify='right').pack(side='right')
        body = tk.Frame(self.root, bg=BG, padx=18, pady=12); body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1); body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg='white', padx=17, pady=14, width=300); left.grid(row=0, column=0, sticky='nsew', padx=(0, 16)); left.grid_propagate(False)
        tk.Label(left, text='Thiết lập phục hồi', bg='white', fg=INK, font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(0, 10))
        tk.Label(left, text='TÁC VỤ', bg='white', fg=MUTED, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        task = ttk.Combobox(left, textvariable=self.task, values=list(LABELS), state='readonly', font=('Segoe UI', 11)); task.pack(fill='x', pady=(5, 14)); task.bind('<<ComboboxSelected>>', lambda e: self.invalidate()); self.controls.append(task)
        self.button(left, 'Mở ảnh đầu vào…', self.open_source).pack(fill='x')
        tk.Label(left, textvariable=self.source_label, bg='white', fg=MUTED, font=('Segoe UI', 9), wraplength=255, justify='left').pack(anchor='w', pady=(7, 11))
        row = tk.Frame(left, bg='white'); row.pack(fill='x', pady=(0, 12))
        tk.Label(row, text='Cạnh dài tối đa', bg='white', fg=INK, font=('Segoe UI', 10)).pack(side='left')
        size = ttk.Combobox(row, textvariable=self.size, values=['Gốc', '512', '384', '256'], state='readonly', width=6); size.pack(side='right'); size.bind('<<ComboboxSelected>>', lambda e:self.invalidate()); self.controls.append(size)
        tk.Label(left, text='Gốc: giữ nguyên độ phân giải.\n512 / 384 / 256: thu gọn để chạy nhanh.\nẢnh lớn chạy chậm hơn trên CPU.', bg='white', fg=MUTED, font=('Segoe UI', 9), justify='left').pack(anchor='w', pady=(0, 14))
        self.button(left, 'Chọn ảnh sạch tham chiếu…', self.open_reference).pack(fill='x')
        self.button(left, 'Bỏ ảnh tham chiếu', self.clear_reference).pack(fill='x', pady=(2, 0))
        tk.Label(left, textvariable=self.ref_label, bg='white', fg=MUTED, font=('Segoe UI', 9), wraplength=255, justify='left').pack(anchor='w', pady=(6, 14))
        self.run_button = self.button(left, 'PHỤC HỒI ẢNH', self.start, style='Accent.TButton'); self.run_button.pack(fill='x')
        self.progress = ttk.Progressbar(left, mode='indeterminate'); self.progress.pack(fill='x', pady=(10, 6))
        right = tk.Frame(body, bg='white', padx=16, pady=14); right.grid(row=0, column=1, sticky='nsew'); right.columnconfigure(0, weight=1); right.rowconfigure(1, weight=1)
        top = tk.Frame(right, bg='white'); top.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        tk.Label(top, text='So sánh đầu vào và kết quả', bg='white', fg=INK, font=('Segoe UI', 15, 'bold')).pack(side='left')
        for view in ['Cạnh nhau', 'Kéo so sánh']:
            ttk.Radiobutton(top, text=view, value=view, variable=self.view, command=self.draw).pack(side='right', padx=4)
        self.canvas = tk.Canvas(right, bg='#e9eff0', highlightthickness=0, height=390); self.canvas.grid(row=1, column=0, sticky='nsew'); self.canvas.bind('<Configure>', lambda e:self.draw())
        self.slider = ttk.Scale(right, from_=0, to=100, variable=self.ratio, command=lambda v:self.draw()); self.slider.grid(row=2, column=0, sticky='ew', pady=(8, 3))
        tk.Label(right, textvariable=self.status, bg='white', fg=TEAL, font=('Segoe UI', 10), wraplength=680, justify='left').grid(row=3, column=0, sticky='w', pady=5)
        stages = tk.Frame(right, bg='white'); stages.grid(row=4, column=0, sticky='ew', pady=6)
        tk.Label(stages, text='Giai đoạn', bg='white', fg=INK, font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 12))
        for n in [1, 2, 3]:
            b = ttk.Radiobutton(stages, text=f'{n:02}' + (' · Cuối' if n==3 else ''), value=n, variable=self.stage, command=self.select_stage); b.pack(side='left', padx=9); b.configure(state='disabled'); self.stage_buttons.append(b)
        tk.Label(right, textvariable=self.metrics, bg='#edf5f4', fg=INK, font=('Segoe UI', 12), padx=14, pady=10, justify='left', anchor='w').grid(row=5, column=0, sticky='ew', pady=(5, 7))
        tk.Label(right, textvariable=self.note, bg='white', fg=MUTED, font=('Segoe UI', 9), wraplength=690, justify='left').grid(row=6, column=0, sticky='w', pady=(0, 6))
        downloads = tk.Frame(right, bg='white'); downloads.grid(row=7, column=0, sticky='ew')
        self.save_image = ttk.Button(downloads, text='Lưu ảnh PNG…', command=self.export_image, state='disabled'); self.save_image.pack(side='left')
        self.save_bundle = ttk.Button(downloads, text='Lưu kết quả ZIP…', command=self.export_bundle, state='disabled'); self.save_bundle.pack(side='left', padx=8)
        tk.Label(self.root, text='MPRNet · CVPR 2021     |     Encoder–Decoder → Encoder–Decoder → ORSNet     |     SAM + CSFF', bg=BG, fg=MUTED, font=('Segoe UI', 9), pady=8).pack(fill='x')

    def load(self, path):
        if self.running: return
        try:
            self.source = read_file(path); self.source_path = Path(path); self.reference = None
            self.source_label.set(f'{Path(path).name} · {self.source.width} × {self.source.height} px')
            self.invalidate()
        except Exception as exc: messagebox.showerror('Không đọc được ảnh', str(exc), parent=self.root)

    def open_source(self):
        p = filedialog.askopenfilename(parent=self.root, title='Chọn ảnh đầu vào', filetypes=[('Ảnh', '*.png *.jpg *.jpeg *.webp *.bmp'), ('Tất cả', '*.*')])
        if p:self.load(p)

    def clear_reference(self):
        self.reference = None; self.invalidate()

    def open_reference(self):
        if self.source is None:
            messagebox.showinfo('Chưa có ảnh đầu vào', 'Hãy chọn ảnh đầu vào trước.', parent=self.root); return
        p = filedialog.askopenfilename(parent=self.root, title='Chọn ảnh sạch cùng cảnh và kích thước', filetypes=[('Ảnh', '*.png *.jpg *.jpeg *.webp *.bmp')])
        if p:
            try:
                ref = read_file(p)
                if self.source is None or ref.size != self.source.size: raise ValueError('Ảnh tham chiếu phải cùng kích thước và cùng cảnh với ảnh đầu vào.')
                self.reference = ref; self.invalidate(); self.ref_label.set(f'Tham chiếu: {Path(p).name}')
            except Exception as exc:messagebox.showerror('Ảnh tham chiếu không hợp lệ', str(exc), parent=self.root)

    def inputs(self):
        if self.source is None:raise ValueError('Hãy chọn ảnh đầu vào.')
        before=self.source.copy(); ref=self.reference.copy() if self.reference is not None else None
        metadata={'mode':'original','description':'Xử lý trực tiếp ảnh đã chọn; không tự tạo thêm suy giảm.','source_file':self.source_path.name,'source_resolution':list(self.source.size),'processing_size':self.size.get()}
        return before, ref, metadata

    def invalidate(self):
        self.result = None; self.after_image = None; self.key = None
        self.save_image.configure(state='disabled'); self.save_bundle.configure(state='disabled')
        for b in self.stage_buttons:b.configure(state='disabled')
        self.metrics.set('PSNR —    SSIM —\nChưa có kết quả.'); self.runtime.set('')
        self.ref_label.set('Đã chọn ảnh tham chiếu' if self.reference else 'Chưa có ảnh sạch tham chiếu')
        try:
            self.before, _, metadata = self.inputs(); self.note.set(metadata['description'])
            self.status.set('Ảnh sẵn sàng. Nhấn PHỤC HỒI ẢNH.'); self.run_button.configure(state='normal')
        except ValueError as exc:self.status.set(str(exc)); self.before=None; self.run_button.configure(state='disabled')
        self.draw()

    def set_running(self, value):
        self.running = value
        for widget in self.controls:
            if value:widget.configure(state='disabled')
            else:widget.configure(state='readonly' if isinstance(widget, ttk.Combobox) else 'normal')
        if value:self.progress.start(12)
        else:self.progress.stop()

    def start(self):
        if self.running:return
        try:
            self.before, ref, metadata = self.inputs()
            self.result=None; self.after_image=None; self.metrics.set('Đang tính toán…'); self.draw()
            self.save_image.configure(state='disabled'); self.save_bundle.configure(state='disabled')
            for b in self.stage_buttons:b.configure(state='disabled')
            self.key=uuid.uuid4().hex
            payload={'task':LABELS[self.task.get()], 'image':encoded(self.before), 'reference':encoded(ref) if ref else None, 'size':'original' if self.size.get()=='Gốc' else int(self.size.get()), 'demo_metadata':metadata}
            with engine.GUARD:engine.JOBS[self.key]={'state':'running','message':'Đang chuẩn bị…'}
            self.set_running(True)
            threading.Thread(target=engine.run_job,args=(self.key,payload),daemon=True).start()
            self.root.after(150,self.poll)
        except Exception as exc:messagebox.showerror('Không thể xử lý',str(exc),parent=self.root)

    def poll(self):
        if self.closed:return
        with engine.GUARD:job=dict(engine.JOBS[self.key])
        self.status.set(job['message'])
        if job['state']=='running':self.root.after(150,self.poll);return
        self.set_running(False)
        if job['state']=='error':self.metrics.set('Không có kết quả do lỗi xử lý.');messagebox.showerror('Lỗi phục hồi',job['message'],parent=self.root);return
        self.result=job['result'];self.before=Image.open(ROOT/'results'/self.key/'input.png').convert('RGB');self.stage.set(3);self.select_stage()
        for b in self.stage_buttons:b.configure(state='normal')
        self.save_image.configure(state='normal');self.save_bundle.configure(state='normal')
        w,h=self.result['resolution'];self.runtime.set(f'{w} × {h} px  ·  {self.result["seconds"]:.2f} giây suy luận đầy đủ  ·  {self.result["device"].upper()}')
        self.status.set(f'Hoàn tất · {w} × {h} px · {self.result["seconds"]:.2f} giây suy luận đầy đủ · {self.result["device"].upper()}')

    @staticmethod
    def metric_text(m):
        if m is None:return 'PSNR —    SSIM —'
        p='∞' if m['perfect_match'] else f'{m["psnr"]:.2f}'
        return f'PSNR {p} dB    SSIM {m["ssim"]:.4f}'

    def select_stage(self):
        if not self.result:return
        n=self.stage.get(); self.after_image=Image.open(ROOT/'results'/self.key/f'stage{n}.png').convert('RGB')
        m=self.result['stages'][n-1]['metrics']; base=self.result['baseline_metrics']
        self.metrics.set(f'Giai đoạn {n:02}:  {self.metric_text(m)}\nĐầu vào:       {self.metric_text(base)}' if m else f'Giai đoạn {n:02}:  PSNR —    SSIM —\nKhông có ảnh tham chiếu; đánh giá bằng quan sát.')
        self.note.set(self.result['demo_metadata']['description']+'\nChỉ số RGB tại kích thước xử lý; không phải benchmark bài báo.')
        self.draw()

    def draw(self):
        if not hasattr(self,'canvas'):return
        c=self.canvas;c.delete('all');w=max(c.winfo_width(),1);h=max(c.winfo_height(),1);self.display_photos=[]
        if self.before is None:c.create_text(w/2,h/2,text='Chọn ảnh để bắt đầu',fill=MUTED,font=('Segoe UI',15));return
        if self.after_image is None:
            im=ImageOps.contain(self.before,(max(w-24,1),max(h-48,1)));photo=ImageTk.PhotoImage(im);self.display_photos.append(photo)
            c.create_image(w/2,h/2,image=photo);c.create_text(w/2,15,text='ẢNH ĐẦU VÀO',fill=INK,font=('Segoe UI',10,'bold'));return
        if self.view.get()=='Cạnh nhau':
            for i,(im,label) in enumerate([(self.before,'ĐẦU VÀO'),(self.after_image,f'MPRNET · GIAI ĐOẠN {self.stage.get()}')]):
                thumb=ImageOps.contain(im,(max(w//2-20,1),max(h-50,1)));photo=ImageTk.PhotoImage(thumb);self.display_photos.append(photo)
                c.create_image((i+.5)*w/2,h/2+8,image=photo);c.create_text((i+.5)*w/2,17,text=label,fill=INK,font=('Segoe UI',10,'bold'))
            c.create_line(w/2,35,w/2,h-10,fill='#c6d3d6')
        else:
            a=ImageOps.contain(self.before,(max(w-24,1),max(h-50,1)));b=self.after_image.resize(a.size,Image.Resampling.LANCZOS)
            cut=int(a.width*self.ratio.get()/100);merged=b.copy()
            if cut:merged.paste(a.crop((0,0,cut,a.height)),(0,0))
            photo=ImageTk.PhotoImage(merged);self.display_photos.append(photo);x=(w-a.width)/2;y=(h-a.height)/2+8
            c.create_image(x,y,image=photo,anchor='nw');c.create_line(x+cut,y,x+cut,y+a.height,fill='white',width=3)
            c.create_text(12,17,text='ĐẦU VÀO',anchor='w',fill=INK,font=('Segoe UI',10,'bold'));c.create_text(w-12,17,text=f'MPRNET · GIAI ĐOẠN {self.stage.get()}',anchor='e',fill=INK,font=('Segoe UI',10,'bold'))

    def export_image(self):
        if not self.result:return
        target=filedialog.asksaveasfilename(parent=self.root,title='Lưu ảnh phục hồi',defaultextension='.png',initialfile=f'MPRNet-{self.source_path.stem}-stage{self.stage.get()}.png',filetypes=[('PNG','*.png')])
        if target:shutil.copyfile(ROOT/'results'/self.key/f'stage{self.stage.get()}.png',target);self.status.set('Đã lưu ảnh PNG.')

    def export_bundle(self):
        if not self.result:return
        target=filedialog.asksaveasfilename(parent=self.root,title='Lưu ảnh và số liệu',defaultextension='.zip',initialfile=f'MPRNet-{self.source_path.stem}.zip',filetypes=[('ZIP','*.zip')])
        if target:shutil.copyfile(ROOT/'results'/self.key/'bundle.zip',target);self.status.set('Đã lưu gói kết quả ZIP.')

    def close(self):
        if self.running:
            messagebox.showinfo('Đang xử lý', 'Vui lòng chờ mô hình hoàn thành trước khi đóng.', parent=self.root);return
        self.closed=True;self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();MPRNetApp(root);root.mainloop()
