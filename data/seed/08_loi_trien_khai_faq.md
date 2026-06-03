# [MINH HOẠ] FAQ lỗi triển khai thường gặp (cho đội triển khai)

Đây là nhóm tri thức phục vụ ĐỘI TRIỂN KHAI — điểm khác biệt của flagship.

- **Không kết nối được SQL Server**: kiểm tra chuỗi kết nối (connection string), dịch vụ SQL Server đang chạy, firewall/port 1433, thông tin đăng nhập SQL.
- **Người dùng không thấy dữ liệu mong đợi**: thường do phân quyền dữ liệu theo vai trò/đơn vị — kiểm tra cấu hình phân quyền của người dùng.
- **Lệch số dư đầu kỳ sau khi chuyển đổi dữ liệu**: đối chiếu bảng ánh xạ tài khoản và số dư import; kiểm tra tỷ giá/đơn vị tính.
- **Import Excel báo lỗi**: kiểm tra đúng mẫu template, định dạng cột (ngày, số), mã danh mục đã được khai báo trước.
- **Báo cáo lệch giữa các phân hệ**: kiểm tra chứng từ chưa ghi sổ hoặc kỳ kế toán chưa khóa.

> Tài liệu MINH HOẠ cho POC — quy trình xử lý thật cần verify với tài liệu/kinh nghiệm triển khai BRAVO.
