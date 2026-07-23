#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{B52596D7-1B18-4A27-86AD-F749AA881E5F}
AppName=nfprogress
AppVersion={#AppVersion}
AppVerName=nfprogress {#AppVersion}
AppPublisher=nfproject
DefaultDirName={localappdata}\Programs\nfprogress
DefaultGroupName=nfprogress
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=nfprogress-setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\nfprogress.exe
UninstallFilesDir={localappdata}\nfprogress\uninstall
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: checkedonce

[Files]
Source: "dist\nfprogress\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\nfprogress"; Filename: "{app}\nfprogress.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\nfprogress"; Filename: "{app}\nfprogress.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\nfprogress.exe"; Description: "Запустить nfprogress"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\nfprogress\updater"
Type: filesandordirs; Name: "{localappdata}\nfprogress\updates"
