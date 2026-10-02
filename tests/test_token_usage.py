# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from augmentor_linux.token_usage import TokenCalendar, TokenUsage, read_usage

SUMMARY={'start':'2025-10-03','end':'2026-10-02','days':[{'date':'2026-10-01','total':130,'input':80,'output':20,'cached':30}], 'total':130,'records':1,'sources':['Pi'],'incomplete':0}

class TokenUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.owner=QWidget();self.owner.accent=QColor('#61ef85');self.owner.background=QColor('#121718')
        self.addCleanup(self.owner.deleteLater)
    def test_calendar_keyboard_selection_announces_reported_values_and_bounds(self):
        c=TokenCalendar(self.owner);self.addCleanup(c.deleteLater);c.resize(600,112);c.set_data(SUMMARY);c.show();c.setFocus();self.app.processEvents()
        selected=[];c.selected.connect(selected.append)
        QTest.keyClick(c,Qt.Key.Key_Up)
        self.assertEqual(c.current,date(2026,10,1));self.assertIn('130 tokens · 80 input / 20 output',selected[-1]);self.assertIn(selected[-1],c.accessibleName())
        QTest.keyClick(c,Qt.Key.Key_Home);QTest.keyClick(c,Qt.Key.Key_Up);self.assertEqual(c.current,c.start)
        QTest.keyClick(c,Qt.Key.Key_End);QTest.keyClick(c,Qt.Key.Key_Right);self.assertEqual(c.current,c.end)
        self.assertIn('No recorded tokens',selected[-1])
    def test_all_days_fit_narrow_width_and_mouse_selection_reports_same_counts(self):
        c=TokenCalendar(self.owner);self.addCleanup(c.deleteLater);c.set_data(SUMMARY);c.show()
        for width in (250,420,624):
            c.resize(width,112);self.app.processEvents();c.grab()
            self.assertEqual(len(c.cells),365)
            self.assertTrue(all(rect.right()<=width and rect.bottom()<112 for rect,day in c.cells))
            rect,day=next((r,d) for r,d in c.cells if d==date(2026,10,1));selected=[];c.selected.connect(selected.append)
            QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=rect.center().toPoint());self.assertIn('130 tokens',selected[-1])
    def test_empty_partial_and_failure_are_distinct_and_refresh_is_serialized(self):
        jobs=[];panel=SimpleNamespace(owner=self.owner,background=lambda work,callback:jobs.append((work,callback)))
        u=TokenUsage(panel);self.addCleanup(u.deleteLater);u.reload();self.assertEqual(len(jobs),1);self.assertFalse(u.refresh.isEnabled())
        jobs[0][1](({**SUMMARY,'days':[],'total':0,'records':0,'sources':[]},None))
        self.assertIn('No recorded usage yet',u.detail.text());self.assertTrue(u.refresh.isEnabled())
        u.reload();jobs[-1][1](({**SUMMARY,'incomplete':1},None));self.assertIn('Partial history',u.note.text());self.assertEqual(u.calendar.days['2026-10-01']['total'],130)
        u.reload();jobs[-1][1]((None,'Recorded token history is unavailable. Try refreshing.'))
        self.assertEqual(u.total.text(),'Usage unavailable');self.assertIn('unavailable',u.note.text())
    def test_reader_rejects_bad_summary_and_calls_local_helper_without_a_shell(self):
        with patch('augmentor_linux.token_usage.subprocess.run',return_value=SimpleNamespace(stdout=b'{"days":false}')) as run:
            with self.assertRaises(ValueError):read_usage()
            args,kw=run.call_args;self.assertTrue(args[0][-1].endswith('services/usage/history.mjs'));self.assertNotIn('shell',kw);self.assertEqual(kw['timeout'],20)
