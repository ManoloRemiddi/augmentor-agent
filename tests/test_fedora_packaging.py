# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Wrong distro/ABI must refuse before the RPM maintenance hook writes state."""
import importlib.util
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fedora_packaging',ROOT/'scripts/package-fedora.py')
fedora=importlib.util.module_from_spec(spec);spec.loader.exec_module(fedora)


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux RPM maintainer hooks')
class FedoraPackagingTests(unittest.TestCase):
    def test_wrong_distro_release_and_architecture_refuse_before_state_creation(self):
        for target in ('43','44'):
            source=re.findall(r"/usr/bin/python3 -I <<'AUGMENTOR_HOOK'\n(.*?)\nAUGMENTOR_HOOK",fedora.guard('0.2.13',target),re.S)
            self.assertEqual(len(source),2)
            for hook in source:
                for release,machine in [('ID=opensuse-leap\nVERSION_ID=16.0\n','x86_64'),
                                        ('ID=linuxmint\nVERSION_ID=22.3\nID_LIKE=fedora\n','x86_64'),
                                        ('ID=fedora\nVERSION_ID='+('44' if target=='43' else '43')+'\n','x86_64'),
                                        ('ID=fedora\nVERSION_ID='+target+'\n','aarch64')]:
                    with self.subTest(target=target,release=release,machine=machine),\
                         patch.object(Path,'read_text',return_value=release),\
                         patch.object(Path,'mkdir') as mkdir,\
                         patch('platform.machine',return_value=machine),patch('sys.argv',['rpm-pre']):
                        with self.assertRaisesRegex(SystemExit,'requires Fedora '+target):
                            exec(compile(hook,'rpm-pre','exec'),{})
                        mkdir.assert_not_called()

    def test_unreviewed_fedora_release_cannot_generate_a_hook(self):
        with self.assertRaisesRegex(ValueError,'explicit Fedora'):
            fedora.guard('0.2.13','45')

    def test_old_target_can_be_removed_after_distro_upgrade_without_install_admission(self):
        source=re.findall(r"/usr/bin/python3 -I <<'AUGMENTOR_HOOK'\n(.*?)\nAUGMENTOR_HOOK",fedora.guard('0.2.13','43',removal=True),re.S)
        for hook in source:
            with patch.object(Path,'read_text',return_value='ID=fedora\nVERSION_ID=44\n'),\
                 patch.object(Path,'mkdir',side_effect=RuntimeError('Synthetic root state boundary')) as mkdir,\
                 patch('platform.machine',return_value='x86_64'),patch('sys.argv',['rpm-preun']):
                with self.assertRaisesRegex(RuntimeError,'Synthetic root state boundary'):
                    exec(compile(hook,'rpm-preun','exec'),{})
                mkdir.assert_called_once()


if __name__=='__main__':unittest.main()
