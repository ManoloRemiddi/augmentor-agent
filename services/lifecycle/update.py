# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared prepare/drain/apply decision, with OS-owned process/file mechanisms.

The caller pins and verifies both artifacts before entering this function, and
supplies a fresh durable journal. This function does not download, establish
publisher trust, complete installation, reopen components or replay recovery.
"""


def authorize_update(journal, preparation, installer, *, revalidate=None):
    """Transfer apply authority once, after durable intent and observed drain.

    preparation() returns the platform graph context. installer(gate) returns
    an independent installer context with wait_ready()/authorize(). The caller
    must exit its coordinator process after success; Setup's final lifetime
    check deliberately prevents replacing this still-running interpreter.
    A reversibly released preparation can be archived before any shutdown.
    Later or uncertain failures retain the record for independent recovery.
    Customer orchestration supplies revalidate(stage), which must return exactly
    True after checking fresh publisher authority, the selected bytes and current
    consent. Legacy fixed-artifact qualification callers omit this hook; omission
    does not authorize a downloaded release or qualify automatic installation.
    """
    if journal.record['phase'] != 'verified':
        raise ValueError('Use a fresh verified update attempt; never resume commands from a saved phase.')
    def authority(stage):
        if revalidate is not None and revalidate(stage) is not True:
            raise ValueError('Update authorization changed. Preserve this attempt for inspection.')
    context = None
    try:
        authority('verified')
        journal.advance('preparing')
        context = preparation()
        with context as graph:
            graph.check()
            journal.advance('prepared')
            # Refuse stale selection/withdrawal or revoked consent before any
            # owned peer is asked to shut down; reservation cleanup stays live.
            authority('prepared')
            graph.check()
            graph.drain(checkpoint=journal.checkpoint)
            graph.check()
            journal.advance('drained')
            # Launch only after shutdown: installer readiness has its own bounded
            # deadline, independent of how many live components needed draining.
            with installer(graph.gate) as backend:
                backend.wait_ready()
                graph.check()
                # The independent installer still has no apply authority. Check
                # again after drain/readiness, before the durable APPLY intent.
                authority('installer-ready')
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
