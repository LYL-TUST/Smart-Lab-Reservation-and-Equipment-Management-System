# 测试登录接口
$body = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

Write-Host "测试登录接口..." -ForegroundColor Yellow
Write-Host "请求体: $body" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/auth/login" -Method Post -Body $body -ContentType "application/json"
    Write-Host "`n登录成功!" -ForegroundColor Green
    Write-Host "响应数据:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "`n登录失败!" -ForegroundColor Red
    Write-Host "错误信息: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "详细错误: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

