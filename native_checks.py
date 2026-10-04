"""End-to-end Tkinter integration and analytic metric checks; no gallery in UI."""
import json, time, zipfile, math
from unittest.mock import patch
import tkinter as tk
from PIL import Image
import numpy as np
from desktop import MPRNetApp, ROOT, read_file, encoded
import app as engine

root=tk.Tk();root.withdraw();ui=MPRNetApp(root);root.update()
assert ui.source is None and ui.result is None
assert str(ui.run_button['state'])=='disabled'
texts=[]
def walk(w):
    for c in w.winfo_children():
        if 'text' in c.keys():texts.append(str(c['text']))
        walk(c)
walk(root)
assert not any('ẢNH MẪU' in t or '.jpg' in t or '.jpeg' in t for t in texts)
fixture=ROOT/'validation'/'input.png'
assert fixture.exists()
ui.load(fixture);ui.size.set('256')
records=[]
for task,label in engine.TASKS.items():
    ui.task.set(label);ui.invalidate();ui.start();assert ui.running
    assert all(str(w['state'])=='disabled' for w in ui.controls)
    deadline=time.monotonic()+120
    while ui.running:
        root.update();time.sleep(.025)
        assert time.monotonic()<deadline
    assert ui.result is not None and ui.result['task']==task
    assert ui.result['baseline_metrics'] is None
    assert all(s['metrics'] is None for s in ui.result['stages'])
    assert ui.before.size==ui.after_image.size==tuple(ui.result['resolution'])
    for n in [1,2,3]:ui.stage.set(n);ui.select_stage();root.update();assert ui.after_image.size==ui.before.size
    ui.view.set('Kéo so sánh');ui.ratio.set(35);ui.draw();root.update()
    target=ROOT/'results'/f'checked-{task}.png'
    with patch('desktop.filedialog.asksaveasfilename',return_value=str(target)):ui.export_image()
    assert target.read_bytes()==(ROOT/'results'/ui.key/'stage3.png').read_bytes()
    target_zip=ROOT/'results'/f'checked-{task}.zip'
    with patch('desktop.filedialog.asksaveasfilename',return_value=str(target_zip)):ui.export_bundle()
    with zipfile.ZipFile(target_zip) as z:assert {'input.png','stage1.png','stage2.png','stage3.png','metrics.json'}<=set(z.namelist())
    records.append({'task':task,'seconds':ui.result['seconds'],'resolution':ui.result['resolution'],'passed':True})
# Original-resolution odd-size image + manually selected reference; no pre-resize.
odd=ROOT/'results'/'odd-fixture.png';Image.new('RGB',(127,119),(90,110,130)).save(odd)
ui.load(odd);ui.reference=read_file(odd);ui.task.set('Khử nhiễu');ui.size.set('Gốc');ui.invalidate();ui.start()
deadline=time.monotonic()+60
while ui.running:root.update();time.sleep(.025);assert time.monotonic()<deadline
assert ui.result['resolution']==[127,119] and ui.result['original_resolution']==[127,119] and not ui.result['resized']
assert ui.result['baseline_metrics']['perfect_match']
assert all(s['metrics'] is not None for s in ui.result['stages'])
ui.size.set('256');ui.invalidate();assert ui.result is None and ui.after_image is None and str(ui.save_image['state'])=='disabled'
# Invalid files and reference dimensions should fail rather than report fake scores.
bad=ROOT/'results'/'bad-image.txt';bad.write_text('not an image')
with patch('desktop.messagebox.showerror') as err:ui.load(bad);assert err.called
with patch('desktop.filedialog.askopenfilename',return_value=str(fixture)),patch('desktop.messagebox.showerror') as err:ui.open_reference();assert err.called
# Independent analytic PSNR/SSIM check on uniform RGB images.
x=Image.new('RGB',(32,32),(100,100,100));y=Image.new('RGB',(32,32),(110,110,110))
m=engine.quality(x,y);expected=20*math.log10(255/10)
assert abs(m['psnr']-expected)<1e-4
expected_ssim=(2*(100/255)*(110/255)+.01**2)/((100/255)**2+(110/255)**2+.01**2)
assert abs(m['ssim']-expected_ssim)<2e-4
assert engine.quality(x,x)['perfect_match']
root.destroy()
(ROOT/'native-check-results.json').write_text(json.dumps({'tasks':records,'checks':['empty startup without samples','manual file input','correct per-task checkpoint','locked controls while running','all three stages','side/slider comparison','PNG export','ZIP export','missing reference gives no scores','original odd dimensions preserved','manual reference metrics','stale result invalidated','invalid file rejected','reference size mismatch rejected','analytic PSNR and SSIM']},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(records,ensure_ascii=False,indent=2));print('PASS: native application and analytic metric checks')
