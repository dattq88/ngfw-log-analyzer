# 🛡️ THREATHUNTER M4 PRO EDITION - MASTER DOCUMENTATION

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)
- **Tên dự án:** ThreatHunter (PANW Log Visualizer)
- **Phiên bản:** v7.8 (Stable Bulletproof Edition)
- **Mục tiêu:** Nền tảng phân tích log tường lửa Palo Alto (NGFW) tốc độ cao, hoạt động hoàn toàn cục bộ (Local-first), tối ưu hóa cho kiến trúc bộ nhớ hợp nhất của chip Apple M4 Pro.
- **Triết lý thiết kế:** "Giao diện SOC tiêu chuẩn - Truy vấn Parquet siêu tốc - Đồ họa tương tác sâu".

---

## 2. KIẾN TRÚC KỸ THUẬT (TECH STACK)
- **Backend Core:** Python 3.12, FastAPI (Bất đồng bộ).
- **Data Engine:** DuckDB. Tự động chuyển đổi file `log.csv` thành `log.parquet` (Định dạng nén dạng cột nhị phân, tối ưu tốc độ đọc và tiết kiệm RAM). Sử dụng `TRY_CAST` để chống lỗi tràn bộ nhớ hoặc crash do dữ liệu rỗng/sai định dạng.
- **Frontend:** Vanilla HTML/JS/CSS (Không Framework) để triệt tiêu độ trễ render.
- **Data Visualization:** Apache ECharts 5.5.

---

## 3. ĐẶC TẢ GIAO DIỆN & TÍNH NĂNG (UI/UX SPECIFICATIONS)

Giao diện được chia thành 4 phân vùng chính, thiết kế theo tiêu chuẩn màn hình của Trung tâm điều hành an ninh mạng (SOC).

### VÙNG 1: Thanh Điều Hướng Toàn Cục (Header Panel)
Nằm ở trên cùng, dính chặt (sticky) vào màn hình khi cuộn.
- **Nút `[📁 Import Log]`**: Mở cửa sổ chọn file `.csv` từ máy tính. Sau khi chọn, hệ thống đẩy file lên Backend, tự động xóa file Parquet cũ, tạo file Parquet mới và reload lại trang.
- **Nút `[🌊 Mở Rộng Sankey]`**: Mở Modal hiển thị biểu đồ dòng chảy dữ liệu toàn màn hình.
- **Nút `[🌐 Mạng Lưới (Star Graph)]`**: Mở Modal hiển thị biểu đồ quan hệ Source ➔ Destination toàn màn hình.
- **Ô nhập liệu `[Tìm kiếm nhanh...]`**: Tìm kiếm toàn văn (Full-text search) áp dụng thuật toán `ILIKE` trên TẤT CẢ các cột của file log.
- **Nút `[Search]`**: Kích hoạt lệnh tìm kiếm từ ô nhập liệu trên.
- **Nút `[Reset All]`**: Xóa toàn bộ điều kiện lọc, reset thời gian về "24 Giờ qua", làm trống ô tìm kiếm và tải lại toàn bộ biểu đồ.

### VÙNG 2: Trung Tâm Cấu Hình & Bộ Lọc (Control Panel)
- **Khu vực 🕒 Thời gian (Time-bar):**
    - **Dropdown Presets:** Lựa chọn nhanh `[Tất cả]`, `[3 Giờ qua]`, `[24 Giờ qua]`. Khi chọn, hai ô thời gian Custom sẽ tự động ẩn/hiện và cập nhật giá trị.
    - **Ô nhập liệu Custom (Datetime-local):** Chọn ngày giờ bắt đầu và kết thúc cụ thể.
    - **Nút `[Áp dụng]`**: Cập nhật biểu đồ theo khung thời gian đã chọn.
- **Khu vực 🎨 Flow Designer (Thiết kế Luồng):**
    - Cho phép "lắp ghép" biểu đồ Sankey từ 1 đến tối đa 5 tầng dữ liệu.
    - **Ô nhập liệu (Có `<datalist>`):** Gõ tên trường (Ví dụ: `Rule`, `Application`). Hệ thống tự động gợi ý tên cột chính xác từ Metadata của file Parquet.
    - **Nút `[×]` (Màu đỏ):** Nằm cạnh mỗi tầng, dùng để xóa tầng đó khỏi biểu đồ.
    - **Nút `[+ Thêm tầng]`**: Bổ sung thêm một cấp độ phân tích mới.
    - **Nút `[▶ Cập nhật Biểu đồ]`**: Áp dụng cấu hình Flow mới vào Sankey.
