; Qingxin Translator - Inno Setup 安装脚本
; 使用方法：安装 Inno Setup 6 后，双击此文件编译即可生成安装程序

#define MyAppName "青欣翻译"
#define MyAppNameEn "Qingxin Translator"
#define MyAppVersion "0.3.6"
#define MyAppPublisher "Qingxin"
#define MyAppExeName "QingxinTranslator.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=Copyright (C) 2024 {#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=QingxinTranslator-Setup-{#MyAppVersion}
; 安装程序图标
SetupIconFile=resources\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 语言
LanguageDetectionMethod=uilanguage
ShowLanguageDialog=no
; 外观
WizardSizePercent=100
WizardImageFile=resources\icons\app_128.png
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Launch at Windows startup"; GroupDescription: "Additional options:"; Flags: unchecked

[Files]
; 主程序（onedir 模式：整个目录递归安装，含 exe 与 _internal）
Source: "dist\QingxinTranslator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 默认配置文件（安装到 {app}\data\config.json）
Source: "data\config.json"; DestDir: "{app}\data"; Flags: ignoreversion

[Icons]
; 开始菜单
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; 开机自启动（可选）
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "Qingxin_Translator"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时清理用户数据目录（可选，取消注释则卸载时删除数据）
; Type: filesandordirs; Name: "{app}\data"

[Code]
// 安装前检查是否正在运行
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // 尝试结束正在运行的进程
  Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
