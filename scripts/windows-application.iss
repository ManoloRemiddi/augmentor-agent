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

[Tasks]
Name: startup; Description: "Start Augmentor in the background when I sign in"; Flags: checkedonce; Check: OfferStartupTask

[Code]
var MaintenanceHeld, AuthenticatedHandoff, RemovalHeld, FreshInstallation: Boolean;
  StartupChoiceKnown, StartupChoice: Boolean;
  BrowserCleanupReady: Boolean; BrowserDigest: String;

function OfferStartupTask: Boolean;
begin
  if not StartupChoiceKnown then begin
    StartupChoice := not DirExists(ExpandConstant('{#InstallDirectory}\current'));
    StartupChoiceKnown := True;
  end;
  Result := StartupChoice;
end;

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
function OwnedRegistry(Key, Name, Expected: String; Action: Cardinal): Cardinal;
  external 'AugmentorOwnedRegistry@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function RemoveOwnedRegistry(Key, Name, Expected: String; Action: Cardinal): Cardinal;
  external 'AugmentorOwnedRegistry@{tmp}\augmentor-removal.dll stdcall delayload uninstallonly';
function RetainBrowserManifest(Path: String): BOOL;
  external 'AugmentorRetainManifest@{tmp}\augmentor-removal.dll stdcall delayload uninstallonly';

function BrowserKey(Index: Integer): String;
begin
  case Index of
    0: Result := '{#BrowserChromeKey}';
    1: Result := '{#BrowserChromiumKey}';
    2: Result := '{#BrowserEdgeKey}';
  end;
end;

function PrepareBrowserCleanup: Boolean;
var Index: Integer; State: Cardinal; HasOwnedRegistration, Pinned: Boolean;
begin
  Result := True;
  if (RemoveOwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{app}\current'), 0) <> 2) or
      (RemoveOwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 0) <> 2) then exit;
  HasOwnedRegistration := False;
  for Index := 0 to 2 do begin
    State := RemoveOwnedRegistry(BrowserKey(Index), '', ExpandConstant('{#BrowserManifestPath}'), 0);
    if State = 0 then begin Log('Browser removal registry inspection failed.'); Result := False; exit; end;
    if State = 2 then HasOwnedRegistration := True;
  end;
  if not HasOwnedRegistration then exit;
  Result := False;
  Pinned := RetainBrowserManifest(ExpandConstant('{#BrowserManifestPath}'));
  if not Pinned then begin Log('Browser removal could not retain the private manifest.'); exit; end;
  BrowserDigest := GetSHA256OfFile(ExpandConstant('{#BrowserManifestPath}'));
  if RemoveOwnedRegistry('{#InstallationKey}', 'BrowserManifestSHA256', BrowserDigest, 0) <> 2 then begin
    Log('Browser removal manifest digest does not match the ownership receipt.');
    exit;
  end;
  BrowserCleanupReady := True;
  Result := True;
end;

function StartupCommand: String;
var Arguments: String;
begin
  Arguments := LaunchParameters('');
  if Arguments <> '' then Arguments := Arguments + ' ';
  Result := '"' + ExpandConstant('{app}\current\Augmentor.exe') + '" ' + Arguments + '--background';
end;

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
var CurrentRelease: String; AccessReady: Boolean; Registration: Cardinal;
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
  FreshInstallation := not DirExists(ExpandConstant('{app}\current'));
  if not AuthenticatedHandoff and DirExists(ExpandConstant('{app}\current')) then begin
    if not FileExists(CurrentRelease) then begin
      Result := 'This application folder cannot be identified. Its files were preserved; recovery is required.';
      exit;
    end;
    if GetSHA256OfFile(CurrentRelease) <> '{#ReleaseDigest}' then
      Result := 'A different Augmentor build is installed. Use the coordinated update in Augmentor.';
  end;
  if Result <> '' then exit;
  Registration := OwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{app}\current'), 0);
  if (Registration <> 1) and (Registration <> 2) then begin
    Result := 'Another Augmentor installation owns the browser setup registration. Its registration was preserved.';
    exit;
  end;
  Registration := OwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 0);
  if (Registration <> 1) and (Registration <> 2) then begin
    Result := 'The existing Augmentor application identity is unfamiliar. Its registration was preserved.';
    exit;
  end;
  if FreshInstallation and WizardIsTaskSelected('startup') then begin
    if ('{#QualificationBase}' = '') and (Length(StartupCommand) > 260) then begin
      Result := 'This installation path is too long for Windows login startup. Disable the startup task to continue.';
      exit;
    end;
    Registration := OwnedRegistry('{#StartupKey}', 'Augmentor Agent', StartupCommand, 0);
    if (Registration <> 1) and (Registration <> 2) then
      Result := 'An existing login entry uses the Augmentor name. Disable the startup task to preserve it and continue.';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep <> ssPostInstall then exit;
  if OwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{app}\current'), 1) <> 2 then
    RaiseException('Augmentor could not record its installed location. Repair this installation.');
  if OwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 1) <> 2 then
    RaiseException('Augmentor could not record its application identity. Repair this installation.');
  { Only initial installation chooses a default. Repair/update do not recreate
    an entry removed by the user or alter Windows StartupApproved state. }
  if FreshInstallation and WizardIsTaskSelected('startup') then
    if OwnedRegistry('{#StartupKey}', 'Augmentor Agent', StartupCommand, 1) <> 2 then
      RaiseException('Augmentor could not enable login startup. The existing entry was preserved.');
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
  if not Result then Log('Removal could not acquire idle maintenance access.');
  if Result then begin
    Result := ValidateRemovalPath(ExpandConstant('{app}'));
    if not Result then Log('Removal application-tree validation failed.');
  end;
  if Result then Result := PrepareBrowserCleanup;
  if not Result then begin
    Log('Active work or changed installation/browser registration prevented removal; no application files were changed.');
    if not UninstallSilent then
      MsgBox('Augmentor cannot be removed while it is running or its browser registration has changed. Finish your work and quit Augmentor. Repair browser setup if its registration was edited.', mbInformation, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Outcome: Cardinal; Index: Integer;
begin
  if CurUninstallStep <> usUninstall then exit;
  { Cancellation before the actual removal step must leave startup intact.
    Delete only exact owned values; never delete keys or unrelated entries. }
  if BrowserCleanupReady then begin
    for Index := 0 to 2 do begin
      Outcome := RemoveOwnedRegistry(BrowserKey(Index), '', ExpandConstant('{#BrowserManifestPath}'), 2);
      if Outcome = 0 then RaiseException('Augmentor could not remove an owned browser registration.');
    end;
    if RemoveOwnedRegistry('{#InstallationKey}', 'BrowserManifestSHA256', BrowserDigest, 2) <> 2 then
      RaiseException('The browser ownership record changed during removal.');
  end;
  Outcome := RemoveOwnedRegistry('{#StartupKey}', 'Augmentor Agent', StartupCommand, 2);
  if Outcome = 0 then RaiseException('Augmentor could not remove its owned login entry.');
  if (RemoveOwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{app}\current'), 0) = 2) and
      (RemoveOwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 0) = 2) then begin
    if RemoveOwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{app}\current'), 2) <> 2 then
      RaiseException('Augmentor could not remove its owned location registration.');
    if RemoveOwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 2) <> 2 then
      RaiseException('Augmentor could not remove its owned application identity.');
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
