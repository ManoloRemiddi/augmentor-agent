# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live Mac graph/apply/completion composition, executed outside the app."""
from pathlib import Path
import sys

from lifecycle.macos_apply import MacInstallerBackend
from lifecycle.posix_preparation import PosixPreparation
from lifecycle.update import authorize_update
from lifecycle.update_journal import UpdateJournal,artifact
from .macos_completion import complete_observed


class CapturedPreparation(PosixPreparation):
    def __init__(self,*args,captured,**kwargs):
        super().__init__(*args,**kwargs);self.captured=captured

    def __enter__(self):
        result=super().__enter__()
        try:self.captured(self.reopen_plan())
        except BaseException as error:
            self.__exit__(type(error),error,error.__traceback__);raise
        return result


class MacCoordinator:
    def __init__(self,destination,staged,runtime,shared,transactions,source_release,target_release,
            source_payload,target_payload,source,target,*,development=False):
        if sys.platform!='darwin':raise RuntimeError('Mac coordination requires native macOS.')
        if type(development) is not bool:raise ValueError('Use an explicit distribution policy.')
        self.destination=Path(destination).absolute();self.staged=Path(staged).absolute()
        self.runtime,self.shared,self.transactions=map(Path,(runtime,shared,transactions))
        self.source_release,self.target_release=source_release,target_release
        self.source_payload,self.target_payload=source_payload,target_payload
        self.source,self.target=artifact(source),artifact(target)
        self.development=development;self.begun=False;self.backend=None;self.plan=None;self.completion=None

    def capture(self,plan):
        if self.plan is not None:raise ValueError('A live reopening plan cannot be replaced.')
        from .macos_reopen import validate_plan
        self.plan=validate_plan(plan)

    def prepare_and_apply(self,journal,revalidate):
        if self.begun or self.backend is not None or not callable(revalidate):
            raise ValueError('Use a fresh coordinator and live publisher/consent authority.')
        self.begun=True  # Unknown outcomes never permit another attempt.
        if (journal.directory!=self.transactions or journal.record['source']!=self.source
                or journal.record['target']!=self.target):
            raise ValueError('The fresh journal belongs to another update.')
        def installer(gate):
            self.backend=MacInstallerBackend(gate,self.destination,self.staged,self.source_release,self.target_release,
                self.source_payload,self.target_payload,development=self.development,journal=journal)
            from copy import deepcopy
            self.backend.reopen_plan=deepcopy(self.plan)
            return self.backend
        result=authorize_update(journal,lambda:CapturedPreparation(self.destination/'Contents/Resources/app',
            self.runtime,self.shared,transactions=self.transactions,captured=self.capture),installer,revalidate=revalidate)
        self.backend.observe_acknowledgement()
        return result

    def complete(self):
        if self.completion is not None:raise ValueError('A completed coordinator cannot run health or archive again.')
        result=complete_observed(self.backend,self.source,self.target)
        self.completion=result
        return result

    def run(self,revalidate):
        with UpdateJournal(self.transactions,self.source,self.target) as journal:
            self.prepare_and_apply(journal,revalidate)
        self.complete()
        from .macos_reopen import reopen_observed
        reopened=reopen_observed(self.backend,self.plan,self.completion)
        return {**self.completion,'reopened':reopened}
