# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Never let fixture provisioning modify an owner or an unrelated guest."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('noble_gnome_provision',Path(__file__).resolve().parents[1]/'release/provision-noble-gnome-vm.py')
guest=importlib.util.module_from_spec(spec);spec.loader.exec_module(guest)


class NobleGuestGuard(unittest.TestCase):
    def test_only_exact_marked_guest_and_dedicated_ordinary_user_pass(self):
        valid=({'ID':'ubuntu','VERSION_ID':'24.04'},guest.MARKER,1000,'augmentor-proof','qemu')
        guest.validate_guest(*valid)
        cases=[(0,{'ID':'linuxmint','VERSION_ID':'22.3','ID_LIKE':'ubuntu'}),
               (0,{'ID':'ubuntu','VERSION_ID':'26.04'}),(1,''),(1,guest.MARKER.rstrip()),
               (2,0),(3,'owner'),(4,'none'),(4,'docker')]
        for index,value in cases:
            candidate=list(valid);candidate[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):guest.validate_guest(*candidate)


if __name__=='__main__':unittest.main()
