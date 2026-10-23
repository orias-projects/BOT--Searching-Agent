# ============================================================================
# QUICK DEPLOY - Setup nhanh cho test 2 tiếng
# ============================================================================

Write-Host "`n🚀 QUICK DEPLOY SETUP`n" -ForegroundColor Cyan

# 1. Mở Windows Firewall
Write-Host "Step 1: Mở Windows Firewall cho port 8000..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "RAG Server Test" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 8000 `
        -Action Allow `
        -ErrorAction SilentlyContinue | Out-Null
    Write-Host "  ✅ Firewall rule đã tạo`n" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Firewall rule có thể đã tồn tại`n" -ForegroundColor Yellow
}

# 2. Lấy Local IP (LAN)
Write-Host "Step 2: Lấy địa chỉ IP..." -ForegroundColor Yellow
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | 
    Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"}
).IPAddress | Select-Object -First 1

Write-Host "  ✅ Local IP: $localIP`n" -ForegroundColor Green

# 3. Lấy Public IP
try {
    $publicIP = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 5).Content
    Write-Host "  ✅ Public IP: $publicIP`n" -ForegroundColor Green
} catch {
    $publicIP = "N/A"
    Write-Host "  ⚠️  Không lấy được Public IP (cần internet)`n" -ForegroundColor Yellow
}

# 4. Hiển thị kết quả
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "                    🎯 CÁCH TRUY CẬP SERVER" -ForegroundColor Cyan
Write-Host "============================================================================`n" -ForegroundColor Cyan

Write-Host "📱 TRUY CẬP TỪ THIẾT BỊ CÙNG WIFI (LAN):" -ForegroundColor Green
Write-Host "   http://${localIP}:8000" -ForegroundColor White
Write-Host "   → Bất kỳ thiết bị nào kết nối cùng WiFi có thể vào`n" -ForegroundColor Gray

if ($publicIP -ne "N/A") {
    Write-Host "🌍 TRUY CẬP TỪ INTERNET (WAN):" -ForegroundColor Green
    Write-Host "   http://${publicIP}:8000" -ForegroundColor White
    Write-Host "   → Cần PORT FORWARDING trên router:" -ForegroundColor Yellow
    Write-Host "      External Port: 8000 → Internal IP: $localIP → Internal Port: 8000`n" -ForegroundColor Gray
}

Write-Host "💻 TRUY CẬP TỪ MÁY NÀY:" -ForegroundColor Green
Write-Host "   http://localhost:8000" -ForegroundColor White
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "                    ⚙️  HƯỚNG DẪN PORT FORWARDING" -ForegroundColor Cyan
Write-Host "============================================================================`n" -ForegroundColor Cyan

Write-Host "Nếu muốn cho người ngoài internet vào (không cùng WiFi):`n" -ForegroundColor Yellow

Write-Host "1. Mở trình duyệt, vào địa chỉ router (thường là):" -ForegroundColor White
Write-Host "   - 192.168.1.1" -ForegroundColor Cyan
Write-Host "   - 192.168.0.1" -ForegroundColor Cyan
Write-Host "   - Hoặc xem trên router/modem`n" -ForegroundColor Cyan

Write-Host "2. Login vào router (admin/admin hoặc xem dưới router)`n" -ForegroundColor White

Write-Host "3. Tìm mục: Port Forwarding / Virtual Server / NAT`n" -ForegroundColor White

Write-Host "4. Thêm rule mới:" -ForegroundColor White
Write-Host "   - Service Name: RAG Server" -ForegroundColor Gray
Write-Host "   - External Port: 8000" -ForegroundColor Gray
Write-Host "   - Internal IP: $localIP" -ForegroundColor Gray
Write-Host "   - Internal Port: 8000" -ForegroundColor Gray
Write-Host "   - Protocol: TCP`n" -ForegroundColor Gray

Write-Host "5. Save và khởi động lại router`n" -ForegroundColor White

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "                    🚀 KHỞI ĐỘNG SERVER" -ForegroundColor Cyan
Write-Host "============================================================================`n" -ForegroundColor Cyan

Write-Host "Chạy lệnh sau để start server:`n" -ForegroundColor Yellow
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   python run.py`n" -ForegroundColor Cyan

Write-Host "Sau khi server chạy, share link cho người khác:" -ForegroundColor Green
Write-Host "   - Cùng WiFi: http://${localIP}:8000" -ForegroundColor White
if ($publicIP -ne "N/A") {
    Write-Host "   - Từ internet: http://${publicIP}:8000 (sau khi port forward)" -ForegroundColor White
}
Write-Host ""

Write-Host "============================================================================`n" -ForegroundColor Cyan

# 5. Hỏi có muốn start server ngay không
$start = Read-Host "Bạn có muốn start server ngay bây giờ không? (y/n)"
if ($start -eq "y" -or $start -eq "Y") {
    Write-Host "`n🚀 Starting server...`n" -ForegroundColor Cyan
    & ".\.venv\Scripts\Activate.ps1"
    python run.py
}
