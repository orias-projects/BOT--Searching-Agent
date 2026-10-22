**[CONTEXT & OBJECTIVE]**

Dự án RAG này đang có 2 luồng hoạt động chính bị trộn lẫn:

1. Xử lý dữ liệu (đọc tài liệu, chunking, tạo vector embedding và đẩy lên Vector DB).
2. Vận hành Web (tiếp nhận truy vấn từ người dùng, tìm kiếm vector, gọi LLM và phản hồi).

**Nhiệm vụ của bạn:** Thực hiện một đợt **Refactor toàn diện (Major Refactor)** để tách biệt rõ ràng 2 luồng này, đồng thời quy hoạch lại toàn bộ thư mục dự án cho chuẩn mực và dễ mở rộng.

**[PROJECT STRUCTURE GUIDELINES]**
Hãy tổ chức lại cấu trúc thư mục ở thư mục gốc (root) như sau:

1. **`/data_builder` (Phase 1: Xây dựng dữ liệu):**
   * Chứa code xử lý pipeline: Extract -> Chunk -> Embed -> Load vào Vector DB.
   * Thiết kế theo  **cấu trúc Lab (Experimental/Pipeline structure)** : Nghĩa là chia thành các script, module độc lập hoặc jupyter notebooks để dễ dàng chạy thử nghiệm, tinh chỉnh chunking size, đổi mô hình embedding mà không ảnh hưởng đến web.
2. **`/web_services` (Phase 2: Vận hành Web):**
   * Chứa code phục vụ người dùng cuối (API, Frontend/Backend).
   * Thiết kế theo  **kiến trúc Microservices** : Tách biệt rõ các service như API Gateway, RAG Query Service, Chat History Service (nếu có).
3. **Các thư mục dùng chung (Shared root folders):**
   * `/database`: Chứa script khởi tạo DB, migration, và file `docker-compose.yml`.
   * `/documents`: Nơi lưu trữ các tài liệu thô (raw data) đầu vào.
   * `/configs`: Chứa các file cấu hình tổng (Global configs, biến môi trường, prompt templates).
   * `/assets`: Chứa các tài nguyên dùng chung (hình ảnh, icon, file tĩnh).

**[TECHNICAL CONSTRAINTS]**

* **Về Database:** Chuyển đổi thiết lập cơ sở dữ liệu (PostgreSQL + pgvector) về chạy local hoàn toàn. Hãy tạo một file `docker-compose.yml` trong thư mục `/database` để tôi có thể dễ dàng khởi chạy, kiểm soát, xem dữ liệu và sửa đổi cấu trúc ngay trên máy cá nhân.
* Đảm bảo tính độc lập: `/data_builder` và `/web_services` không được phụ thuộc chéo code của nhau một cách lộn xộn, chỉ nên gọi chung cấu hình từ `/configs`.

**[EXECUTION STEPS]**
Vui lòng thực hiện theo các bước sau, ở mỗi bước hãy tự kiểm thử và sửa lỗi nếu có sau đó tự làm bước tiếp theo:

1. **Analyze:** Đọc toàn bộ source code hiện tại để hiểu luồng chạy.
2. **Propose:** In ra cấu trúc cây thư mục (File Tree) mới mà bạn dự định di chuyển các file hiện tại vào.
3. **Refactor:** Bắt đầu di chuyển file, viết lại các file import, chia tách code theo đúng kiến trúc (Lab & Microservices) đã yêu cầu.
4. **Dockerize:** Viết file `docker-compose.yml` cho local database.
5. **Verify:** Cập nhật lại tài liệu `README.md` hướng dẫn cách chạy độc lập phần `data_builder` và phần `web_services`.

Toàn bộ quy trình tự động từ đầu đén cuối, không cần hỏi lại.
