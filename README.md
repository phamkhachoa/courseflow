# CourseFlow

CourseFlow là một nền tảng quản lý học tập (LMS) giúp tổ chức vận hành toàn bộ vòng đời học tập: từ xây dựng khóa học, tuyển sinh, giao bài, chấm điểm, đến cấp chứng chỉ. Hệ thống được tổ chức theo các thành phần độc lập, mỗi thành phần đảm nhận một năng lực nghiệp vụ riêng và sở hữu dữ liệu của chính nó.

```text
courseflow/
  backend/           Hệ thống microservice (Spring Boot), BFF, worker và hạ tầng backend
  web/
    next-learning/   Web cho người học và trang công khai (Next.js), tối ưu SEO cho trang khóa học
    react-admin/     Bảng điều khiển vận hành/quản trị (React)
  app/               Ứng dụng di động cho người học (Flutter)
  docs/              Tài liệu sản phẩm và nghiên cứu dùng chung
```

## Tính năng chính

### Quản lý người dùng và tổ chức
- Đăng ký, đăng nhập, phân quyền theo vai trò (RBAC) và quản lý vòng đời phiên đăng nhập.
- Quản lý phòng ban, chương trình đào tạo, kỳ học và các lớp/khóa học theo cấu trúc tổ chức.

### Khóa học và lộ trình học tập
- Xây dựng danh mục khóa học, đề cương, mục tiêu đầu ra và quản lý tài liệu học tập.
- Tổ chức nội dung theo các học phần (Course Modules) và lộ trình học tập có cấu trúc.
- Theo dõi tiến độ hoàn thành từng học phần của người học.

### Tuyển sinh và ghi danh
- Quản lý danh sách lớp, trạng thái ghi danh, danh sách chờ và quyết định về sức chứa lớp học.

### Bài tập, bài kiểm tra và chấm điểm
- Định nghĩa bài tập, tiêu chí chấm (rubric) và quản lý thông tin bài nộp.
- Ngân hàng câu hỏi, bài kiểm tra có giới hạn thời gian, ghi nhận lần làm bài và tự động chấm điểm.
- Sổ điểm với hạng mục điểm, trọng số, điểm tổng kết, điều chỉnh điểm và lịch sử kiểm toán rubric.
- Đánh giá đồng cấp (peer review): phân công người chấm, nộp đánh giá, xử lý khiếu nại và chốt điểm.

### Hồ sơ học tập và phản hồi
- Lưu trữ minh chứng học tập, nhật ký, phản hồi và hồ sơ điểm đã công bố.

### Chứng chỉ
- Cấp, thu hồi và cấp lại chứng chỉ kèm mã xác thực.
- Trang xác minh chứng chỉ công khai cho bên thứ ba.

### Hạn nộp và nhắc nhở
- Quản lý lịch, khung thời gian đến hạn và quy tắc nhắc nhở tự động.

### Thông báo và tương tác
- Thông báo khóa học theo trạng thái nháp/lên lịch/đã công bố.
- Hộp thư thông báo, tùy chọn nhận thông báo và đẩy thông báo theo thời gian thực.
- Diễn đàn thảo luận với luồng bài, bình luận, phản ứng (reaction), kiểm duyệt và đánh dấu câu trả lời được chấp nhận.

### Tìm kiếm và phân tích
- Tìm kiếm khóa học và nội dung học tập dựa trên Elasticsearch.
- Báo cáo, chỉ số tiến độ học tập và tín hiệu cảnh báo người học có nguy cơ (student-at-risk).

### Tệp tin và đa phương tiện
- Quản lý metadata tệp, chính sách tải lên và cấp URL có chữ ký để truy cập an toàn.

## Trải nghiệm theo nền tảng

| Nền tảng | Mục đích | Tính năng tiêu biểu |
|---|---|---|
| Web học tập (Next.js) | Trang công khai, tối ưu SEO và server rendering | Danh mục và trang chi tiết khóa học, bài viết/đề cương, xác minh chứng chỉ, bảng điều khiển người học |
| Bảng quản trị (React) | Quy trình vận hành nội bộ cần thao tác nhanh | Quản lý người dùng/tổ chức, xuất bản khóa học, ghi danh, lên lịch thông báo, kiểm duyệt thảo luận, dashboard phân tích |
| Ứng dụng di động (Flutter) | Trải nghiệm gốc cho người học | Khóa học, bài tập, hạn nộp, học phần, làm bài kiểm tra, sổ điểm, thông báo realtime, hồ sơ học tập, thảo luận, hàng đợi đánh giá đồng cấp |

## Kiến trúc tổng quan

Mỗi service đảm nhận đúng một năng lực nghiệp vụ và sở hữu cơ sở dữ liệu riêng. Các service giao tiếp qua API hoặc sự kiện (event-driven), không truy cập trực tiếp vào dữ liệu của nhau.

- `api-gateway` là cổng vào duy nhất cho client: định tuyến, xác thực JWT, CORS, rate limit và làm sạch header.
- Các BFF (`learning-bff`, `backoffice-bff`) tổng hợp dữ liệu theo từng màn hình cho web và mobile.
- Tích hợp sự kiện qua Kafka với mẫu outbox và khử trùng lặp (dedup) để đảm bảo xử lý an toàn theo cơ chế at-least-once.
- Tìm kiếm dùng Elasticsearch; hạ tầng và observability tách biệt khỏi các module nghiệp vụ.

Chi tiết kỹ thuật về bounded context, luồng sự kiện và quy ước dữ liệu xem trong `backend/docs/architecture/backend-architecture.md`.
