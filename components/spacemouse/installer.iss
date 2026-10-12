#ifndef Role
  #define Role "client"
#endif
#define AppVersion "0.2.0-beta.1"
#if Role == "server"
  #define RoleTitle "Server"
  #define DriverFile "usbipd-win_5.3.0_x64.msi"
  #define DriverUrl "https://github.com/dorssel/usbipd-win/releases/download/v5.3.0/usbipd-win_5.3.0_x64.msi"
  #define DriverHash "1c984914aec944de19b64eff232421439629699f8138e3ddc29301175bc6d938"
  #define DriverPath "usbipd-win\usbipd.exe"
#else
  #define RoleTitle "Client"
  #define DriverFile "USBip-0.9.8.1-x64.exe"
  #define DriverUrl "https://github.com/vadimgrn/usbip-win2/releases/download/v.0.9.8.1/USBip-0.9.8.1-x64.exe"
  #define DriverHash "38cad6d4432b52d5bb9409d9ad03b72fdffc4ada4cd3a48fbeca1a2752a8518a"
  #define DriverPath "USBip\usbip.exe"
#endif

[Setup]
AppId=SpaceMouseLink-{#Role}
AppName=SpaceMouse Link {#RoleTitle}
AppVersion={#AppVersion}
AppPublisher=softyoda
AppPublisherURL=https://github.com/softyoda/apollo-desktop-kit
DefaultDirName={autopf}\SpaceMouse Link\{#RoleTitle}
DefaultGroupName=SpaceMouse Link
OutputDir=release
OutputBaseFilename=SpaceMouseLink-{#RoleTitle}-{#AppVersion}-x64
SetupIconFile=assets\spacemouse.ico
UninstallDisplayIcon={app}\SpaceMouseLink.exe
LicenseFile=LICENSE
InfoBeforeFile=INSTALL-NOTES.txt
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter=SpaceMouseLink.exe
RestartApplications=no
DisableProgramGroupPage=yes
Uninstallable=yes

[Tasks]
Name: usbdriver; Description: "Install / configure the official USB prerequisite (optional)"; Flags: unchecked
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\SpaceMouseLink\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "Prepare-Device.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "Install-Driver.ps1"; Flags: dontcopy
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "licenses\*"; DestDir: "{app}\licenses"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\SpaceMouse Link {#RoleTitle}"; Filename: "{app}\SpaceMouseLink.exe"; Parameters: "--role {#Role}"
Name: "{autodesktop}\SpaceMouse Link {#RoleTitle}"; Filename: "{app}\SpaceMouseLink.exe"; Parameters: "--role {#Role}"; Tasks: desktopicon
Name: "{group}\Uninstall SpaceMouse Link {#RoleTitle}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\SpaceMouseLink.exe"; Parameters: "--role {#Role}"; Description: "Open SpaceMouse Link {#RoleTitle}"; Flags: postinstall nowait skipifsilent runasoriginaluser

[UninstallDelete]
Type: files; Name: "{localappdata}\SpaceMouseLink\{#Role}\identity.dpapi"
Type: files; Name: "{localappdata}\SpaceMouseLink\{#Role}\identity.dpapi.tmp"
Type: files; Name: "{localappdata}\SpaceMouseLink\{#Role}\latency.json"
Type: dirifempty; Name: "{localappdata}\SpaceMouseLink\{#Role}"

[Code]
var PrerequisiteInstalled: Boolean;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Driver, Args: String; Code: Integer; AlreadyInstalled: Boolean;
begin
  Result := '';
  if PrerequisiteInstalled or not WizardIsTaskSelected('usbdriver') then exit;
  AlreadyInstalled := FileExists(ExpandConstant('{autopf}\{#DriverPath}'));
  try
    WizardForm.PreparingLabel.Caption := 'Downloading and verifying the optional USB prerequisite...';
    DownloadTemporaryFile('{#DriverUrl}', '{#DriverFile}', '{#DriverHash}', nil);
    ExtractTemporaryFile('Install-Driver.ps1');
    Driver := ExpandConstant('{tmp}\{#DriverFile}');
    Args := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\Install-Driver.ps1') + '" -Role {#Role} -InstallerPath "' + Driver + '"';
    WizardForm.PreparingLabel.Caption := 'Preparing the signed USB prerequisite. This may take a minute...';
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Args, '', SW_HIDE, ewWaitUntilTerminated, Code) or (Code <> 0) then
      Result := 'USB prerequisite failed. Check the network, administrator permissions and Windows Firewall, then retry.'
    else begin
      PrerequisiteInstalled := True;
      if ('{#Role}' = 'client') and not AlreadyInstalled then NeedsRestart := True;
    end;
  except
    Result := GetExceptionMessage;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'SpaceMouseLink-{#Role}');
end;
