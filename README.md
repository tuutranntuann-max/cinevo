# CINEVO - Website đặt vé xem phim

Gồm **React + Vite** (frontend), **Flask** (backend) và **SQLite** (database).
Thanh toán VietQR tạo mã theo số tiền và mã giao dịch từ ngân hàng nhận tiền đã cấu hình; khách cũng có thể mở website ngân hàng/ví để tự chuyển khoản. Nhân viên/quản lý/Admin vẫn xác nhận thủ công; chưa kết nối cổng thanh toán merchant hoặc tự xác minh tiền vào.

> Trợ lý Cinevo dành cho khách hàng dùng xử lý luật nội bộ, hỗ trợ các câu hỏi tiếng Việt và tiếng Anh, gợi ý phim, hướng dẫn đặt vé và xem trạng thái giao dịch trong tài khoản đã đăng nhập. Trợ lý không gọi dịch vụ AI bên ngoài, không hiểu hội thoại tự do như LLM và không xác minh tiền trực tiếp với ngân hàng. Các API AI khác và trang quản trị gợi ý AI vẫn được kiểm soát riêng bằng `FEATURE_AI`. Admin có trang **Trợ lý gửi OTP** chạy theo quy tắc cố định; chỉ gửi email xác minh đăng ký, không đọc hộp thư hay gửi nội dung tùy ý.

## 1. Yêu cầu cài đặt
- Python 3.10 trở lên
- Node.js 18 trở lên

## 2. Chạy backend (Flask)
(Tùy chọn) tạo file cấu hình: sao chép `.env.example` thành `.env`. Có thể bỏ qua khi phát triển, hệ thống tự dùng giá trị an toàn.
Mở terminal (PowerShell) tại thư mục dự án:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

