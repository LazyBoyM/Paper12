# Ứng dụng Python MPRNet

Nhấp đúp **start.bat** để mở ứng dụng. Hoặc chạy `python desktop.py` trong môi trường có các thư viện cần thiết. Không cần trình duyệt; ứng dụng không tự nạp hay hiển thị ảnh mẫu.

## Sử dụng

1. Nhấn **Mở ảnh đầu vào** và chọn ảnh của bạn.
2. Chọn đúng tác vụ: **Khử nhiễu**, **Khử nhòe**, **Loại bỏ vệt mưa**. Mỗi tác vụ dùng một checkpoint chính thức riêng.
3. Chọn **Gốc** để giữ độ phân giải, hoặc cạnh dài 512 / 384 / 256 pixel để chạy nhanh trên CPU. Mặc định 512; ảnh nhỏ hơn mức chọn không bị phóng lớn. Ảnh rất lớn có thể chạy chậm hoặc thiếu bộ nhớ, nên bắt đầu với 256/512.
4. Nếu có ảnh sạch cùng cảnh, cùng kích thước và căn chỉnh chính xác, nhấn **Chọn ảnh sạch tham chiếu**. Nếu không có thì bỏ qua.
5. Nhấn **PHỤC HỒI ẢNH**, chờ hoàn tất rồi xem giai đoạn 01 / 02 / 03. So sánh cạnh nhau hoặc kéo thanh so sánh.
6. **Lưu ảnh PNG** xuất giai đoạn đang xem. **Lưu kết quả ZIP** xuất ảnh đầu vào tại kích thước xử lý, cả ba đầu ra, tham chiếu nếu có và metrics.json.

Ứng dụng xử lý trực tiếp ảnh đã chọn, không tự tạo nhiễu, nhòe hoặc mưa. Đổi ảnh, tác vụ, kích thước hay tham chiếu sẽ xóa kết quả cũ trên giao diện, cần chạy lại. Các thao tác thay đổi đầu vào bị khóa trong lúc xử lý để tránh trộn các lượt chạy.

Đóng cửa sổ để thoát. Nếu đang chạy, chờ hoàn thành rồi đóng. Kết quả tự lưu trong `results/<mã phiên>` trên máy.

## Đánh giá kết quả

Không có ảnh sạch tham chiếu thì không có PSNR/SSIM; không thể suy ra độ chính xác chỉ từ việc ảnh trông sắc nét hơn. Ảnh tham chiếu phải đúng cảnh và được căn chỉnh, không chỉ cùng kích thước.

PSNR dùng MSE RGB trên [0,1]. SSIM dùng cửa sổ Gaussian 11 × 11, sigma=1,5, miền hợp lệ và trung bình RGB. Điểm số tính trên PNG 8 bit ở kích thước xử lý; ảnh tham chiếu được thu gọn tương ứng nếu chọn giới hạn cạnh dài. Không so trực tiếp với benchmark khử mưa kênh Y của bài báo.

Thời gian là suy luận đủ ba giai đoạn, không gồm tải mô hình, đọc/ghi ảnh hay tính chỉ số. Chuyển nút giai đoạn chỉ đổi đầu ra đang xem, không phải dừng sớm.

MPRNet phụ thuộc dữ liệu huấn luyện và kiểu suy giảm. Khử nhòe được huấn luyện với nhòe chuyển động; khử nhiễu với nhiễu ảnh thực; khử mưa hướng tới vệt mưa. Chọn đúng tác vụ không bảo đảm mọi ảnh đều cải thiện. Ứng dụng không huấn luyện lại mô hình.

## Cài trên máy khác

Xem README.md để tải dự án, tạo môi trường Python và cài đúng requirements.txt.
Ba checkpoint chính thức được giữ trong weights/, không cần tải lại nếu đã tải đủ repository.
Không cần thư mục .deps hay kết quả cũ trong results/. Ứng dụng tự tạo results/ khi xử lý ảnh.
## Nguồn và tệp

- desktop.py: giao diện Tkinter.
- app.py: phần suy luận PyTorch dùng chung; launcher mặc định mở desktop.
- weights/manifest.json: nguồn và SHA-256 ba checkpoint chính thức.
- native_checks.py: kiểm thử luồng ứng dụng và tính chỉ số.
- https://arxiv.org/abs/2102.02808
- https://github.com/swz30/MPRNet
- Kiến trúc gốc tại commit 43feb2aed45f5e0b9082c78c8c455160e30a3a82; giấy phép học thuật phi thương mại tại models/LICENSE.md.

Phiên bản đã chuẩn bị dùng Python 3.12.14, PyTorch 2.6.0+cpu, NumPy, Pillow, Tkinter. Trọng số và ảnh được xử lý cục bộ.

