# MPRNet Demo — Nhóm 13 · 74DCTT25

Ứng dụng desktop Tkinter phục hồi ảnh bằng MPRNet: khử nhiễu, khử nhòe và loại bỏ vệt mưa. Chạy cục bộ trên CPU hoặc GPU mà PyTorch nhận diện được.

## Cài đặt trên Windows

Cài Python 3.12 64 bit có pip và Tcl/Tk (Tkinter), cùng Git nếu dùng lệnh clone. Có thể tải ZIP từ GitHub và giải nén thay cho clone.

```powershell
git clone https://github.com/LazyBoyM/Paper12.git
cd Paper12
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe desktop.py
```

Sau khi cài, nhấp đúp start.bat để mở lại. Launcher dùng .venv nếu có, hoặc Python trên PATH. Cần mạng khi cài thư viện; xử lý ảnh chạy cục bộ. Dùng Python 3.12 64 bit để khớp bộ thư viện được kiểm tra.

Linux/macOS: tạo môi trường bằng python3 -m venv .venv, cài requirements.txt và chạy desktop.py bằng .venv/bin/python. Linux cần Tkinter (thường là gói python3-tk) và phiên đồ họa. Hai hệ điều hành này chưa được kiểm thử trong lần dọn dự án.

## Trọng số và sử dụng

Repository giữ ba checkpoint trong weights/ cùng manifest.json ghi nguồn và SHA-256. Nếu thiếu checkpoint, chạy:

```powershell
.venv\Scripts\python.exe download_models.py
```

Mở ảnh đầu vào, chọn tác vụ, chọn cạnh dài 256/384/512 hoặc kích thước gốc, rồi nhấn PHỤC HỒI ẢNH. Bắt đầu với 256 trên CPU. Có thể chọn ảnh sạch tham chiếu để tính PSNR/SSIM. Xem HUONG_DAN.md để biết cách so sánh và xuất ảnh/ZIP.

## Các file được giữ

- desktop.py: giao diện ứng dụng; app.py: bộ suy luận và chỉ số dùng chung.
- models/: ba kiến trúc MPRNet và giấy phép gốc.
- weights/: ba checkpoint chính thức và thông tin kiểm chứng.
- picture/: ảnh đầu vào mẫu để chọn thủ công.
- requirements.txt, download_models.py, start.bat, run.ps1: cài đặt và khởi chạy.
- native_checks.py, validation/input.png: kiểm tra giao diện, suy luận ba tác vụ, xuất file và chỉ số.

Kết quả xử lý, thư viện cài cục bộ và cache được bỏ qua bởi .gitignore. Không cần mang .deps lên GitHub. app.py được desktop.py dùng làm bộ suy luận; chạy desktop.py để mở giao diện đầy đủ.

## Kiểm tra

```powershell
.venv\Scripts\python.exe native_checks.py
```

Kiểm tra cần phiên đồ họa và đủ ba checkpoint, tạo results/ và native-check-results.json (không đưa lên Git).

## Nguồn và giấy phép

Kiến trúc và checkpoint: https://github.com/swz30/MPRNet (commit kiến trúc 43feb2aed45f5e0b9082c78c8c455160e30a3a82).
Bài báo: https://arxiv.org/abs/2102.02808.
Dự án được phân phối theo giấy phép học thuật phi thương mại gốc tại models/LICENSE.md; giữ thông báo bản quyền trong models/*.py.

