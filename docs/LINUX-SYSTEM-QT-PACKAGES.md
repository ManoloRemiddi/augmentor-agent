<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Arch and Leap native application package candidates

The new [package preparer](../scripts/package-system-qt.py) builds separate native
recipe inputs from checksum-verified clean Debian application packages. Actual
ordinary-user `makepkg` and `rpmbuild` produce full Arch and Leap application
candidates. [The exact artifact and inspection record](../release/qualification/next-targets/20261003-system-qt-native-packages.json)
owns their hashes, input source `536fc75`, separately hashed working recipes,
native logs and limits. These packages have not passed installed acceptance or
the complete target installer; they are private qualification artifacts.

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
separately; its replacement has not yet executed installed scriptlets.

Both recipes retain checked native bytes and the input product's source identity;
the packaging recipe and input artifacts have separate hashes. A source label
alone does not identify the generated package. The complete installer must
independently verify registration, receipt and finalization: package-manager exit
status alone is insufficient. The
[transaction guide](LINUX-PACKAGE-TRANSACTIONS.md) owns previous synthetic failure,
recovery and active-lease evidence, which is not full application acceptance.

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

## Remaining acceptance

The complete bundle still needs Arch/Leap target/runtime contracts, verified guard
installation order, explicit bootstrap propagation, matching npm24 selection and
installed/resumed setup checks. Inspect native dependency solver plans before
changing owned fixtures; preserve frozen Qt/Python manifests and runtime receipts.
Any drift needs a new candidate rather than refreshing old inventory.

Next execute fresh native installation, cold ordinary-user runtime/rendering and
busy/idle replacement/removal, then full installer/resume. Real GNOME/KDE/Mint
sessions, consent/input/lock/reboot, graphical Browser, physical audio, version
upgrades/rollback and source/legal/release acceptance stay open. All five rollout
points remain active. Owner installations, services, models, audio devices and the
22-file license proposal remain unchanged.
