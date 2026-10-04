# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live managed-Linux graph, selection and offline-health composition.

The external driver owns authentic download staging; the managed plan binds the
exact owned user service to the prepared original socket process.
No saved plan or journal can reconstruct this controller after interruption.
"""
from lifecycle.posix_preparation import PosixPreparation
from lifecycle.update import authorize_update
from lifecycle.update_journal import UpdateJournal
from .linux_managed import ManagedPlan,ManagedBackend
from .linux_completion import complete_observed


class CapturedPreparation(PosixPreparation):
    def __init__(self,*args,captured,services=None,desktop=None,**kwargs):
        super().__init__(*args,**kwargs);self.captured=captured;self.services=services;self.desktop=desktop

    def __enter__(self):
        result=super().__enter__()
        try:
            if self.services is not None:self.services.bind(self)
            if self.desktop is not None:self.desktop.bind(self)
            self.captured(self.reopen_plan())
        except BaseException as error:
            self.__exit__(type(error),error,error.__traceback__);raise
        return result


class LinuxCoordinator:
    def __init__(self,plan,runtime,shared,transactions):
        if not isinstance(plan,ManagedPlan) or plan.fd is None or plan.closed:
            raise ValueError('Retain the original successful managed preflight.')
        self.plan,self.runtime,self.shared,self.transactions=plan,runtime,shared,transactions
        self.begun=False;self.backend=None;self.reopen_plan=None;self.completion=None

    def capture(self,plan):
        if self.reopen_plan is not None:raise ValueError('The original graph cannot be replaced.')
        self.reopen_plan=plan

    def run(self,revalidate):
        if self.begun or not callable(revalidate):raise ValueError('Use a fresh coordinator and live publisher/consent authority.')
        self.begun=True
        # A changed selection/artifact should be refused before recording an
        # attempt or reserving any accepted work. Check around every bounded
        # publisher refresh too, while preparation can still be cancelled.
        self.plan.validate(offline=False)
        def authority(stage):
            self.plan.validate(offline=False)
            result=revalidate(stage)
            self.plan.validate(offline=False)
            return result
        def installer(gate):
            self.backend=ManagedBackend(self.plan,gate,journal)
            from .posix_reopen import validate_plan
            self.backend.reopen_plan=validate_plan(self.reopen_plan)
            return self.backend
        with UpdateJournal(self.transactions,*self.plan.pair()) as journal:
            authorize_update(journal,lambda:CapturedPreparation(self.plan.source,self.runtime,self.shared,
                transactions=self.transactions,captured=self.capture,services=self.plan.services,desktop=self.plan.desktop),installer,revalidate=authority)
            self.backend.observe_acknowledgement()
        self.completion=complete_observed(self.backend)
        return self.completion
