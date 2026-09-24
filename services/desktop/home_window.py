# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Manage only the configured Chromium dashboard app window on KDE."""
import json
import re
import sys
from urllib.parse import urlsplit


def window_script(url, action):
    if action not in ('open', 'toggle', 'probe'):
        raise ValueError('Unknown Home window action')
    parsed = urlsplit(url)
    # Chromium's URL app identity is hostname + '_' + path (not page title).
    # It omits scheme/port; separate apps on the same host/path share that identity.
    name = re.sub(r'[<>:"/\\|?*]', '_', parsed.hostname+'_'+(parsed.path or '/')).strip('_')
    prefix = 'chrome-'+name+'-'
    return '''
var prefix=PREFIX, appName=APPNAME, action=ACTION;
var matches=workspace.windowList().filter(function(w) {
    var c=String(w.resourceClass), n=String(w.resourceName);
    return !w.deleted && (c.indexOf(prefix)===0 ||
        (c==='AugmentorHome' && n===appName));
});
if (action==='toggle') {
    matches.forEach(function(w) { w.closeWindow(); });
} else if (action==='open' && matches.length) {
    var w=matches[matches.length-1];
    w.minimized=false;
    if (w.desktops.length) workspace.currentDesktop=w.desktops[0];
    workspace.activeWindow=w;
}
callDBus(SERVICE,'/com/augmentor/Desktop','com.augmentor.Desktop','Report',TOKEN,
    JSON.stringify({found:matches.length}));
'''.replace('PREFIX', json.dumps(prefix)).replace('APPNAME', json.dumps(name)).replace('ACTION', json.dumps(action))


if __name__ == '__main__':
    from gi.repository import Gio
    from kwin import KWin
    try:
        result = KWin(Gio.bus_get_sync(Gio.BusType.SESSION, None)).execute(window_script(sys.argv[1], sys.argv[2]))
        print(json.dumps(result))
    except Exception as error:
        print('Home window control: '+str(error), file=sys.stderr)
        raise SystemExit(1)
