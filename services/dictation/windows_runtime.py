# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Use only the bundled WebView2 for the embedded Windows recording pill."""
import json
from pathlib import Path


def environment(runtime, values):
    runtime = Path(runtime)
    record = json.loads((runtime/'BUILD.json').read_text(encoding='utf-8'))['windowsRuntime']
    folder = record['folder']
    if Path(folder).name != folder: raise ValueError('Invalid bundled browser location.')
    browser = runtime/'webview2'/folder
    if not (browser/'msedgewebview2.exe').is_file():
        raise RuntimeError('The bundled dictation browser is missing. Repair the Augmentor installation.')
    return {**values, 'WEBVIEW2_BROWSER_EXECUTABLE_FOLDER': str(browser.resolve())}
