#define AppName "VoiceType"
#define AppVersion "0.2.0"
#define AppPublisher "VoiceType"
#define AppExeName "VoiceType.exe"

[Setup]
AppId={{B85B9D0F-3DA8-4D7E-BB08-1652B9F930EA}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\VoiceType
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist-installer
OutputBaseFilename=VoiceType-Setup
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExeName}
Uninstallable=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=VoiceType.exe
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start VoiceType automatically when I sign in"; GroupDescription: "Additional options:"; Flags: unchecked

[Files]
Source: "..\dist\VoiceType\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\VoiceType"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\VoiceType"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VoiceType"; ValueData: """{app}\{#AppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch VoiceType"; Flags: postinstall nowait skipifsilent
