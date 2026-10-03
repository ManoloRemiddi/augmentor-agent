# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('cold_history',Path(__file__).resolve().parents[1]/'release/prove-published-linux-cold-history.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ColdHistoryTests(unittest.TestCase):
    def fixture(self): return {'sessionId':'owned', 'hasMore':False, 'events':[{'type':'event','event':{'seq':0,'type':'user/message','data':{'text':'fixture'}}}, {'type':'event','event':{'seq':1,'type':'assistant/message','data':{'text':'answer'}}}]}

    def test_only_cold_page_is_called_never_follow_or_create(self):
        expected=self.fixture();remote=Mock();remote.invoke.return_value={'hasMore':False,'records':expected['events']}
        module.page(remote,'owned',expected)
        remote.invoke.assert_called_once_with('session/page',{'request':{'address':{'kind':'session','sessionId':'owned'},'throughSeq':1,'maxMessages':200}})
        remote.stream.assert_not_called();remote.call.assert_not_called()

    def test_changed_lost_reordered_extra_or_paginated_events_refuse(self):
        expected=self.fixture()
        variants=[expected['events'][:-1],expected['events'][::-1],expected['events']+[{'type':'event','event':{'seq':2,'type':'session/end-seed','data':{}}}]]
        changed=copy.deepcopy(expected['events']);changed[0]['event']['data']['text']='changed';variants.append(changed)
        for records in variants:
            remote=Mock();remote.invoke.return_value={'hasMore':False,'records':records}
            with self.subTest(records=records),self.assertRaises(ValueError):module.page(remote,'owned',expected)
        remote=Mock();remote.invoke.return_value={'hasMore':True,'records':expected['events']}
        with self.assertRaises(ValueError):module.page(remote,'owned',expected)

    def test_unknown_rpc_outcome_is_never_replayed(self):
        remote=Mock();remote.invoke.side_effect=OSError('unknown read')
        with self.assertRaises(OSError):module.page(remote,'owned',self.fixture())
        remote.invoke.assert_called_once();remote.stream.assert_not_called()

    def test_foreign_partial_and_sequence_gap_inputs_refuse_before_rpc(self):
        for change in ('foreign','partial','gap','empty'):
            expected=self.fixture()
            if change=='foreign':expected['sessionId']='foreign'
            elif change=='partial':expected['hasMore']=True
            elif change=='gap':expected['events'][1]['event']['seq']=2
            else:expected['events']=[]
            remote=Mock()
            with self.subTest(change=change),self.assertRaises(ValueError):module.page(remote,'owned',expected)
            remote.invoke.assert_not_called()


if __name__=='__main__':unittest.main()