- Lần chạy đầu tiên, `run.py` tự tạo file `backend/database/cinevo.db` cùng toàn bộ bảng và dữ liệu demo.
- Backend chỉ lắng nghe `127.0.0.1:5000` (kiểm tra: http://localhost:5000/api/health). Muốn mở cho mạng LAN phải đặt `HOST` trong `.env`, khi đó chế độ debug tự tắt.
- **Gửi OTP đăng ký bằng Gmail OAuth (khuyến nghị):** bật Gmail API trong Google Cloud, tạo OAuth Client ID/Secret, đăng nhập Admin → **Trợ lý gửi OTP** → nhập Client ID/Secret trực tiếp trên trang rồi bấm **Lưu cấu hình**. Các giá trị bí mật được mã hóa trong database bằng `SECRET_KEY`; trang không trả lại secret sau khi lưu. Đặt URI chuyển hướng được ủy quyền là `http://127.0.0.1:5000/api/admin/gmail-assistant/callback`, nhập cùng URI trong trang Admin, sau đó bấm **Kết nối Gmail** và cấp quyền trực tiếp tại Google. Ứng dụng chỉ xin `gmail.send`; không nhập mật khẩu Google vào Cinevo. Callback dùng POST để tránh ghi mã cấp quyền vào URL access log. Giữ `SECRET_KEY` ổn định để giải mã cấu hình và token. SMTP cũng có thể nhập tại trang Admin bằng Gmail App Password; không dùng mật khẩu đăng nhập Gmail thông thường.
- Nếu PowerShell chặn `activate`, chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Muốn tạo lại database từ đầu (ví dụ ngày suất chiếu demo đã cũ): `python database/seed.py --reset`.

> Suất chiếu demo được tạo cho **5 ngày kể từ lúc tạo database**. Nếu thấy hết suất chiếu, hãy chạy lệnh `--reset` ở trên.

## 3. Chạy frontend (React + Vite)
Mở terminal thứ hai:

```powershell
cd frontend
npm install
npm run dev
```

Mở http://localhost:5173. Vite tự chuyển tiếp mọi request `/api` sang backend (cấu hình trong `vite.config.js`), nên không bị lỗi CORS.

### Mở trên điện thoại/thiết bị cùng Wi-Fi (chỉ dùng phát triển)

1. Giữ backend chạy như bình thường trên máy phát triển.
2. Trong terminal frontend, chạy `npm run dev:lan`. Script mặc định chỉ bind vào Wi-Fi `192.168.10.6`, không bind vào các giao diện VPN khác.
3. Trên máy phát triển, tìm địa chỉ IPv4 của Wi-Fi bằng `ipconfig` (ví dụ `192.168.10.6`).
4. Trên điện thoại đang dùng cùng Wi-Fi, mở `http://<địa-chỉ-IPv4>:5173` (ví dụ `http://192.168.10.6:5173`).

Chế độ này chỉ dùng trong mạng riêng đáng tin cậy: Vite mở website và API proxy cho các thiết bị có thể truy cập máy phát triển trên mạng. Không dùng trên Wi-Fi công cộng; không cần mở cổng router hay đưa website lên Internet. Nếu địa chỉ Wi-Fi thay đổi, cập nhật IP trong script `dev:lan` ở `frontend/package.json`. Nếu Windows Firewall chặn, mở PowerShell **Run as administrator** và thêm quy tắc chỉ cho subnet Wi-Fi hiện tại (đổi subnet nếu `ipconfig` cho kết quả khác):

```powershell
New-NetFirewallRule -DisplayName "Cinevo Dev LAN Vite 5173" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5173 -RemoteAddress "192.168.10.0/24" -Profile Private
```

Để gỡ quy tắc sau khi dùng xong: `Remove-NetFirewallRule -DisplayName "Cinevo Dev LAN Vite 5173"`. Backend vẫn chỉ lắng nghe trên máy phát triển.

### Triển khai demo miễn phí trên Render

Repository có `render.yaml` để tạo frontend và backend từ nhánh `main`:

1. Đăng nhập Render, chọn **New → Blueprint** và kết nối `tuutranntuann-max/cinevo`.
2. Chọn nhánh `main`, xem trước hai dịch vụ `cinevo-web` và `cinevo-api`, rồi bấm **Apply**.
3. Khi cả hai dịch vụ triển khai xong, mở URL `onrender.com` của dịch vụ `cinevo-web`.

Render tự sinh `SECRET_KEY` riêng trong biến môi trường backend; không cần tải `.env` hoặc khóa bí mật lên GitHub. Nếu tên miền `cinevo-web.onrender.com` hoặc `cinevo-api.onrender.com` đã được dùng, đổi tên dịch vụ rồi cập nhật `CORS_ORIGINS` của backend và `VITE_API_URL` của frontend cho khớp.

Đây chỉ là demo: backend Free có thể ngủ sau thời gian không hoạt động; SQLite và các tệp tải lên nằm trên filesystem tạm thời, có thể mất khi restart/redeploy. Database demo được tạo lại từ dữ liệu seed, vì vậy không dùng dữ liệu khách hàng thật hoặc để dịch vụ này xử lý giao dịch thật. Render cấp domain `onrender.com` miễn phí; domain riêng cần được sở hữu/cấu hình riêng.

## 4. Tài khoản test
| Vai trò | Email | Mật khẩu | Vào trang |
|---|---|---|---|
| USER | user@cinevo.vn | User@123 | `/user` |
| MANAGER | manager@cinevo.vn | Manager@123 (development only) | `/manager` |
| ADMIN | admin@cinevo.vn | Admin@123 (development only) | `/admin` |

Đăng nhập tại `/user/login`. Hệ thống tự chuyển ADMIN sang `/admin`, MANAGER sang `/manager`. Đăng nhập chỉ cần email và mật khẩu. Khi development chưa kết nối Gmail OAuth hoặc cấu hình SMTP, OTP đăng ký dùng mã demo **123456**. Trên Render, mật khẩu MANAGER và ADMIN được sinh riêng qua `MANAGER_BOOTSTRAP_PASSWORD` và `ADMIN_BOOTSTRAP_PASSWORD`; xem các giá trị này trong Environment của API service. Không dùng mật khẩu development mặc định trên dịch vụ công khai.

Nhân viên/quản lý đăng nhập tại **Cổng nhân viên** hoặc `/manager/login`. Tài khoản mới gửi hồ sơ tại `/staff/register` gồm họ tên, email, điện thoại, CCCD, địa chỉ, giới tính và nghề nghiệp/tình trạng. Admin duyệt tại **Admin → Hồ sơ nhân viên** và cấp mã mời một lần (hạn 7 ngày); người đăng ký cần mã để tạo mật khẩu và kích hoạt tài khoản. Nhân viên và quản lý có chung quyền quản lý rạp.

Quản trị viên có thể đăng nhập tại `/admin/login`. Trong **Phim → Suất chiếu**, chọn **＋ Thêm phim mới bằng cách nhập thông tin...** để tạo phim ngay trong lúc lập lịch chiếu. Ở trang **Phim**, có thể tải poster JPG, PNG, WEBP tối đa 5 MB và video nền MP4/WebM tối đa 10 GB lên backend. Video trailer phát tự động, không tiếng và lặp lại trong banner phim trang chủ; có thể đổi hoặc xóa video tại trang quản lý phim. Hỗ trợ video 4K tùy codec mà trình duyệt hỗ trợ. Cần đủ dung lượng ổ đĩa để lưu video lớn.
Trang **Tổng quan hệ thống** hiển thị biểu đồ doanh thu đã thanh toán theo tuần, tháng và năm, kèm biểu đồ thu–chi–lãi/lỗ. Admin có thể nhập và xóa khoản chi với ngày, nội dung và số tiền; khoản chi được phân bổ vào báo cáo theo ngày ghi nhận.

## 5. Luồng khách hàng đã được đáp ứng
```
Trang chủ → Chọn khu vực → Khám phá phim → Chi tiết phim → Chọn ngày & rạp → Chọn suất chiếu
→ Chọn ghế
→ [Bấm Tiếp tục] CHƯA đăng nhập mới hiện popup "Đăng nhập Cinevo" (Đăng ký / Đăng nhập)
→ Đăng ký: Họ tên, Email, SĐT, Mật khẩu, Nhập lại mật khẩu, đồng ý điều khoản
→ Xác thực OTP 6 số → tài khoản USER / ACTIVE
→ Xác nhận đặt vé (đơn được GIỮ NGUYÊN, không phải chọn lại; có thể nhập mã giảm giá)
→ Chọn combo (hoặc Bỏ qua) → Thanh toán QR và nhập mã giao dịch làm nội dung chuyển khoản
→ Nhân viên/quản lý/Admin xác nhận → Vé điện tử có mã dạng CV10260001 + QR
→ Vé của tôi (đang chờ xác nhận / sắp tới có nút Xem QR / đã xem)
```
Chi tiết kỹ thuật của từng yêu cầu:
- **Chỉ yêu cầu đăng nhập sau bước chọn ghế**: `SeatSelectionPage` gọi `requireLogin()` (xem `context/AuthContext.jsx`). Các trang khám phá là công khai.
- **Giữ nguyên đơn hàng**: `context/BookingContext.jsx` lưu suất chiếu, ghế, combo vào `localStorage`, nên đăng nhập, đăng ký hay tải lại trang đều không mất.
- **OTP email**: chỉ khi đăng ký tài khoản khách, mã dùng một lần được gửi qua Gmail OAuth (hoặc SMTP tương thích cũ); mã hết hạn sau 10 phút. Đăng nhập khách/Admin/nhân viên không yêu cầu OTP.
- **Email trùng**: backend trả `EMAIL_EXISTS`, frontend hiện "Email này đã được sử dụng. Bạn đã có tài khoản? [Đăng nhập]".
- **Ảnh đại diện**: người dùng đổi/xóa ảnh tại `/user/profile`; backend kiểm tra định dạng và giới hạn 5 MB, cập nhật avatar trên thanh điều hướng và lưu ảnh trong `backend/uploads/avatars`.
- **Role khách hàng luôn là USER**: `routes/auth.py` không đọc trường `role` từ client. Nhân viên/quản lý mới chỉ kích hoạt được bằng mã mời Admin duyệt; mã dùng một lần.
- **Chat hỗ trợ**: khách phải đăng nhập để nhắn tin. Hệ thống báo đang tìm nhân viên; nhân viên/quản lý nhận cuộc trò chuyện trước khi trả lời và tên người phụ trách hiển thị cho khách.
- **Giá tính ở server**: client chỉ gửi `showtime_id`, `seat_ids`, `foods`; backend tự tính tiền (ghế VIP +20.000đ).
- **Mã giảm giá**: nhập mã ở bước xác nhận đặt vé; chỉ mã đang hoạt động mới được áp dụng. Phần trăm và số tiền giảm được tính lại tại backend trên tổng tiền vé và combo sau ưu đãi thành viên; mỗi đơn áp dụng một mã, mã có thể dùng lại ở các đơn khác.
- **Chống đặt trùng ghế**: ràng buộc `UNIQUE(showtime_id, seat_id)` ở bảng `booking_seats`.
- **Giữ ghế**: ghế khách chọn được giữ tối đa 10 phút; bộ đếm phút/giây hiển thị ở màn hình chọn ghế và thanh toán. Đơn QR chưa được xác nhận cũng hết hạn sau 10 phút. Cứ 3 lần hết hạn trừ 1 điểm uy tín; sau 3 lần bị trừ điểm đặt ghế sẽ tạm khóa 24 giờ.
- **Ghế đôi**: Admin cấu hình tại `/admin/seats`, Quản lý tại `/manager/seats`; chọn một ghế trong cặp rồi bấm “Ghế đôi” để ghép tự động với ghế liền kề (1–2, 3–4...). Cả hai ghế sáng lên khi cấu hình/chọn cặp; khách có thể bấm một ghế trong cặp để chọn hoặc bỏ chọn cả hai. Cả hai chỗ được giữ/đặt và tính tiền riêng theo giá từng ghế.
- **Gói thành viên**: Bạc/Vàng/Kim cương có hiệu lực 30 ngày; giá do Admin nhập tại Quản lý → Giao dịch. Ưu đãi giảm đồ ăn/hàng hóa lần lượt 10%/15%, 20%/30%, 45%/45%; không giảm vé. Hạn mức đặt vé mỗi ngày là 5, 10 và không giới hạn. Chỉ thành viên có gói đang hoạt động mới xem được phim trực tuyến; khách chưa có gói chỉ xem phần giới thiệu. Gói được kích hoạt sau khi nhân viên xác nhận thanh toán.
- **VietQR/ngân hàng**: Admin chọn ngân hàng nhận tiền, nhập số tài khoản và tên chủ tài khoản trong Quản lý → Giao dịch. VietQR được tạo tự động theo giao dịch; ảnh QR tùy chỉnh không bắt buộc. Khách có thể mở website ngân hàng hoặc ví, nhưng cần tự nhập lệnh chuyển khoản; không nhập thông tin đăng nhập trên Cinevo.
- **Cinevo Shop**: khách đặt kính 3D/vật tư và nhận tại rạp; đơn được xác nhận chuyển khoản trước khi nhân viên đánh dấu đã giao. Quản lý/nhân viên/Admin được quản lý kho và xử lý đơn.
- **Vé của tôi**: nhóm Sắp tới / Đã xem dựa theo giờ chiếu.

## 6. Phân quyền
| Route | Ai được vào |
|---|---|
| `/user/*` (khám phá, chọn ghế, đăng nhập) | Công khai |
| `/user/checkout`, `food`, `payment`, `booking-success`, `my-tickets`, `profile` | Đã đăng nhập |
| `/manager/*` | EMPLOYEE, MANAGER, ADMIN |
| `/admin/*` | ADMIN |
| Gửi hồ sơ/kích hoạt mã mời nhân viên | Công khai; kích hoạt cần mã hợp lệ |
| Xem và duyệt hồ sơ nhân viên | ADMIN |

Frontend chặn bằng `ProtectedRoute`, và **backend kiểm tra lại** bằng `@roles_required` ở mọi API `/api/manager/*`, `/api/admin/*`.

## 7. Cấu trúc thư mục
```
Cinevo/
├── frontend/
│   ├── src/
│   │   ├── components/   Navbar, AuthPanel, AuthModal, SeatMap, TicketCard, ResourcePage...
│   │   ├── pages/
│   │   │   ├── user/     14 trang khách hàng
│   │   │   ├── manager/  9 trang quản lý rạp
│   │   │   └── admin/    10 trang quản trị
│   │   ├── layouts/      UserLayout, ManagerLayout, AdminLayout (+ PanelLayout dùng chung)
│   │   ├── services/     api.js (fetch + JWT) và các service gọi API
│   │   ├── context/      AuthContext (đăng nhập, popup), BookingContext (đơn đang đặt)
│   │   ├── utils/        format.js (tiền, ngày giờ)
│   │   ├── App.jsx       toàn bộ Router
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── app/
│   │   ├── routes/       auth, staff_accounts, support_chat, movies, cinemas, showtimes, bookings, admin, manager, ai
│   │   ├── models/       User, Role, Movie, Cinema, Room, Seat, Showtime, Booking, Food, Payment, Promotion (+ ActivityLog)
│   │   ├── services/     auth_service.py (JWT, phân quyền, OTP), booking_service.py (đặt vé)
│   │   ├── ai/           recommendation_service.py, seat_recommendation.py, chatbot_service.py
│   │   ├── config.py
│   │   └── __init__.py   application factory
│   ├── database/         seed.py (dữ liệu demo) + file cinevo.db sinh ra khi chạy
│   ├── requirements.txt
│   └── run.py
├── .env.example
├── .gitignore
└── README.md
```

## 8. Module AI (TẠM TẮT, giữ code)
Mặc định `FEATURE_AI=false` (xem `.env.example`). Khi tắt: không đăng ký route AI, `/api/admin/ai-settings` trả 404, frontend ẩn chatbot, mục gợi ý phim, nút gợi ý ghế và trang Quản lý AI. Trang Trợ lý gửi OTP riêng vẫn khả dụng cho Admin mà không bật các tính năng AI khác.

| Class | File | Hiện tại | Nơi gắn AI thật |
|---|---|---|---|
| `MovieRecommendationService` | `ai/recommendation_service.py` | Lọc theo thể loại, xếp theo điểm | `recommend()` |
| `SeatRecommendationService` | `ai/seat_recommendation.py` | Chấm điểm vị trí, tìm 1-2 ghế liền kề gần trung tâm | `recommend()` |
| `ChatbotService` | `ai/chatbot_service.py` | Trả lời theo từ khóa | `reply()` |

API: `GET /api/ai/recommend-movies?genre=`, `GET /api/ai/recommend-seats?showtime_id=&count=`, `POST /api/ai/chat`.
Mỗi chỗ cần gọi AI thật đều có comment `TODO (AI thật)`.

## 9. Chuyển sang PostgreSQL
Dùng SQLAlchemy nên không cần sửa model. Cài `pip install psycopg2-binary`, rồi đặt `DATABASE_URL` trong `.env`
(ví dụ `postgresql+psycopg2://user:pass@localhost:5432/cinevo`).

## 10. Bảo mật và cấu hình môi trường
| Hạng mục | Cách xử lý |
|---|---|
| `SECRET_KEY` | Production **bắt buộc** khóa ≥ 32 ký tự, thiếu/yếu là không khởi động. Development tự sinh khóa ngẫu nhiên (file `backend/database/.dev_secret_key`, đã ignore) |
| Debug | Chỉ bật ở development **và** khi `HOST` là localhost |
| OTP | Chỉ xác minh đăng ký. Gmail OAuth/SMTP: gửi mã ngẫu nhiên thật, không trả mã ra API. Development chưa cấu hình gửi mail: mã demo `123456` + gợi ý giao diện. Production chưa cấu hình gửi mail: báo lỗi gửi mã |
| Giới hạn lần thử | Đăng nhập 10 lần/5 phút (theo IP + email); OTP 5 lần/10 phút/email; đăng ký 10 lần/giờ/IP. Trả `429` + `Retry-After` |
| Dữ liệu vào | Giới hạn độ dài, kiểm tra kiểu và giá trị; JSON hỏng trả `400`; body tối đa 1 MB |
| Hồ sơ nhân viên | CCCD và địa chỉ được mã hóa khi lưu; chỉ ADMIN xem hồ sơ. Giữ `SECRET_KEY` ổn định và sao lưu an toàn để có thể giải mã dữ liệu. |
| Giờ | Mốc hệ thống lưu UTC; giờ chiếu là giờ Việt Nam (UTC+7), xem `app/timeutil.py` |
| Header | `nosniff`, `X-Frame-Options`, `Referrer-Policy`; HSTS ở production |

Còn tồn đọng (ghi nhận, xử lý ở phase sau): token JWT lưu `localStorage` và chưa thu hồi được phía server; bộ đếm giới hạn lần thử là in-memory (cần Redis khi chạy nhiều worker); `npm audit` báo `vite` và `react-router-dom` có bản vá ở phiên bản major mới, chưa nâng cấp; chưa có migration (Alembic).

## 11. Kiểm thử
```powershell
cd backend
pip install -r requirements-dev.txt
python -m pytest
```
Bộ test (`backend/tests/`) gồm tài khoản, chống nâng quyền, ma trận phân quyền, token giả, tranh chấp ghế (12 request đồng thời), giá do server tính, validate, rate limit, cấu hình production.

## 12. Git và điểm khôi phục
Dự án đã có Git. Tag `phase0-baseline` là bản trước khi gia cố. Quay lại: `git checkout phase0-baseline`.
Trước mỗi thay đổi lớn hãy `git commit` và đặt tag mới.

### Triển khai demo trên Render
Blueprint `cinevo-render-demo` lấy cấu hình từ `main` và mã chạy từ nhánh `render-deploy`. Nhánh deploy bỏ qua môi trường cài đặt, cache và video Git LFS để Render có thể clone/build nhanh; nhánh `main` và dữ liệu gốc không bị thay đổi. Sau khi cập nhật mã nguồn, đồng bộ thay đổi cần triển khai sang `render-deploy`.

Demo Free dùng SQLite và lưu tệp trên filesystem tạm thời; dữ liệu có thể mất khi dịch vụ khởi động lại hoặc triển khai lại. Không dùng dịch vụ này với dữ liệu khách hàng thật hoặc giao dịch thật.

## 13. Giới hạn thanh toán
- Việc xác nhận giao dịch là thao tác thủ công sau khi nhân viên kiểm tra biến động ngân hàng; chưa tích hợp webhook ngân hàng/cổng thanh toán, vì vậy trạng thái “đã thanh toán” không được xác minh tự động.
- Không nhập hoặc lưu thông tin thẻ/tài khoản ngân hàng của khách. QR VietQR được tạo theo số tiền và nội dung giao dịch; khách cần kiểm tra người nhận, chuyển đúng số tiền và mã giao dịch. Mọi thanh toán vẫn cần nhân viên xác nhận.
- OTP đăng ký dùng Gmail OAuth khi đã kết nối; SMTP App Password vẫn được hỗ trợ tương thích. Giao hàng tận nơi và thanh toán trực tuyến tự động chưa được tích hợp.
