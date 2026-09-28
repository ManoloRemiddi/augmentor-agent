# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared prepare/drain/apply decision, with OS-owned process/file mechanisms.

The caller pins and verifies both artifacts before entering this function, and
supplies a fresh durable journal. This function does not download, establish
publisher trust, complete installation, reopen components or replay recovery.
"""


def authorize_update(journal, preparation, installer):
    """Transfer apply authority once, after durable intent and observed drain.

    preparation() returns the platform graph context. installer(gate) returns
    an independent installer context with wait_ready()/authorize(). The caller
    must exit its coordinator process after success; Setup's final lifetime
    check deliberately prevents replacing this still-running interpreter.
    Any exception leaves the journal for independent inspection and recovery.
    """
    if journal.record['phase'] != 'verified':
        raise ValueError('Use a fresh verified update attempt; never resume commands from a saved phase.')
    journal.advance('preparing')
    with preparation() as graph:
        graph.check()
        journal.advance('prepared')
        graph.drain(checkpoint=journal.checkpoint)
        graph.check()
        journal.advance('drained')
        # Launch only after shutdown: installer readiness has its own bounded
        # deadline, independent of however many live components needed draining.
        with installer(graph.gate) as backend:
            backend.wait_ready()
            graph.check()
            journal.advance('installer-ready')
            journal.advance('apply-intent')
            graph.check()
            backend.authorize()
            journal.advance('apply-acknowledged')
    return {'transactionId': journal.record['id'], 'coordinatorMustExit': True,
            'installationComplete': False}
