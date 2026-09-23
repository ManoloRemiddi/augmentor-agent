# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Same pure rule as packages/templates/clipboard.mjs, verified by shared fixtures.
def expand_template(template, snapshot=None):
    if '[clipboard]' not in template:return template
    if not isinstance(snapshot,str) or not snapshot.strip():
        raise ValueError('Clipboard has no text. Copy text and choose the prompt again.')
    return template.replace('[clipboard]',snapshot)
