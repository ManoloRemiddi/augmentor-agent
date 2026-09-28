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
Source: "{#PayloadDirectory}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#FixtureId}"; Filename: "{app}\AugmentorFixture.exe"

[Code]
var GateHandle: THandle;

function OpenGateFile(Name: String; Access, Sharing: Cardinal;
  Security: NativeInt; Creation, Attributes: Cardinal; Template: THandle): THandle;
  external 'CreateFileW@kernel32.dll stdcall';
function CloseGateFile(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

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
begin
  Result := '';
  if not AcquireGate then
    Result := 'Augmentor qualification has active work. Finish it before maintenance.'
  else if ExpandConstant('{param:failaftergate|0}') = '1' then
    Result := 'Deliberate qualification failure after acquiring admission.';
end;

procedure DeinitializeSetup;
begin
  ReleaseGate;
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
