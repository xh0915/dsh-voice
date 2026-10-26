# ============================================================
# 鲸歌 · dsh-voice 一键安装（Windows PowerShell）
# ============================================================
# 用法:
#   powershell -ExecutionPolicy Bypass -File install.ps1            # 安装
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Check     # 只检查环境，不安装
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall # 卸载
#
# 做了什么:
#   1. 检查 Python 3.9+（必需）
#   2. 检查 bl CLI（只有 STT 需要，缺失不阻断安装）
#   3. 把本目录复制到 ~\.dsh\skills\dsh-voice
#   4. 检查 BREEZE_API_KEY 是否已配置
#
# 零第三方依赖：不需要 pip install 任何东西。
# ============================================================

param(
    [switch]$Check,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$SkillName = "dsh-voice"
$SrcDir    = $PSScriptRoot
$DstDir    = Join-Path $HOME ".dsh\skills\$SkillName"

function Write-Ok  ($m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn2($m) { Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Write-Err2 ($m) { Write-Host "  [X]  $m" -ForegroundColor Red }

function Find-KeySource {
    if ($env:BREEZE_API_KEY) { return "环境变量" }
    $candidates = @(
        (Join-Path $HOME ".dsh\.env"),
        (Join-Path $DstDir ".env"),
        (Join-Path $SrcDir ".env"),
        (Join-Path (Split-Path $SrcDir -Parent) ".env")
    )
    foreach ($f in $candidates) {
        if ((Test-Path $f) -and (Select-String -Path $f -Pattern '^BREEZE_API_KEY=' -Quiet)) {
            return $f
        }
    }
    return $null
}

Write-Host "=========================================="
Write-Host " 鲸歌 · dsh-voice 安装器"
Write-Host "=========================================="
Write-Host "源目录: $SrcDir"
Write-Host "目标:   $DstDir"
Write-Host ""

# ---------------- 卸载 ----------------
if ($Uninstall) {
    if (Test-Path $DstDir) {
        Remove-Item -Recurse -Force $DstDir
        Write-Ok "已卸载: $DstDir"
    } else {
        Write-Warn2 "未安装过，无需卸载"
    }
    Write-Host ""
    Write-Host "注意: ~\.dsh\.env 里的 BREEZE_API_KEY 不会自动删除。"
    Write-Host "      如果 key 放在技能目录的 .env 里，会随目录一起删除。"
    exit 0
}

# ---------------- 检查 Python ----------------
Write-Host "[1/4] 检查 Python"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $py) {
    Write-Err2 "找不到 python。请安装 Python 3.9+"
    exit 1
}
$verText = & $py.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
$need    = & $py.Source -c "import sys; print(1 if sys.version_info >= (3,9) else 0)" 2>$null
if ($need -eq "1") {
    Write-Ok "Python $verText"
} else {
    Write-Err2 "Python $verText 过旧，需要 3.9+"
    exit 1
}

# ---------------- 检查 bl CLI（STT 用，可选）----------------
Write-Host ""
Write-Host "[2/4] 检查 bl CLI（只有语音识别 STT 需要）"
$bl = Get-Command bl -ErrorAction SilentlyContinue
if ($bl) {
    Write-Ok "bl 已安装"
} else {
    Write-Warn2 "未找到 bl —— 语音合成功能不受影响，只有语音识别用不了"
    Write-Host "     安装方法见 https://help.aliyun.com/zh/model-studio/"
}

# ---------------- 只检查模式 ----------------
if ($Check) {
    Write-Host ""
    Write-Host "[3/4] 检查 API key"
    $keySrc = Find-KeySource
    if ($keySrc) {
        Write-Ok "BREEZE_API_KEY 已配置（$keySrc）"
    } else {
        Write-Warn2 "BREEZE_API_KEY 未配置"
        Write-Host "     获取: https://breezeblue.ai/app/developer/api-keys"
    }
    Write-Host ""
    Write-Host "[4/4] 跳过安装（-Check 模式）"
    exit 0
}

# ---------------- 复制文件 ----------------
Write-Host ""
Write-Host "[3/4] 安装到 $DstDir"
New-Item -ItemType Directory -Force -Path $DstDir | Out-Null

# 只复制需要的文件，排除开发产物
foreach ($item in @("SKILL.md","README.md","README.en.md","LICENSE","CHANGELOG.md",".env.example","assets","reference")) {
    $src = Join-Path $SrcDir $item
    if (Test-Path $src) {
        $dstItem = Join-Path $DstDir $item
        if (Test-Path $dstItem) { Remove-Item -Recurse -Force $dstItem }
        Copy-Item -Recurse -Force $src $dstItem
        Write-Ok "复制 $item"
    }
}

# 清理字节码缓存
Get-ChildItem -Path $DstDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $DstDir -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

# ---------------- 检查 key ----------------
Write-Host ""
Write-Host "[4/4] 检查 API key"
$keySrc = Find-KeySource
if ($keySrc -eq "环境变量" -or $keySrc -eq (Join-Path $HOME ".dsh\.env") -or $keySrc -eq (Join-Path $DstDir ".env")) {
    Write-Ok "BREEZE_API_KEY 已配置（$keySrc）"
} elseif ($keySrc) {
    Write-Warn2 "已在 $keySrc 找到 BREEZE_API_KEY（仅从该目录运行时生效）"
    Write-Host "     如果 Harness 打开的就是这个工作区，可以直接用；否则请移到 $HOME\.dsh\.env"
} else {
    Write-Warn2 "BREEZE_API_KEY 尚未配置（合成时会报错）"
    Write-Host "     获取: https://breezeblue.ai/app/developer/api-keys"
    Write-Host "     配置: 在 ~\.dsh\.env 加一行  BREEZE_API_KEY=brz_你的key"
}

Write-Host ""
Write-Host "=========================================="
Write-Host " 安装完成"
Write-Host "=========================================="
Write-Host ""
Write-Host "在 DeepSeek Harness 里直接说："
Write-Host "  「把这段话读出来：你好世界」"
Write-Host "  「造一个温柔的女声讲睡前故事」"
Write-Host "  「把这章小说生成有声书」"
Write-Host ""
Write-Host "命令行直接用："
Write-Host "  python `"$DstDir\assets\breeze_tts.py`" speak `"你好`" -o hi.mp3"
Write-Host ""
Write-Host "验证安装："
Write-Host "  python `"$DstDir\assets\breeze_tts.py`" balance"
