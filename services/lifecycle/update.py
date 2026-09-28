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
    A reversibly released preparation can be archived before any shutdown.
    Later or uncertain failures retain the record for independent recovery.
    """
    if journal.record['phase'] != 'verified':
        raise ValueError('Use a fresh verified update attempt; never resume commands from a saved phase.')
    context = None
    try:
        journal.advance('preparing')
        context = preparation()
        with context as graph:
            graph.check()
            journal.advance('prepared')
            graph.drain(checkpoint=journal.checkpoint)
            graph.check()
            journal.advance('drained')
            # Launch only after shutdown: installer readiness has its own bounded
            # deadline, independent of how many live components needed draining.
            with installer(graph.gate) as backend:
                backend.wait_ready()
                graph.check()
                journal.advance('installer-ready')
                journal.advance('apply-intent')
                graph.check()
                backend.authorize()
                journal.advance('apply-acknowledged')
    except BaseException as error:
        # An exception alone is not evidence of cancellation. Only a platform's
        # live confirmed release, plus a journal with no shutdown intent, can
        # reopen ordinary admission. Contexts without that witness stay pending.
        from .update_journal import PREPARATION_PHASES
        try:
            if (journal.record['phase'] in PREPARATION_PHASES and not journal.record['steps']
                    and not journal.uncertain and getattr(context,'preparation_released',False) is True):
                journal.cancel_preparation(lambda: context.preparation_released)
        except Exception:
            error.add_note('Preparation cancellation was not durably archived; retain the update record for recovery.')
        raise
    return {'transactionId': journal.record['id'], 'coordinatorMustExit': True,
            'installationComplete': False}
