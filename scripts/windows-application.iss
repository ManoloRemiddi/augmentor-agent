; Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
; Shared payload. Unsigned public preview is an explicit distribution profile.
#ifndef PackageSuffix
  #define PackageSuffix "candidate"
#endif
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
OutputBaseFilename=Augmentor-{#ProductVersion}-windows-{#TargetArchitecture}-{#PackageSuffix}
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed={#AllowedArchitecture}
ArchitecturesInstallIn64BitMode={#AllowedArchitecture}
MinVersion={#MinimumVersion}
UninstallDisplayIcon={app}\current\Augmentor.exe
AppModifyPath={code:RetainedInstallerCommand}
CloseApplications=no
RestartApplications=no
Compression=lzma2/fast
SolidCompression=yes
DiskSpanning=no

[Files]
Source: "{#HandoffHelper}"; Flags: dontcopy
Source: "{#HandoffHelper}"; DestDir: "{app}\maintenance"; Flags: ignoreversion
; Keep inspection metadata/code and its existing Python first, in extraction
; order. Solid decompression need not traverse DSH/Node/PowerShell to inspect.
Source: "{#PayloadDirectory}\release.json"; DestDir: "{app}\current"; Flags: ignoreversion
Source: "{#PayloadDirectory}\payload-integrity.json"; DestDir: "{app}\current"; Flags: ignoreversion
Source: "{#PayloadDirectory}\scripts\windows-inspect-payload.py"; DestDir: "{app}\current\scripts"; Flags: ignoreversion
Source: "{#PayloadDirectory}\scripts\windows-recover-source.py"; DestDir: "{app}\current\scripts"; Flags: ignoreversion
Source: "{#PayloadDirectory}\services\lifecycle\*.py"; DestDir: "{app}\current\services\lifecycle"; Flags: ignoreversion
Source: "{#PayloadDirectory}\services\platform_adapters\*.py"; DestDir: "{app}\current\services\platform_adapters"; Flags: ignoreversion
Source: "{#PayloadDirectory}\python\*"; DestDir: "{app}\current\python"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#PayloadDirectory}\*"; DestDir: "{app}\current"; Excludes: "\release.json,\payload-integrity.json,\scripts\windows-inspect-payload.py,\scripts\windows-recover-source.py,\services\lifecycle\*.py,\services\platform_adapters\*.py,\python\*"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#ShortcutName}"; Filename: "{app}\current\Augmentor.exe"; Parameters: "{code:LaunchParameters}"; AppUserModelID: "com.augmentor.Agent"

[Tasks]
Name: startup; Description: "Start Augmentor in the background when I sign in"; Flags: checkedonce; Check: OfferStartupTask

[Run]
Filename: "{app}\current\Augmentor.exe"; Parameters: "{code:LaunchParameters}"; Description: "Open Augmentor"; Flags: postinstall nowait skipifsilent; Check: OfferLaunch; BeforeInstall: ReleaseForLaunch

[Code]
var MaintenanceHeld, AuthenticatedHandoff, RemovalHeld, FreshInstallation: Boolean;
  StartupChoiceKnown, StartupChoice: Boolean;
  BrowserCleanupReady, InstallationComplete, InstallerRetained: Boolean; BrowserDigest: String;
  RetainedInstallerDigest: String;
  RestoreSource, SourceAssessmentReady, SourceAssessmentAttempted: Boolean;

function OfferStartupTask: Boolean;
begin
  if not StartupChoiceKnown then begin
    StartupChoice := not DirExists(ExpandConstant('{#InstallDirectory}\current'));
    StartupChoiceKnown := True;
  end;
  Result := StartupChoice and not RestoreSource;
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
function RetainInstaller(SourcePath, InstallerDigest, ReleaseDigest: String): BOOL;
  external 'AugmentorRetainInstaller@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function SelectInstaller: BOOL;
  external 'AugmentorSelectInstaller@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function MatchesSelectedInstaller: BOOL;
  external 'AugmentorMatchesSelectedInstaller@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function ManualUpdateClear: BOOL;
  external 'AugmentorManualUpdateClear@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function RemovalUpdateClear: BOOL;
  external 'AugmentorManualUpdateClear@{tmp}\augmentor-removal.dll stdcall delayload uninstallonly';
function PrepareInspection(Temporary: String): BOOL;
  external 'AugmentorInspectionPrepare@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function RunInspection(Installed, ReleaseDigest: String): BOOL;
  external 'AugmentorInspectionRun@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function InspectionStage: Cardinal;
  external 'AugmentorInspectionStage@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function InspectionDetail: Cardinal;
  external 'AugmentorInspectionDetail@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function SnapshotUpdate(InstallerDigest: String): BOOL;
  external 'AugmentorInspectionSnapshot@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function InspectHealth(Installed, ReleaseDigest, Qualification: String): BOOL;
  external 'AugmentorInspectionHealth@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function PrepareReplacement(Application: String): BOOL;
  external 'AugmentorPrepareReplacement@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function PrepareSourceRestoration(Application: String): BOOL;
  external 'AugmentorPrepareSourceRestoration@files:augmentor-installer-handoff.dll stdcall delayload setuponly';

function ObserveSourceRecovery(Installed, ReleaseDigest, HelperDigest, InstallationKey, ApplicationId, Qualification: String): BOOL;
  external 'AugmentorRecoveryObserve@files:augmentor-installer-handoff.dll stdcall delayload setuponly';

function PrepareIndependentAssessment(AssessSource: Boolean): Boolean;
var Ready: Boolean; ReportText: AnsiString;
begin
  Result := False;
  { Keep successful admission/pins until Setup closes. Read-only callers close
    in their own finally block; explicit source restoration retains them. }
  Ready := PrepareManualMaintenance('{#QualificationBase}');
  if not Ready then begin Log('Augmentor independent inspection: maintenance unavailable.'); exit; end;
  MaintenanceHeld := True;
  Ready := ValidateApplicationPath(ExpandConstant('{#InstallDirectory}'));
  if not Ready then begin Log('Augmentor independent inspection: unsupported application path.'); exit; end;
  if (OwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{#InstallDirectory}\current'), 0) <> 2) or
     (OwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 0) <> 2) then begin
    Log('Augmentor independent inspection: application ownership is unknown.'); exit;
  end;
  Ready := PrepareInspection(ExpandConstant('{tmp}'));
  if not Ready then begin Log('Augmentor independent inspection: scratch creation failed.'); exit; end;
  if AssessSource then begin
    Ready := SnapshotUpdate(Lowercase(GetSHA256OfFile(ExpandConstant('{srcexe}'))));
    if not Ready then begin Log('Augmentor independent inspection: exclusive private update snapshot unavailable.'); exit; end;
  end;
  ExtractTemporaryFiles('{app}\current\release.json');
  ExtractTemporaryFiles('{app}\current\payload-integrity.json');
  ExtractTemporaryFiles('{app}\current\scripts\windows-inspect-payload.py');
  ExtractTemporaryFiles('{app}\current\services\lifecycle\*.py');
  ExtractTemporaryFiles('{app}\current\services\platform_adapters\*.py');
  ExtractTemporaryFiles('{app}\current\python\*');
  Ready := RunInspection(ExpandConstant('{#InstallDirectory}\current'), '{#ReleaseDigest}');
  if not Ready then begin
    Log('Augmentor independent inspection: worker failed; stage=' + IntToStr(InspectionStage) +
      ', detail=' + IntToStr(InspectionDetail) + '; installation preserved.'); exit;
  end;
  if not LoadStringFromFile(ExpandConstant('{tmp}\') + '{app}\inspection-result.json', ReportText) then
    RaiseException('Augmentor independent inspection result is unavailable.');
  Log('Augmentor independent inspection result: ' + String(ReportText));
  Result := True;
end;

procedure InspectIndependentPayload(AssessSource, ObserveHealth: Boolean);
var Ready: Boolean; ReportText: AnsiString;
begin
  { Returning False from InitializeSetup prevents all installation sections. }
  try
    if not PrepareIndependentAssessment(AssessSource) then exit;
    if ObserveHealth then begin
      Ready := InspectHealth(ExpandConstant('{#InstallDirectory}\current'), '{#ReleaseDigest}', '{#QualificationBase}');
      if not Ready then begin
        Log('Augmentor independent health: worker failed; stage=' + IntToStr(InspectionStage) +
          ', detail=' + IntToStr(InspectionDetail) + '; update record preserved.'); exit;
      end;
      if not LoadStringFromFile(ExpandConstant('{tmp}\') + '{app}\health-result.json', ReportText) then
        RaiseException('Augmentor independent health result is unavailable.');
      Log('Augmentor independent health result: ' + String(ReportText));
    end;
  finally
    CloseSetupMaintenance;
    MaintenanceHeld := False;
  end;
end;

procedure RecoverPreviousSource;
var Ready: Boolean; ReportText: AnsiString; Digest: String;
begin
  try
    if not PrepareIndependentAssessment(True) then exit;
    Digest := Lowercase(GetSHA256OfFile(ExpandConstant('{srcexe}')));
    Ready := RetainInstaller(ExpandConstant('{srcexe}'), Digest, '{#ReleaseDigest}');
    if not Ready then begin Log('Augmentor recovery: exact source retention failed.'); exit; end;
    ExtractTemporaryFiles('{app}\current\scripts\windows-recover-source.py');
    Ready := ObserveSourceRecovery(ExpandConstant('{#InstallDirectory}\current'), '{#ReleaseDigest}',
      '{#HelperDigest}', '{#InstallationKey}', '{#ApplicationId}', '{#QualificationBase}');
    if not Ready then begin
      Log('Augmentor recovery: observer failed; stage=' + IntToStr(InspectionStage) +
        ', detail=' + IntToStr(InspectionDetail) + '; recovery records preserved.');
      if LoadStringFromFile(ExpandConstant('{tmp}\') + '{app}\recovery-error.json', ReportText) then
        Log('Augmentor recovery diagnostics: ' + String(ReportText));
      exit;
    end;
    if not LoadStringFromFile(ExpandConstant('{tmp}\') + '{app}\recovery-result.json', ReportText) then
      RaiseException('Augmentor recovery result is unavailable. Inspect its durable recovery record.');
    Log('Augmentor recovery result: ' + String(ReportText));
  finally
    CloseSetupMaintenance;
    MaintenanceHeld := False;
  end;
end;

function RetainedInstallerCommand(Param: String): String;
begin
  { Windows can run repair with the installed Python/Qt/launcher missing.
    Register only the source already retained and pinned by this installation. }
  if not InstallerRetained or (Length(RetainedInstallerDigest) <> 64) then
    RaiseException('Augmentor has no verified repair installer.');
  { Quote after directive parsing, which strips a surrounding quote pair. }
  Result := '"' + ExpandConstant('{#RecoveryDirectory}') + '\' + RetainedInstallerDigest + '.exe"';
end;

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

function OfferLaunch: Boolean;
begin
  { Coordinated updates reopen only after independent health verification. }
  Result := not AuthenticatedHandoff and not RestoreSource;
end;

procedure ReleaseForLaunch;
begin
  { Inno runs this only after successful file/registration installation, when
    the user accepts the final Open checkbox. Release admission before the
    native app acquires its own startup/lifetime handles. An unchecked box or
    silent/coordinated install keeps the normal DeinitializeSetup cleanup. }
  if not InstallationComplete or not MaintenanceHeld or AuthenticatedHandoff or RestoreSource or WizardSilent then
    RaiseException('Augmentor cannot open before installation is complete.');
  CloseSetupMaintenance;
  MaintenanceHeld := False;
end;

function InitializeSetup: Boolean;
var Pipe, CoordinatorText, Inspection, Recovery: String; Coordinator: Int64;
begin
  Result := False;
  Pipe := ExpandConstant('{param:augmentorpipe|}');
  CoordinatorText := ExpandConstant('{param:augmentorcoordinator|}');
  Inspection := ExpandConstant('{param:augmentorinspect|}');
  Recovery := ExpandConstant('{param:augmentorrecover|}');
  if Recovery <> '' then begin
    if (Inspection <> '') or (Pipe <> '') or (CoordinatorText <> '') then exit;
    if Recovery = 'previous' then begin RecoverPreviousSource; exit; end;
    if Recovery <> 'source' then exit;
    RestoreSource := True;
    Result := True;
    exit;
  end;
  if Inspection <> '' then begin
    if ((Inspection <> '1') and (Inspection <> 'source') and (Inspection <> 'health')) or
        (Pipe <> '') or (CoordinatorText <> '') then exit;
    InspectIndependentPayload(Inspection <> '1', Inspection = 'health');
    exit;
  end;
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
var CurrentRelease: String; AccessReady, NeedsSelectedRepair, OwnedInstallation: Boolean;
  RootRegistration, IdentityRegistration, Registration: Cardinal;
begin
  Result := '';
  if CompareText(ExpandFileName(WizardDirValue), ExpandFileName(ExpandConstant('{#InstallDirectory}'))) <> 0 then begin
    Result := 'This installer uses the single Augmentor application folder. Custom replacement paths are not supported.';
    exit;
  end;
  if RestoreSource and not SourceAssessmentReady then begin
    if SourceAssessmentAttempted then begin
      Result := 'Source assessment failed. Close this installer before another recovery attempt.';
      exit;
    end;
    SourceAssessmentAttempted := True;
    SourceAssessmentReady := PrepareIndependentAssessment(True);
    if not SourceAssessmentReady then begin
      Result := 'This installer could not verify the exact previous Augmentor version. Your installation and update record were preserved.';
      exit;
    end;
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
  if not AuthenticatedHandoff and not RestoreSource then begin
    AccessReady := ManualUpdateClear;
    if not AccessReady then begin
      Result := 'An unfinished Augmentor update needs recovery before installation or repair can continue. Its records and your data were preserved.';
      exit;
    end;
  end;
  AccessReady := ValidateApplicationPath(ExpandConstant('{app}'));
  if not AccessReady then begin
    Result := 'The application folder contains a redirected or unsupported path. It was preserved; recovery is required.';
    exit;
  end;
  { The independent selected-source receipt can identify an owned damaged
    installation even when its replaceable release.json is missing. }
  CurrentRelease := ExpandConstant('{app}\current\release.json');
  RootRegistration := OwnedRegistry('{#InstallationKey}', 'Root', ExpandConstant('{app}\current'), 0);
  if (RootRegistration <> 1) and (RootRegistration <> 2) then begin
    Result := 'Another Augmentor installation owns the browser setup registration. Its registration was preserved.';
    exit;
  end;
  IdentityRegistration := OwnedRegistry('{#InstallationKey}', 'AppId', 'com.augmentor.Agent', 0);
  if (IdentityRegistration <> 1) and (IdentityRegistration <> 2) then begin
    Result := 'The existing Augmentor application identity is unfamiliar. Its registration was preserved.';
    exit;
  end;
  OwnedInstallation := (RootRegistration = 2) and (IdentityRegistration = 2);
  if (AuthenticatedHandoff or RestoreSource) and not OwnedInstallation then begin
    Result := 'A coordinated update requires the registered Augmentor installation. Its files were preserved.';
    exit;
  end;
  FreshInstallation := not DirExists(ExpandConstant('{app}\current')) and
    (RootRegistration = 1) and (IdentityRegistration = 1);
  NeedsSelectedRepair := False;
  if not AuthenticatedHandoff and not RestoreSource and not FreshInstallation then begin
    NeedsSelectedRepair := True;
    if FileExists(CurrentRelease) then
      NeedsSelectedRepair := GetSHA256OfFile(CurrentRelease) <> '{#ReleaseDigest}';
    if NeedsSelectedRepair and not OwnedInstallation then begin
      Result := 'This application folder cannot be identified. Its files were preserved; recovery is required.';
      exit;
    end;
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
  if Result <> '' then exit;
  if not InstallerRetained then begin
    RetainedInstallerDigest := Lowercase(GetSHA256OfFile(ExpandConstant('{srcexe}')));
    InstallerRetained := RetainInstaller(ExpandConstant('{srcexe}'),
      RetainedInstallerDigest, '{#ReleaseDigest}');
    if not InstallerRetained then
      Result := 'Augmentor could not save its recovery copy. Check free disk space and try again. If this continues, contact support. Your installed app was not changed.';
  end;
  if (Result = '') and NeedsSelectedRepair then begin
    AccessReady := MatchesSelectedInstaller;
    if not AccessReady then
      Result := 'This installer does not match the recorded Augmentor installation. Use its registered repair option or the coordinated update in Augmentor. Your installed app was not changed.';
  end;
  if (Result = '') and (AuthenticatedHandoff or RestoreSource) then begin
    if RestoreSource then
      AccessReady := PrepareSourceRestoration(ExpandConstant('{app}'))
    else
      AccessReady := PrepareReplacement(ExpandConstant('{app}'));
    if not AccessReady then
      Result := 'Augmentor could not prepare a clean replacement. The update remains unresolved and its recovery files were preserved. Close this installer before trying recovery.';
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
  if not SelectInstaller then
    RaiseException('Augmentor could not record its installed build. Repair this installation.');
  InstallationComplete := True;
  if RestoreSource then
    Log('Augmentor previous-source files installed; recovery verification and journal completion remain required.');
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
    Result := RemovalUpdateClear;
    if not Result then begin
      Log('An unresolved update prevented removal.');
      if not UninstallSilent then
        MsgBox('An unfinished Augmentor update needs recovery before removal can continue. Its records and your data were preserved.', mbInformation, MB_OK);
      exit;
    end;
  end;
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
