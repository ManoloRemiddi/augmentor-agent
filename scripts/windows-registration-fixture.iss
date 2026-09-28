; Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
; Real x64 Setup/native-helper registry checks, including on ARM64 under emulation.
[Setup]
AppId={#FixtureId}
AppName=Augmentor registry qualification
AppVersion=0.0.1
DefaultDirName={#QualificationBase}\unused
OutputDir={#OutputDirectory}
OutputBaseFilename=registration-fixture
SetupArchitecture=x64
PrivilegesRequired=lowest
Uninstallable=no
CreateAppDir=no
DisableDirPage=yes
DisableProgramGroupPage=yes

[Files]
Source: "{#HandoffHelper}"; Flags: dontcopy

[Code]
function PrepareManual(Qualification: String): BOOL;
  external 'AugmentorMaintenancePrepare@files:augmentor-installer-handoff.dll stdcall delayload';
procedure CloseManual;
  external 'AugmentorHandoffClose@files:augmentor-installer-handoff.dll stdcall delayload';
function OwnedRegistry(Key, Name, Expected: String; Action: Cardinal): Cardinal;
  external 'AugmentorOwnedRegistry@files:augmentor-installer-handoff.dll stdcall delayload';
function RetainManifest(Path: String): BOOL;
  external 'AugmentorRetainManifest@files:augmentor-installer-handoff.dll stdcall delayload';
function ValidatePath(Path: String): BOOL;
  external 'AugmentorMaintenancePath@files:augmentor-installer-handoff.dll stdcall delayload';

procedure Require(Condition: Boolean; Detail: String);
begin
  if not Condition then RaiseException(Detail);
end;

function InitializeSetup: Boolean;
var Ready: Boolean; Expected, Actual: String; Number: Cardinal;
begin
  Result := False;
  Expected := '"{#QualificationBase}\installed café\Augmentor.exe" --background';
  Ready := PrepareManual('{#QualificationBase}');
  Require(Ready, 'Could not acquire disposable native maintenance.');
  Ready := ValidatePath('{#LongTree}');
  Require(Ready, 'Ordinary long payload paths must pass native inspection.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 0) = 1, 'Expected absent value.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 1) = 2, 'Could not create owned value.');
  Require(RegQueryStringValue(HKCU, '{#RegistryKey}', 'Augmentor Agent', Actual), 'Missing actual registry value.');
  Require(Actual = Expected, 'Registry command quoting changed.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 1) = 2, 'Repeated ownership check failed.');
  Require(RegWriteStringValue(HKCU, '{#RegistryKey}', 'Unrelated', 'preserve'), 'Could not create fixture unrelated value.');
  Require(RegWriteStringValue(HKCU, '{#RegistryKey}', 'Augmentor Agent', 'foreign'), 'Could not change fixture value.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 1) = 3, 'Foreign create must refuse.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 2) = 3, 'Foreign remove must refuse.');
  Require(RegQueryStringValue(HKCU, '{#RegistryKey}', 'Augmentor Agent', Actual), 'Foreign value disappeared.');
  Require(Actual = 'foreign', 'Foreign value changed.');
  Require(RegWriteDWordValue(HKCU, '{#RegistryKey}', 'Augmentor Agent', 23), 'Could not change fixture type.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 1) = 3, 'Wrong type create must refuse.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 2) = 3, 'Wrong type remove must refuse.');
  Require(RegQueryDWordValue(HKCU, '{#RegistryKey}', 'Augmentor Agent', Number), 'Wrong type was removed.');
  Require(Number = 23, 'Wrong type was changed.');
  Require(RegDeleteValue(HKCU, '{#RegistryKey}', 'Augmentor Agent'), 'Could not reset disposable value.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 1) = 2, 'Could not restore owned value.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 2) = 2, 'Could not remove owned value.');
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 2) = 1, 'Absent removal must be idempotent.');
  Require(RegQueryStringValue(HKCU, '{#RegistryKey}', 'Unrelated', Actual), 'Unrelated value disappeared.');
  Require(Actual = 'preserve', 'Unrelated value changed.');
  Require(OwnedRegistry('{#RegistryKey}', '', Expected, 0) = 1, 'Expected absent default value.');
  Require(OwnedRegistry('{#RegistryKey}', '', Expected, 1) = 2, 'Could not create default value.');
  Require(RegQueryStringValue(HKCU, '{#RegistryKey}', '', Actual), 'Missing actual default value.');
  Require(Actual = Expected, 'Default value changed.');
  Require(OwnedRegistry('{#RegistryKey}', '', 'foreign', 2) = 3, 'Foreign default removal must refuse.');
  Require(OwnedRegistry('{#RegistryKey}', '', Expected, 2) = 2, 'Could not remove owned default value.');
  Require(OwnedRegistry('{#RegistryKey}', '', Expected, 2) = 1, 'Absent default removal must be idempotent.');
  Ready := RetainManifest('{#ManifestPath}');
  Require(Ready, 'Could not retain the private browser manifest.');
  Require(GetSHA256OfFile('{#ManifestPath}') = '{#ManifestDigest}', 'Pinned manifest hash differs.');
  Require(not SaveStringToFile('{#ManifestPath}', 'overwrite', False), 'Pinned manifest allowed writes.');
  Require(not DeleteFile('{#ManifestPath}'), 'Pinned manifest allowed deletion.');
  CloseManual;
  Require(OwnedRegistry('{#RegistryKey}', 'Augmentor Agent', Expected, 1) = 0, 'Ungated mutation must refuse.');
  Result := True;
end;

procedure DeinitializeSetup;
begin
  CloseManual;
end;
