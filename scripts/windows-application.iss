; Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
; Actual shared application payload. Public delivery requires signing/release gates.
[Setup]
AppId={#ApplicationId}
AppName=Augmentor Agent
AppVerName=Augmentor Agent
AppVersion={#ProductVersion}
AppPublisher=Augmentor
AppPublisherURL=https://augmentoragent.com
DefaultDirName={#InstallDirectory}
UsePreviousAppDir=no
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir={#OutputDirectory}
OutputBaseFilename=Augmentor-{#ProductVersion}-windows-{#TargetArchitecture}-candidate
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed={#AllowedArchitecture}
ArchitecturesInstallIn64BitMode={#AllowedArchitecture}
MinVersion={#MinimumVersion}
UninstallDisplayIcon={app}\current\Augmentor.exe
CloseApplications=no
RestartApplications=no
Compression=lzma2/fast
SolidCompression=yes
DiskSpanning=no

[Files]
Source: "{#HandoffHelper}"; Flags: dontcopy
Source: "{#HandoffHelper}"; DestDir: "{app}\maintenance"; Flags: ignoreversion
Source: "{#PayloadDirectory}\*"; DestDir: "{app}\current"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#ShortcutName}"; Filename: "{app}\current\Augmentor.exe"; Parameters: "{code:LaunchParameters}"; AppUserModelID: "com.augmentor.Agent"

[Code]
var MaintenanceHeld, AuthenticatedHandoff, RemovalHeld: Boolean;

function LaunchParameters(Param: String): String;
begin
  { Construct command quoting here, after both compiler command-line parsing
    and section-value parsing. Physical paths never contain quote characters. }
  Result := '';
  if '{#QualificationBase}' <> '' then
    Result := '--qualification-root "{#QualificationBase}"';
end;

function PrepareAuthenticatedHandoff(Pipe: String; Coordinator: Cardinal; Qualification: String): BOOL;
  external 'AugmentorHandoffPrepare@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function AcquireAuthenticatedInstallation(Timeout: Cardinal): BOOL;
  external 'AugmentorHandoffExclusive@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function PrepareManualMaintenance(Qualification: String): BOOL;
  external 'AugmentorMaintenancePrepare@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function ValidateApplicationPath(Directory: String): BOOL;
  external 'AugmentorMaintenancePath@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
procedure CloseSetupMaintenance;
  external 'AugmentorHandoffClose@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function PrepareRemoval(Qualification: String): BOOL;
  external 'AugmentorMaintenancePrepare@{tmp}\augmentor-removal.dll stdcall delayload uninstallonly';
procedure CloseRemoval;
  external 'AugmentorHandoffClose@{tmp}\augmentor-removal.dll stdcall delayload uninstallonly';
function ValidateRemovalPath(Directory: String): BOOL;
  external 'AugmentorMaintenancePath@{tmp}\augmentor-removal.dll stdcall delayload uninstallonly';

function InitializeSetup: Boolean;
var Pipe, CoordinatorText: String; Coordinator: Int64;
begin
  Result := False;
  Pipe := ExpandConstant('{param:augmentorpipe|}');
  CoordinatorText := ExpandConstant('{param:augmentorcoordinator|}');
  if (Pipe <> '') or (CoordinatorText <> '') then begin
    if Pipe = '' then exit;
    Coordinator := StrToInt64Def(CoordinatorText, -1);
    if (Coordinator < 1) or (Coordinator > 4294967295) then exit;
    AuthenticatedHandoff := PrepareAuthenticatedHandoff(Pipe, Cardinal(Coordinator), '{#HandoffRuntime}');
    Result := AuthenticatedHandoff;
  end else
    Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var CurrentRelease: String; AccessReady: Boolean;
begin
  Result := '';
  if CompareText(ExpandFileName(WizardDirValue), ExpandFileName(ExpandConstant('{#InstallDirectory}'))) <> 0 then begin
    Result := 'This installer uses the single Augmentor application folder. Custom replacement paths are not supported.';
    exit;
  end;
  if not MaintenanceHeld then begin
    if AuthenticatedHandoff then
      AccessReady := AcquireAuthenticatedInstallation(30000)
    else
      AccessReady := PrepareManualMaintenance('{#QualificationBase}');
    if not AccessReady then begin
      Result := 'Augmentor is still running. Finish your work and quit Augmentor before installing or repairing it.';
      exit;
    end;
    MaintenanceHeld := True;
  end;
  AccessReady := ValidateApplicationPath(ExpandConstant('{app}'));
  if not AccessReady then begin
    Result := 'The application folder contains a redirected or unsupported path. It was preserved; recovery is required.';
    exit;
  end;
  { Same-build manual repair is allowed. Cross-version application needs the
    coordinated transaction and retained recovery artifact; never guess from
    a version string or overwrite an unidentified partial/foreign directory. }
  CurrentRelease := ExpandConstant('{app}\current\release.json');
  if not AuthenticatedHandoff and DirExists(ExpandConstant('{app}\current')) then begin
    if not FileExists(CurrentRelease) then begin
      Result := 'This application folder cannot be identified. Its files were preserved; recovery is required.';
      exit;
    end;
    if GetSHA256OfFile(CurrentRelease) <> '{#ReleaseDigest}' then
      Result := 'A different Augmentor build is installed. Use the coordinated update in Augmentor.';
  end;
end;

procedure DeinitializeSetup;
begin
  if MaintenanceHeld or AuthenticatedHandoff then begin
    CloseSetupMaintenance;
    MaintenanceHeld := False;
    AuthenticatedHandoff := False;
  end;
end;

function InitializeUninstall: Boolean;
begin
  { Load a temporary copy, so the installed helper can be removed while its
    independent copy retains both gates through the complete uninstall. }
  Result := FileCopy(ExpandConstant('{app}\maintenance\augmentor-installer-handoff.dll'),
    ExpandConstant('{tmp}\augmentor-removal.dll'), True);
  if not Result then exit;
  Result := GetSHA256OfFile(ExpandConstant('{tmp}\augmentor-removal.dll')) = '{#HelperDigest}';
  if not Result then exit;
  RemovalHeld := PrepareRemoval('{#QualificationBase}');
  Result := RemovalHeld;
  if Result then Result := ValidateRemovalPath(ExpandConstant('{app}'));
  if not Result then begin
    Log('Running Augmentor prevented removal; no application files were changed.');
    if not UninstallSilent then
      MsgBox('Augmentor is still running. Finish your work and quit Augmentor before removing it.', mbInformation, MB_OK);
  end;
end;

procedure DeinitializeUninstall;
begin
  if RemovalHeld then begin
    CloseRemoval;
    RemovalHeld := False;
  end;
  UnloadDLL(ExpandConstant('{tmp}\augmentor-removal.dll'));
end;