- **Khu vực 🛠️ Filter Builder (Bộ lọc Thủ công):**
    - Hiển thị danh sách các điều kiện đang được áp dụng dưới dạng các Tag: `Cột = Giá trị [x]`.
    - **Dropdown Logic:** Chọn `AND` hoặc `OR` cho điều kiện tiếp theo.
    - **Ô nhập liệu Cột (Có `<datalist>`):** Chọn trường cần lọc (Vd: `Action`).
    - **Dropdown Toán tử:** Chọn `=` (Bằng), `!=` (Khác), `ILIKE` (Chứa).
    - **Ô nhập liệu Giá trị:** Nhập giá trị cần lọc (Vd: `deny`).
    - **Nút `[Lọc]`**: Thêm điều kiện vào mảng Filters và cập nhật toàn bộ hệ thống.

### VÙNG 3: Bảng Wigdets & Dữ Liệu Thô (Analytics Workspace)
- **Khu vực + Thêm Dashboard:** Cho phép người dùng tự tạo Widget mới bằng cách chọn Cột và Phương pháp tính toán (Count Sessions, Sum Total Bytes, Sum Sent, Sum Received).
- **Lưới Dashboards (Mặc định 6 cái):**
    - Hiển thị Top Source IP, Top App, Top Country theo Sessions và Bytes.
    - **Nút `[L]`**: Chuyển sang chế độ Danh sách (List). Hiển thị số liệu in đậm và tự động gắn đơn vị `MB` nếu đang tính theo dung lượng.
    - **Nút `[B]`**: Chuyển sang chế độ Biểu đồ Cột (Bar Chart).
    - **Nút `[P]`**: Chuyển sang chế độ Biểu đồ Tròn (Pie Chart).
    - **Nút `[X]`**: Xóa Widget khỏi màn hình.
    - **Tính năng Click-to-Filter:** Click vào bất kỳ dòng nào (List), cột nào (Bar) hoặc miếng bánh nào (Pie) để tự động thêm điều kiện đó vào Filter Builder.
- **Sankey Preview:** Bản thu nhỏ của biểu đồ dòng chảy dữ liệu.
- **Bảng Raw Logs:** Hiển thị 200 dòng log chi tiết nhất (mới nhất) dựa theo bộ lọc hiện tại để xuất bằng chứng (Evidence).

### VÙNG 4: Không Gian Điều Tra Chuyên Sâu (Fullscreen Modals)
Các cửa sổ Pop-up nền đen mờ (Backdrop blur) giúp tập trung tối đa, hiển thị nổi lên trên giao diện chính. Có nút `[Reset Filters]` và `[X ĐÓNG]` trên thanh tiêu đề.

#### 4.1. Modal Connected Star Graph (Mạng Lưới Hình Sao)
- **Chức năng:** Phát hiện máy chủ C2, rà quét mạng (Scanning), hoặc tấn công DDoS dựa trên cấu trúc Hub-and-Spoke.
- **Logic Dữ liệu:** Tự động lấy "Tầng 1" và "Tầng 2" từ Flow Designer làm Source và Destination. Tính toán `SUM(Bytes Sent)` làm trọng số.
- **Đồ họa:** - Sử dụng `Force-Directed Layout` (Lực hút vật lý). Các IP có kết nối sẽ tự động co cụm lại với nhau.
    - Độ lớn của Node (Chấm IP) tỷ lệ thuận với tổng dung lượng trao đổi.
    - Độ dày của Edge (Đường nối) thể hiện lượng Bytes Sent giữa 2 IP.
- **Tương tác:** Cuộn chuột để Zoom, Kéo nền để Pan, Kéo thả Node để sắp xếp cụm sao, Click vào Node để tự động lọc theo IP đó.

#### 4.2. Modal Deep Sankey Explorer (Sankey Toàn Màn Hình)
- **Chức năng:** Phân tích đường đi của dữ liệu qua nhiều trạm kiểm soát (Source ➔ Rule ➔ App ➔ Dest...).
- **Tooltip Intelligence:** Khi Hover (di chuột) vào một Node hoặc đường dẫn, sẽ hiển thị 4 chỉ số (đã được backend tính toán sẵn):
    1. Tổng số phiên (Sessions).
    2. Total Bytes (MB) - Màu xanh dương.
    3. Bytes Sent (MB) - Màu đỏ.
    4. Bytes Received (MB) - Màu xanh ngọc.
- **Tương tác:** Cuộn chuột để Zoom, Kéo nền để Pan, Kéo Node lên/xuống để làm rõ các đường nối bị chồng chéo. Click vào Node để tự động lọc hệ thống.

---