<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Proposed MIT permission for recipient source controls

Status: proposal only. No license grant, source header or repository license has changed.

Recommendation: license the following 22 Augmentor-authored recipient build,
acquisition, verification, policy and instruction files under standard MIT,
without the Augmentor resale condition. This gives recipients a clear permission
for these build materials while the application and all other files retain their
existing terms. Third-party components retain upstream terms throughout.

This is a proposed engineering distribution choice, not final legal approval.
The existing root LICENSE states: “This condition must accompany all copies or
substantial portions of the Software, including modified versions.” Removing
that intentional condition for this file set requires the copyright owner's
explicit decision; general authorization to finish distro work does not decide it.

The exact private review artifacts are in outputs/linux-rollout/: the draft
standard MIT text, recipient-controls-license-scope.json.draft with current file
hashes, and recipient-controls-MIT-header.patch.draft. The patch changes only the
SPDX identifier in files which support comments. JSON stays byte-identical and
would be covered by an explicit path-scoped license declaration. If approved,
add the scope/license declaration alongside the headers, preserving the root
LICENSE for all other Augmentor-authored files. Preserve historical receipts and
kit manifests; newly assembled controls need their own byte identities/checks.

The original private kit18, proposed hash snapshot and header draft remain
historical review artifacts. Subsequent engineering changes updated the source
runtime guide and notice collector, while preserving their existing license
terms. The two current hashes below supersede only those original hash entries;
the proposed 22-path permission scope is unchanged and remains unapproved. The refreshed current scope and header-only draft are retained privately as
qt-recipient-point5-research162/recipient-controls-current-scope224.json.draft
and recipient-controls-current-header224.patch.draft; neither is applied. The
separate current-control kit220 has its own manifest and omits the prior bound
Python bytecode cache; no historical kit or receipt was rewritten. These source
kits and runtime proofs are review candidates, not a binary release or complete
legal/source-kit acceptance.

| Proposed file | Current SHA256 | Header change |
| --- | --- | --- |
| docs/LINUX-LGPL-SOURCE-RUNTIME.md | 38d03003f8af5f09626c67f3faeac753553bafa8de9737e8d89fd40af3d57420 | MIT |
| release/acquire-linux-lgpl-runtime-sources.py | f889871a8d77be2ed4946a637be9e8eb89aab5e94dbccfab3e1475a4cdab6e0d | MIT |
| release/acquire-ubuntu-toolchain-sources.py | 0d098d6cdaba46718057e7886dbebafd70aba5ca67ac9531457cb8a0d6238791 | MIT |
| release/acquire-ubuntu-toolchain.py | bafb64db71aa312c3e2f9e5bfe0d77e33640a886128ddbe2bfeb3fbc8c2dce40 | MIT |
| release/build-linux-lgpl-runtime.py | 9594c4439638cccb8f3bb91b34848cb95169d075aa61ab614171fd066c41dac7 | MIT |
| release/collect-source-qt-notices.py | ad711cf7ab4e56fe5f054469124f4970b678ef81ae82eb8220013b43f55acf4c | MIT |
| release/derive-source-pyside-wheel.py | 50c2ec4720dd784a0a408845a934bc622ed679c7404a6668d997e0710cf7b7eb | MIT |
| release/linux-lgpl-runtime-sources.json | 969dca5093394282eef5517ade6e0bcb31d1a9ceb1b22513d213aa9ef434196e | JSON scope declaration |
| release/probe-source-plasma-shader.py | 65d05f5e8d45bc3dad571098a3e6f10f971bd1add6278e0a02e9099afb992a54 | MIT |
| release/probe-source-qt-build.py | fd4fe26ca5a056484e1c80a1d369f16bdce7093a022f722336254ee6c29e601c | MIT |
| release/probe-source-qt-recipient-build.py | 440b4cfe57a516d519d75585365f109b2842e6ffb182b96fc7a3819c2d970591 | MIT |
| release/probe-source-qt-replacement.py | c738520682361840110dd4584777c4b80d587690c181da4b0fdfb95a1d7badad | MIT |
| release/probe-source-qt-runtime.py | 860cc78cbedd875907ce04b165c640d1b2f152614eaaf074433b364a40570b4d | MIT |
| release/probe-ubuntu-toolchain-auth.py | e148fa5dc124607b15149b506a10babcc86d4b0c6162afb1bd93f2c5f8b9d93b | MIT |
| release/probe-ubuntu-toolchain-source-auth.py | d4fe8cd2ed4c0ec1b3d8f0ffabf4c4528e07dcbf04734d87a5e6cbd8d36d8aae | MIT |
| release/qt-source-runtime-recipient-builder.Dockerfile | 9f256bf7043c0c0d44e8bc5ff2208df5e2260ae8c903864d6fd80694de14c20a | MIT |
| release/qualification/next-targets/20261002-public-noble-base-packages.json | 2d2e83d2e3db92145d5f96fdc5f80d00ea03c239aac6f4bea4d3c7c6e14526a0 | JSON scope declaration |
| release/qualification/next-targets/20261002-ubuntu-builder-base-source-lock.json | 76d303297daed229aa5350d6e81e47d29184a290d036023d2653a5d7ae14e102 | JSON scope declaration |
| release/qualification/next-targets/20261002-ubuntu-source-toolchain-lock.json | ee6c3fb58c36563be35466ac6e8c0dfdef3889a7e4f9663d6483f60b623166d2 | JSON scope declaration |
| release/stage-source-qt-runtime.py | 3dc1cd88387cdb0afa49ef9a68f44e4a0591fac80860a4f5c78adf6c27fd9049 | MIT |
| release/verify-ubuntu-base-archive.py | f8eff4c75bccacd3db07191dd9b30f79ea6c9dbd3c82eee2e355983aa11eed35 | MIT |
| scripts/verify-plasma-shader.py | fd03ab56d602f2980032d00647f5c21a478530762c21c01f59dd59c8fdb77ecb | MIT |

## Draft standard MIT text; proposed only

```text
MIT License

Copyright (c) 2026 Manolo Remiddi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
