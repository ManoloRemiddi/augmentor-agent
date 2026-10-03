<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Arch and Leap native application package candidates

The new [package preparer](../scripts/package-system-qt.py) builds separate native
recipe inputs from checksum-verified clean Debian application packages. Actual
ordinary-user `makepkg` and `rpmbuild` produce full Arch and Leap application
candidates. [The exact artifact and inspection record](../release/qualification/next-targets/20261003-system-qt-native-packages.json)
owns their hashes, input source `536fc75`, separately hashed working recipes,
native logs and limits. [Fresh installed lifecycle evidence](../release/qualification/next-targets/20261003-system-qt-installed-packages.json)
now passes on both exact candidates in disposable containers. Complete target
installers and real desktop acceptance remain open; these are private artifacts.

## October 3 installed application and font correction

Fresh containers built from the recorded native qualification images install
the complete application through normal native dependency transactions. Arch
first builds and installs the independent guard in a separate transaction,
checks its files/hooks and empty default hook-override directory, then installs
the application. Leap's actual isolated Python3.13 scriptlets begin and complete
installation. Both registered receipts match every application member, and
their original frozen Python/Qt inventories remain unchanged.

Ordinary UID1002 prepares the immutable runtime from packaged offline wheels,
launches the real offscreen native preview and executes bundled Node24.19 through
the cold lifetime lease. After network disconnection, both package managers
refuse actual replacement and removal under the real preview window or runtime
lease. Idle same-artifact reinstall, removal and reinstall after removal pass;
native `pacman -Qkk`/`rpm -V`, all application inventory members, synthetic user
sentinels and byte-identical runtime receipts pass again. The
[independent public probe](../release/prove-system-qt-package.py) records exact
native exit statuses and log hashes. This is not a version upgrade or rollback.

