// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {isRoutineQuery} from '../dist/runtime/src/permissions.js';

test('literal informational commands run without an approval', () => {
  for (const command of [
    'date', "date '+%A, %B %d, %Y %H:%M:%S %Z'", ' date -u +%FT%TZ ',
    '/usr/bin/date --iso-8601=seconds', '/bin/date -R', 'date "+%H:%M"',
    'pwd', 'pwd -P', 'whoami', 'id -un', 'uname -a', 'uptime -p', 'free -h', 'df -h',
  ]) assert.equal(isRoutineQuery(command), true, command);
});

test('changes, shell syntax, unknown options and executable paths retain approval', () => {
  for (const command of [
    undefined, null, {}, '', ' ', 'date -s now', 'date --set=now', 'date --set now',
    'date 090512002026', 'date -us now', 'date --file=/tmp/input', 'date +%T +%F',
    'date; touch /tmp/no', 'date && touch /tmp/no', 'date || true', 'date &',
    'date | tee /tmp/no', 'date > /tmp/no', 'date >> /tmp/no', 'date < /tmp/input',
    'date\ntouch /tmp/no', 'date\r', 'date\t', 'date\0',
    'date "$(touch /tmp/no)"', 'date +`touch /tmp/no`', "date '+$(touch /tmp/no)'",
    'date ${X}', 'date <(touch /tmp/no)', 'date \\; touch /tmp/no', 'date "unterminated',
    'date #comment', 'TZ=UTC date', 'sudo date', 'bash -c date', 'env date',
    '/tmp/date', './date', '/usr/local/bin/date', 'hostname newname', 'touch file',
    'find . -exec rm {} +', 'git status', 'free -s 1', 'id someone', 'uname --unknown',
    'constructor', '__proto__', 'toString',
  ]) assert.equal(isRoutineQuery(command), false, String(command));
});
