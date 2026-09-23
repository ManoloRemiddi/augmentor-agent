<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Public Augmentor source

## Publication boundary

The public repository is
[augmentor-agent](https://github.com/ManoloRemiddi/augmentor-agent).
It contains the maintained Augmentor Desktop and Browser source, build recipes,
tests, documentation and required component notices. Its first commit is a clean
source snapshot under [MIT with Augmentor Resale Restriction](../LICENSE).

The former development repository, `augmentor-agent-history`, remains private and is archived. Its Git history, alternate
branches, pull requests, issue comments, Actions logs, CI artifacts and private
release assets are outside this publication. The old browser-only scaffold is
not the current Browser product; the maintained implementation is `apps/browser`.

Existing MIT distributions retain the permissions originally granted to their
recipients. This publication does not retroactively change those permissions.
The license requires written permission to resell Augmentor, including modified
versions, while preserving personal/business use and modification.

## Initial September 23 snapshot review (historical procedure)

Export only tracked source files from the reviewed development commit; never
copy a working directory recursively. Exclude `.git`, ignored files, local
configuration, credentials, databases, conversations, recordings, captures,
build outputs, dependency installations and model weights. Preserve tracked
synthetic test fixtures and example configuration.

Scan the exact export with the checksum-verified Gitleaks 8.30.1 binary, with
redaction enabled and archive/encoded-content inspection. Review credential-like
values, private network endpoints, personal paths, source assets and example
configuration manually as well. Test placeholders, public keys and dependency
checksums must be distinguished from authentication material; do not conceal
findings with broad exclusions. Do not publish raw scan reports containing
suspected secrets.

The new Git history must contain only reviewed snapshot commits. Use the owner's
GitHub `noreply` identity for publication commits. Push to a private repository,
scan a fresh remote clone, and only then make that repository public. Keep the
original development history private.

See `SOURCE-PUBLICATION.json` at the public repository root for the exact exported
development revision and publication checks. Historical development documents
may reference private commits or old installations; those references do not
publish the associated private artifacts or certify the current source build.

## Future updates

Develop directly on `main` or feature branches in the canonical public repository,
`ManoloRemiddi/augmentor-agent`. There is no continuing private-to-public mirror.
Review the complete public Git diff for private data before pushing.
Carry the combined license, headers and package metadata forward. Never merge
private development history into the public repository or enable a mirror push.
Audit each binary release separately before uploading it. Source publication
does not update anyone's installed desktop or relicense older downloads.

## September 23 repository consolidation

The clean public repository was renamed from `augmentor-agent-source` to
`augmentor-agent` without importing private history. The original
`SOURCE-PUBLICATION.json` remains unchanged as the publication record.
See [repository roles, archives and preserved work](REPOSITORIES.md).
