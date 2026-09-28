# Windows 本机定时更新脚本（方案 B 用）
# 功能：跑爬取脚本 -> git 提交并推送到 Gitee
# 用法：powershell -ExecutionPolicy Bypass -File run_update.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> 1/3 运行爬取脚本 ..."
python update_source.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "update_source.py 执行失败"
    exit 1
}

if (Test-Path ".git") {
    Write-Host "==> 2/3 提交变更 ..."
    git add tvbox.json update.log sources.txt
    $msg = "auto update $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git commit -m $msg --allow-empty
    Write-Host "==> 3/3 推送到远程 ..."
    git push
    Write-Host "完成！Gitee 上的 tvbox.json 已更新。"
} else {
    Write-Host "当前目录不是 git 仓库，跳过推送。"
    Write-Host "请先: git clone 你的Gitee仓库地址，然后把本目录文件复制进去。"
}
