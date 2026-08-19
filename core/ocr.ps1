# Qingxin Translator - Windows OCR Script
# Uses Windows.Media.Ocr (built-in, zero dependencies)
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File ocr.ps1 -ImagePath "xxx.png"
# Output: __OCR_BASE64__:<base64(utf8 text)>  or  __OCR_ERROR__:<msg>  or  __OCR_EMPTY__

param(
    [Parameter(Mandatory=$true)]
    [string]$ImagePath
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime

[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null

# Async-to-sync helper
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await {
    param($WinRtTask, $ResultType)
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

try {
    # Open image file
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
    if (-not $file) {
        Write-Output "__OCR_ERROR__: cannot open image file"
        exit 1
    }

    # Decode image
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    # Create OCR engine (prefer Chinese, fallback to user profile)
    $lang = New-Object Windows.Globalization.Language("zh-CN")
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    if (-not $engine) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    }
    if (-not $engine) {
        Write-Output "__OCR_ERROR__: no OCR language pack available"
        exit 1
    }

    # Recognize
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $text = $result.Text

    if ($text) {
        # Output as base64 to avoid encoding issues
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
        $b64 = [Convert]::ToBase64String($bytes)
        Write-Output ("__OCR_BASE64__:" + $b64)
    } else {
        Write-Output "__OCR_EMPTY__"
    }

    $stream.Dispose()
} catch {
    $msgBytes = [System.Text.Encoding]::UTF8.GetBytes($_.Exception.Message)
    $msgB64 = [Convert]::ToBase64String($msgBytes)
    Write-Output ("__OCR_ERROR__:" + $msgB64)
    exit 1
}