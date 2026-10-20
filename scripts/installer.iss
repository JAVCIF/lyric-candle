; Build with scripts/build_installer.py. AppId stays stable across upgrades.
[Setup]
AppId={{E9BC91D4-3C79-49AD-866F-37AE0D16B58B}
AppName=Lyric Candle
AppVersion={#AppVersion}
AppPublisher=JAVCIF
AppPublisherURL=https://github.com/JAVCIF/lyric-candle
AppSupportURL=https://github.com/JAVCIF/lyric-candle/issues
DefaultDirName={localappdata}\Programs\LyricCandle
DefaultGroupName=Lyric Candle
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile={#RepoRoot}\LICENSE
SetupIconFile={#RepoRoot}\lyric_candle\assets\logo.ico
UninstallDisplayIcon={app}\LyricCandle.exe
OutputBaseFilename=Lyric-Candle-{#AppVersion}-Setup-x64
VersionInfoVersion={#AppNumericVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Excludes: "\portable.txt,\data\*"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lyric Candle"; Filename: "{app}\LyricCandle.exe"
Name: "{autodesktop}\Lyric Candle"; Filename: "{app}\LyricCandle.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LyricCandle.exe"; Description: "{cm:LaunchProgram,Lyric Candle}"; Flags: nowait postinstall skipifsilent