Two Arch fixture failures remain recorded. The minimal image initially lacks
fakeroot/debugedit; a signed dated dependency install precedes normal guard
build success. Its documentation exclusion also leaves package-owned
/usr/share/doc absent on the first application audit. Only that fixture's exact
usr/share/doc/* exclusion is removed, with signature policy and other tokens
preserved; actual reinstall precedes the successful repeated audit. Neither
failure is hidden or counted as an initial pass.

The native screenshot exposes two missing DejaVu glyphs: New Chat U+FF0B and
pin U+2316. Official package archives and actual font cmaps identify separate
CJK and Symbols2 providers. Signed native font installation, fresh Qt layout
probes and visually inspected unchanged screenshots pass on Arch and Leap.
Every approved symbol has a nonzero shaped glyph index and fits its control.
[The font checkpoint](../release/qualification/next-targets/20261003-linux-surface-fonts.json)
records providers, archive/font hashes and both exact Qt results. The
[standalone font probe](../release/probe-linux-surface-fonts.py) reads literal
design data as an ordinary user; primary-font coverage alone does not establish
fallback rendering.

New recipes require noto-fonts/noto-fonts-cjk on Arch and the narrower
google-noto-sans-symbols2-fonts/google-noto-sans-jp-fonts pair on Leap. Debian/
Ubuntu require fonts-noto-core/fonts-noto-cjk; Fedora requires
google-noto-sans-symbols-2-fonts/google-noto-sans-cjk-fonts. The primary DejaVu
family, approved glyphs and layout stay unchanged. The tested release1 candidates
receive these fonts separately; new recipe artifacts and Debian/Ubuntu/Fedora
fallback installs still need their own build/installed evidence.

## Payload and runtime identity

Debian packages supply checked application, Node24.19, Browser host, Handy and
notice bytes. Their dependency fields and maintainer hooks are not inherited.
The preparer refuses dirty/mismatched source, mixed runtime/Desktop versions,
foreign Noble/source-Qt declarations, wrong architectures and changed checksums.
It preserves prior results and exposes a prepared directory only after validation.

| Candidate | Managed Python profile | System bootstrap | Native package |
| --- | --- | --- | --- |
| Arch snapshot20261001 x86_64 | arch20261001-cp314-x86_64-voice | /usr/bin/python3 | augmentor-agent0.2.13-1 |
| Leap16.0 x86_64 | leap16-cp313-x86_64-voice | /usr/bin/python3.13 | augmentor-agent0.2.13-1.leap16 |

Generated release/runtime metadata, offline wheels and the frozen system Qt
inventory identify the same target. The root-owned joint package receipt binds
the manager's registered name/version-release/architecture to the complete
application-root file/link inventory. The recipe writes that inventory last.
Both inspected native artifacts match every recorded member:29,244 Arch and
29,246 Leap. This inventory covers the application root, not every system library
or other package path.

Desktop, runtime, Browser host and maintenance wrappers use the explicit target
bootstrap. Desktop resolves its immutable ordinary-user Python before launch
and takes the package lease; its existing XWayland default remains present.
Handy's actual build inventory and executable modes pass inspection, as do
offline wheel/stack hashes and inclusion of udev, module-load and tmpfiles rules.
These checks do not establish live device permission or physical dictation.

Original wheel notice bytes are copied through the wheel inventory function.
The Noble-specific Qt6.8.2/ICU notice staging routine is not used to claim coverage
of Arch/Leap system Qt. Distro Qt identities remain supplied by the native package
manager; complete source/license/native closure acceptance stays open.

## Native recipes and transaction guards

Arch uses a generated `PKGBUILD` with checksum-checked local `payload.tar` and
stripping/debug rewriting disabled. The independent
[guard package](../release/arch/guard/PKGBUILD) must be installed and verified in
its own completed transaction before application installation. Declaring it as
a dependency does not establish that pre-hook boundary. Preserve its effective
PreTransaction/AbortOnFail and PostTransaction hooks, including inspection of
hook overrides. Remove the application first and the guard separately afterward.

Leap embeds standalone public guard code in `%pre`, `%posttrans`, final-removal
`%preun` and `%postuntrans`; it needs no application files after removal. All four
recorded interpreter arrays are `/usr/bin/python3.13`, `-I`. Literal RPM query
formats are escaped during spec generation. Native parser/query checks verify
the resulting interpreter arguments and preserved guard code, rather than
assuming a quoted interpreter string works. RPM's
[scriptlet specification](https://rpm.org/docs/4.20.x/manual/spec.html),
[program argument tags](https://rpm.org/docs/4.20.x/manual/tags.html) and
[parser source](https://raw.githubusercontent.com/rpm-software-management/rpm/master/build/parseScript.cc)
explain these mechanisms. The earlier non-isolated Leap build remains identified
separately; its replacement now executes installation, busy refusal, idle
reinstall and final removal/reinstall scriptlets in the fresh owned fixture.

Both recipes retain checked native bytes and the input product's source identity;
the packaging recipe and input artifacts have separate hashes. A source label
alone does not identify the generated package. The complete installer must
independently verify registration, receipt and finalization: package-manager exit
status alone is insufficient. The
[transaction guide](LINUX-PACKAGE-TRANSACTIONS.md) owns previous synthetic failure,
recovery and active-lease evidence, which is not full application acceptance.

## Streaming native artifact verification

The [independent streaming inspector](../scripts/inspect-system-qt-package.py)
now produces artifacts.json only after native package identity, every prepared
file/link, byte hash, executable/mode bit, link target and application/runtime
receipt pass. Arch tar and RPM newc payloads are read without extraction or
application/scriptlet execution. Missing/extra/changed members refuse; changed
artifact bytes/inode identity during inspection also refuse. Prior results stay
preserved. [The exact inspection checkpoint](../release/qualification/next-targets/20261003-system-qt-streaming-inspection.json)
rechecks the previously installed release1 artifacts:29,259 Arch and29,262 Leap
regular-file/link members across the entire native payload, including wrappers
and permission files outside the application root.

The first strict comparison refuses Debian-derived checkout group-write bits.
Both native artifacts already remove those bits while preserving the same bytes.
The inspector admits only that explicit regular-file permission reduction;
it still rejects changes to executable or other permission bits. Future preparation
removes group/world-write bits from regular files and directories before archiving.
Historical preparation bytes are retained. Four meaningful corruption/path/
duplicate/hard-link cases and the three existing preparation cases pass. Directory
ownership/maintenance, full native dependency closure and new artifact production
remain separate gates.

After a normal native build, create a new checked manifest beside that artifact:

```sh
python3 scripts/inspect-system-qt-package.py --prepared PREPARED_DIRECTORY \
  --artifact PREPARED_DIRECTORY/NATIVE_PACKAGE --out PREPARED_DIRECTORY/artifacts.json
```

## Native providers and build repetition

Dependency names were checked against the dated official
[Arch Core](https://archive.archlinux.org/repos/2026/10/01/core/os/x86_64/core.db),
[Arch Extra](https://archive.archlinux.org/repos/2026/10/01/extra/os/x86_64/extra.db)
and [Leap repository metadata](https://download.opensuse.org/distribution/leap/16.0/repo/oss/repodata/repomd.xml),
plus read-only registered package queries in the owned fixtures. Metadata inspection
does not replace authenticated package installation. GTK4/GI/Atspi/GStreamer,
Qt SVG/QML/Wayland, keyring, PortAudio/ALSA/Pulse helpers, native Handy libraries,
fonts and clipboard/input helpers are declared separately for each target.

Leap's system keyring25.2.1 is below the application requirement; the verified
overlay supplies keyring25.6.0. The RPM does not demand an unavailable newer
system package. Its measured C++ requirement is expressed as the actual RPM
GLIBCXX3.4.32 capability. Arch directly depends on `libstdc++`; its dated registered
candidate exports that symbol, while pacman metadata exposes only its SONAME.
No untested GCC minimum is inferred. Full native closure and protection against
coordinated system dependency updates remain separate requirements.

To prepare inputs, use an isolated checkout and new output directory:

```sh
python3 scripts/package-system-qt.py --debian PATH_TO_CHECKED_DEBIAN_ARTIFACTS \
  --wheelhouse PATH_TO_REVIEWED_WHEELS --target arch20261001-x86_64 \
  --out NEW_ARCH_DIRECTORY
python3 scripts/package-system-qt.py --debian PATH_TO_CHECKED_DEBIAN_ARTIFACTS \
  --wheelhouse PATH_TO_REVIEWED_WHEELS --target opensuse-leap16.0-x86_64 \
  --out NEW_LEAP_DIRECTORY
```

Build Arch normally with `makepkg` as an ordinary user. The recorded disposable
builder used `--nodeps --noconfirm` only because installation/guard dependencies
were not being admitted during a build. This does not qualify their installation
and must not become an application-install dependency bypass.
For Leap, place the checked archive in an isolated RPM topdir's `SOURCES` and
the generated spec in `SPECS`, then use ordinary-user `rpmbuild -bb --define
'_topdir NEW_TOPDIR' NEW_TOPDIR/SPECS/augmentor-agent.spec`. Inspect source hashes,
native metadata and complete payload after each new build; do not relabel an old
inspection as qualification of new bytes.

## Complete installer adapters and recorded execution

[Fresh corrected Arch qualification](../release/qualification/next-targets/20261003-arch-clean-complete-installer.json)
now passes the complete matching cleanf85e376 release4 bundle in a new owned
fixture. Normal native dependency/signature admission, the separate guard,
application transaction, ordinary-user setup and repeat, real DSH/plugins, both
fixture model roles, rendering and restart history without replay pass. Its
report explicitly records matching bundled setup and no external overlay.
Native npm12.2 uses bundled Node24.19 with flattened semver. Final native audit,
frozen runtime and approved font shaping pass. The fixture is now offline. Only
regular public native archive/signature cache files were reused and reverified;
no application/user runtime state or keys were transferred. Non-booted upstream
kmod/systemd hooks cannot establish real boot/dictation permissions.

The earlier exact Leap8ad complete installer also passes. These identities are
separate; later source/archives do not inherit either acceptance. The retained
failed Arch8ad bundle and diagnostic helper resume below are historical context
for the module-resolution correction, not current matching-bundle evidence.

[The complete/install/rollback checkpoint](../release/qualification/next-targets/20261003-system-qt-complete-and-release-upgrade.json)
supersedes the pending-execution scope below for its exact clean8adb633 release3
bytes. Both new native packages and full bundles build/inspect/assemble. Leap's
native root plan and ordinary-user complete setup pass actual DSH/plugins, both
fixture model roles, offscreen native rendering, repeat settings and restart
history without replay. Native npm11.16 executes under bundled Node24.19.

Arch's native root plan completes and verifies, but its original user setup
refuses at a hardcoded nested semver import: native npm12.2 uses the flattened
/usr/lib/node_modules/semver provider. The corrected adapter anchors Node
createRequire at npm's package.json. Actual engine probes pass both native
layouts; three actual Node regression cases exercise nested/flattened resolution
and an unsupported engine. An explicitly hashed external corrected helper then
resumes Arch's partial setup and passes the full user/DSH/model/history proof.
The report records installerOverlayUsed:true and setupScriptMatchesBundle:false;
the original bundle stays unchanged. New clean matching fixed Arch assembly and
root/user qualification remains required. Initial failures and diagnostic-driver
omissions are retained. Both installed release3 packages pass final native file
audits and actual font shaping; both complete fixtures are now offline.

[The distinct release probe](../release/prove-system-qt-upgrade.py) also passes
offline release1→3→1 transactions with536→8ad→536 source. Desktop and real
bundled-Node leases refuse upgrade and rollback while busy. Idle transactions,
full inventories, native audits and cold rendering pass, with original packages,
synthetic user files and immutable runtime receipts restored/preserved. This is
package-release qualification only, not product-version or managed DSH/history
upgrade/rollback, graphical sessions or interrupted/reboot recovery.

[The complete installer checkpoint](../release/qualification/next-targets/20261003-system-qt-installer-adapters.json)
records explicit Arch/Leap package and managed-runtime contracts, target-specific
native dependency commands and full bundle assembly inputs. The native producer
requires a fresh streaming inspection and current preparer identity, then matching
clean Desktop/Browser source. Arch additionally checks the guard archive's exact
public controls, modes and native identity; no install script or extra member is
admitted. Only five named public reference files are copied into the bundle.

Arch installs dependencies, then its guard in a separate transaction. The
[read-only verifier](../scripts/linux-package-verification.py) checks registered
guard identity, exact root-owned files, effective default HookDir, absence of
masked hooks and native package audit before application installation. It never
begins maintenance: application hooks must acquire their own intent. After either
native package manager runs, setup requires settled durable/volatile state,
registered package/source/target/product identity, full app inventory and native
file audit. Completed user stamps also repeat these checks and immutable runtime
verification, rather than bypassing an unresolved or changed installation.

That independent verifier actually passes as ordinary UID1002 on both recorded
installed release1 candidates. It imports only the separate checked public guard;
no installed application code is imported during outcome verification. Thirty-three
focused distribution/setup/guard/npm failure and Debian regression cases pass.
These checks are not execution of a newly assembled complete bundle.

Leap uses /usr/bin/python3.13 in install.sh, optional voice bootstrap and leased
DSH service. Native npm CLI paths are explicit: /usr/lib/node_modules/npm/bin/npm-cli.js
on Arch and /usr/lib64/node_modules/npm24/bin/npm-cli.js on Leap. Bundled Node
executes that CLI and its actual semver engine check before npm ci. A generic npm
wrapper exists only in the fresh private install for nested DSH plugin commands;
no system npm alias or owner PATH is changed. The dependency research verifies
Arch npm12.2.0 supports Node24.19. Actual installed checks above also establish
Leap npm11.16.0 accepts bundled Node24.19 (engine ^20.17.0 or >=22.9.0).

Base and optional native providers come from dated official metadata and read-only
native solver plans. Leap explicitly needs ca-certificates-mozilla for public CA
trust. Its pulseaudio-utils hard dependency can select PipeWire/Pulse and
WirePlumber even with --no-recommends; that solver behavior is recorded, not
qualified physical audio. Optional voice/GPU/Docker tools remain explicit choices.
Their installation, compiler/model/service/device acceptance is separate.

## Remaining acceptance

[Fresh release2 builds and source scope](../release/qualification/next-targets/20261003-system-qt-release2-and-source-scope.json)
now record actual clean f1c3975 Desktop/Browser and native Arch/Leap builds with
the font dependencies. Complete streaming inspection passes every29,263 Arch/
29,266 Leap native file/link member, with zero prepared mode reductions. Their
application inventories contain29,248/29,250 members. Installation and complete
setup are still separate gates for these exact new bytes.

Voice0.1.19 has an exact public npm archive containing shipped runtime source,
but no full public repository snapshot was found. Complete assembly now offers
the explicit [package-source mode](COMPLETE-INSTALL.md) with checked Adaptive
source reuse. Archive/provenance hashes, coverage exclusions and the declared
upstream-ref limit remain in the bundle; it does not export private source or
complete legal/source-kit acceptance. Twenty-one source/setup cases pass, while
actual assembly/execution with new matching clean artifacts remains pending.

Arch/Leap source adapters now provide target/runtime contracts, checked guard
ordering, explicit bootstrap and native npm selection. Matching new clean bundle
assembly and actual installed/resumed complete setup checks now pass for the
exact corrected Archf85 and earlier Leap8ad bundles. Later artifacts and actual
interrupted native package/service/boot recovery need their own checks.
Inspect native dependency solver plans before
changing owned fixtures; preserve frozen Qt/Python manifests and runtime receipts.
Any drift needs a new candidate rather than refreshing old inventory.

Fresh native installation, cold ordinary-user runtime/rendering and busy/idle
replacement/removal now pass within their recorded container scope. New font
artifacts and exact Archf85/Leap8ad full installers now pass. The earlier Arch
diagnostic resume stays separately labeled. Real GNOME/KDE/Mint
sessions, consent/input/lock/reboot, graphical Browser, physical audio, version
upgrades/rollback and source/legal/release acceptance stay open. All five rollout
points remain active. Owner installations, services, models, audio devices and the
22-file license proposal remain unchanged.


## Debian input archive permission contract

The Debian producer now normalizes both staged package trees immediately before
archiving: directories0755, regular nonexecutables0644, and files with any
existing execute bit0755. It determines type and executable intent with `lstat`,
skips symlinks without traversing them, and rejects unsupported path types before
changing staged modes. Payload bytes, source-Qt input inventories, target and
`dpkg-deb --root-owner-group` ownership handling remain unchanged. It does not
chmod the source checkout or an installed application.

The triggering [actual Mint16bcb evidence](../release/qualification/next-targets/20261003-mint16bcb-fresh-emulated-proof.json)
is distinct from source tests: normal signed native reinstall and unchanged
installer idempotence pass, while the full proof refuses root-owned mode0664
memory source before SDK activity. The original DEB preserves0664/0775 from the
clean group-writable build checkout; resetting archive ownership alone does not
normalize modes. Final native/exclusive-lease/process/socket/settings/old-account
readback passes, with zero model requests and no pending SDK action.

Six focused tests cover copied group-writable directories/files, unchanged bytes
and owners, executable intent, internal/external/dangling symlinks, unsupported
path refusal and real DEB member metadata. All12 Debian tests pass. Corrected
large application artifacts and native installation have not been executed;
new builds and fresh installed acceptance remain required. Existing Arch/Leap
artifact qualifications remain bound to their earlier exact input bytes.

The subsequent clean365 Mint build now verifies the corrected metadata in the
actual runtime and desktop DEBs: every directory0755 and ordinary file0644/0755,
root ownership, retained symlink targets, all source-Qt/wheel/Handy input members
and complete archive hashes. This supersedes the preceding pending-build
statement; native adoption remains false. The
[365 artifact/source-profile checkpoint](../release/qualification/next-targets/20261003-mint365-permission-fresh-proof.json)
keeps source/build evidence separate from the failed installed16b proof and
pending fresh UID1003 execution. The Linux filesystem permission tests explicitly
skip other platforms; the Debian producer and its targets are unchanged.
