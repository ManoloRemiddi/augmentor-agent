; Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
; Disposable qualification package; never used for customer distribution.
; Definitions are supplied by windows-inno-proof.py, with unique fixture IDs.
[Setup]
AppId={#FixtureId}
AppName={#FixtureId}
AppVersion={#FixtureVersion}
AppPublisher=Augmentor qualification
DefaultDirName={#InstallDirectory}
OutputDir={#OutputDirectory}
OutputBaseFilename=fixture-{#FixtureVersion}
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed={#AllowedArchitecture}
ArchitecturesInstallIn64BitMode={#AllowedArchitecture}
DisableDirPage=yes
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\AugmentorFixture.exe
CloseApplications=no
RestartApplications=no
Compression=lzma2/fast
SolidCompression=yes

[Files]
Source: "{#HandoffHelper}"; Flags: dontcopy
Source: "{#PayloadDirectory}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#FixtureId}"; Filename: "{app}\AugmentorFixture.exe"

[Code]
var GateHandle, StartupHandle: THandle; AuthenticatedHandoff: Boolean;

function PrepareAuthenticatedHandoff(Pipe: String; Coordinator: Cardinal; Qualification: String): BOOL;
  external 'AugmentorHandoffPrepare@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
procedure CloseAuthenticatedHandoff;
  external 'AugmentorHandoffClose@files:augmentor-installer-handoff.dll stdcall delayload setuponly';
function AcquireAuthenticatedInstallation(Timeout: Cardinal): BOOL;
  external 'AugmentorHandoffExclusive@files:augmentor-installer-handoff.dll stdcall delayload setuponly';

function OpenGateFile(Name: String; Access, Sharing: Cardinal;
  Security: NativeInt; Creation, Attributes: Cardinal; Template: THandle): THandle;
  external 'CreateFileW@kernel32.dll stdcall';
function CloseGateFile(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';
function OpenSourceProcess(Access: Cardinal; Inherit: Boolean; Pid: Cardinal): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function CurrentProcess: THandle;
  external 'GetCurrentProcess@kernel32.dll stdcall';
function CurrentProcessId: Cardinal;
  external 'GetCurrentProcessId@kernel32.dll stdcall';
function DuplicateGate(SourceProcess, SourceHandle, TargetProcess: THandle;
  var TargetHandle: THandle; Access: Cardinal; Inherit: Boolean; Options: Cardinal): Boolean;
  external 'DuplicateHandle@kernel32.dll stdcall';

function InitializeSetup: Boolean;
var SourcePid: Int64; SourceHandle, SourceProcess: THandle; Count: Integer;
  SourceText, HandleText: String;
begin
  { Disposable transfer proof only. Production still needs authenticated
    coordinator/installer identity, artifact trust and transaction recovery.
    Duplicate in the actual Setup process; do not assume its loader inherited
    an incoming kernel handle through its extraction/bootstrap subprocess. }
  Result := True;
  SourceText := ExpandConstant('{param:augmentorpipe|}');
  if SourceText <> '' then begin
    Result := False;
    SourcePid := StrToInt64Def(ExpandConstant('{param:augmentorcoordinator|}'), -1);
    if (SourcePid < 1) or (SourcePid > 4294967295) then exit;
    Result := PrepareAuthenticatedHandoff(SourceText, Cardinal(SourcePid), '{#HandoffRuntime}');
    if not Result then exit;
    AuthenticatedHandoff := True;
    Result := SaveStringToFile('{#HandoffReady}', '{"pid":' + IntToStr(CurrentProcessId) + '}', False);
    if not Result then exit;
    for Count := 1 to 1000 do begin
      if FileExists('{#HandoffContinue}') then exit;
      Sleep(20);
    end;
    Result := False;
    exit;
  end;
  SourceText := ExpandConstant('{param:startupowner|}');
  HandleText := ExpandConstant('{param:startuphandle|}');
  if (SourceText = '') and (HandleText = '') then exit;
  Result := False;
  SourcePid := StrToInt64Def(SourceText, -1);
  if (SourcePid < 1) or (SourcePid > 4294967295) then exit;
  SourceHandle := THandle(StrToInt64Def(HandleText, 0));
  if SourceHandle = 0 then exit;
  SourceProcess := OpenSourceProcess($0040, False, Cardinal(SourcePid));
  if SourceProcess = 0 then exit;
  Result := DuplicateGate(SourceProcess, SourceHandle, CurrentProcess, StartupHandle, 0, False, 2);
  CloseGateFile(SourceProcess);
  if not Result then exit;
  Result := SaveStringToFile('{#HandoffReady}', '{"pid":' + IntToStr(CurrentProcessId) + '}', False);
  if not Result then exit;
  for Count := 1 to 1000 do begin
    if FileExists('{#HandoffContinue}') then exit;
    Sleep(20);
  end;
  Log('Disposable handoff was not released; aborting without file changes.');
  Result := False;
end;

function AcquireGate: Boolean;
begin
  if GateHandle <> 0 then begin Result := True; exit; end;
  { Exclusive file sharing holds admission through the entire transaction.
    A running fixture has an open shared handle. New fixtures cannot open this
    file while maintenance owns it. No PID guessing or forced termination. }
  GateHandle := OpenGateFile('{#GateFile}', $C0000000, 0, 0, 4, $80, 0);
  Result := GateHandle <> THandle(-1);
  if not Result then GateHandle := 0;
end;

procedure ReleaseGate;
begin
  if GateHandle <> 0 then begin
    CloseGateFile(GateHandle);
    GateHandle := 0;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var AccessReady: Boolean; AccessTimeout: Cardinal;
begin
  Result := '';
  if AuthenticatedHandoff then begin
    AccessTimeout := Cardinal(StrToIntDef(ExpandConstant('{param:finalleasetimeout|30000}'), 30000));
    AccessReady := AcquireAuthenticatedInstallation(AccessTimeout);
    if not AccessReady then begin
      Result := 'The update coordinator or an application process has not released installation access.';
      exit;
    end;
  end;
  if not AcquireGate then
    Result := 'Augmentor qualification has active work. Finish it before maintenance.'
  else if ExpandConstant('{param:failaftergate|0}') = '1' then
    Result := 'Deliberate qualification failure after acquiring admission.';
end;

procedure DeinitializeSetup;
begin
  ReleaseGate;
  if AuthenticatedHandoff then begin
    CloseAuthenticatedHandoff;
    AuthenticatedHandoff := False;
  end;
  if StartupHandle <> 0 then begin
    CloseGateFile(StartupHandle);
    StartupHandle := 0;
  end;
end;

function InitializeUninstall: Boolean;
begin
  Result := AcquireGate;
  if not Result then Log('Active work prevented removal before changing files.');
end;

procedure DeinitializeUninstall;
begin
  ReleaseGate;
end;
