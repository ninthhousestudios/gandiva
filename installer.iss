[Setup]
AppName=Gandiva
AppVersion=0.1.0
AppPublisher=Ninth House Studios, LLC
AppPublisherURL=https://ninthhouse.studio
DefaultDirName={autopf}\Gandiva
DefaultGroupName=Gandiva
OutputDir=build
OutputBaseFilename=gandiva-0.1.0-setup
SetupIconFile=prometheus-footer.ico
UninstallDisplayIcon={app}\gandiva.exe
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
LicenseFile=LICENSE

[Files]
Source: "build\app.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Gandiva"; Filename: "{app}\gandiva.exe"; IconFilename: "{app}\gandiva.exe"
Name: "{group}\Uninstall Gandiva"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Gandiva"; Filename: "{app}\gandiva.exe"; IconFilename: "{app}\gandiva.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\gandiva.exe"; Description: "Launch Gandiva"; Flags: nowait postinstall skipifsilent
