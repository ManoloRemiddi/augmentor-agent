# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Signed image, target identity and backing-file guards before private boot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('gnome_vm_prepare',Path(__file__).resolve().parents[1]/'scripts/prepare-gnome-vm.py')
vm=importlib.util.module_from_spec(spec);spec.loader.exec_module(vm)


class GnomeVmPreparation(unittest.TestCase):
    def test_detached_checksum_requires_exact_unique_pinned_filename(self):
        manifest={'signature':'official.gpg','sha256':'a'*64}
        line='a'*64+' *ubuntu.img\n'
        self.assertTrue(vm.checksum_matches(manifest,'ubuntu.img',line))
        self.assertTrue(vm.checksum_matches(manifest,'ubuntu.img',line.replace('*','')))
        for text in (line+line,line.replace('ubuntu.img','other.img'),line.replace('a','b'),line.replace('*','../')):
            with self.subTest(text=text):self.assertFalse(vm.checksum_matches(manifest,'ubuntu.img',text))
        self.assertTrue(vm.checksum_matches({'sha256':'a'*64},'fedora.img','SHA256 (fedora.img) = '+'a'*64))

    def test_different_fixture_identity_refuses_before_download_or_boot(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(vm,'ROOT',Path(temp)),patch.object(vm.os,'geteuid',return_value=1000),patch.object(vm,'run') as run:
            root=Path(temp)/'outputs/guest';root.mkdir(parents=True)
            (root/'infrastructure.json').write_text(json.dumps({'base':{'target':'fedora44'}}))
            with self.assertRaisesRegex(ValueError,'different pinned guest'):vm.prepare(root,{'target':'ubuntu24'},22490,True)
            run.assert_not_called()

    def prepare_fixture(self,root):
        root.mkdir(parents=True);image=b'known image bytes';digest=hashlib.sha256(image).hexdigest()
        manifest={'image':'https://example.test/ubuntu.img','checksum':'https://example.test/SHA256SUMS',
                  'signature':'https://example.test/SHA256SUMS.gpg','keyring':'https://example.test/key.gpg',
                  'keyringFile':'key.gpg','signingFingerprint':'A'*40,'sha256':digest,'imageBytes':len(image)}
        for name,content in [('ubuntu.img',image),('SHA256SUMS',(digest+' *ubuntu.img\n').encode()),
                             ('SHA256SUMS.gpg',b'signature'),('key.gpg',b'key'),('guest.qcow2',b'overlay')]:
            (root/name).write_bytes(content)
        return manifest

    def test_wrong_signer_and_wrong_image_bytes_refuse_before_overlay_or_boot(self):
        for corruption in ('signer','image'):
            with tempfile.TemporaryDirectory() as temp,patch.object(vm,'ROOT',Path(temp)),patch.object(vm.os,'geteuid',return_value=1000):
                root=Path(temp)/'outputs/guest';manifest=self.prepare_fixture(root)
                if corruption=='image':(root/'ubuntu.img').write_bytes(b'corrupt')
                status='[GNUPG:] VALIDSIG '+('B'*40 if corruption=='signer' else 'A'*40)+' details'
                with patch.object(vm,'run',return_value=status) as run,self.assertRaisesRegex(ValueError,'signer|Base image'):
                    vm.prepare(root,manifest,22490,True)
                self.assertEqual(len(run.call_args_list),1);self.assertEqual(run.call_args.args[0][0],'gpgv')
                self.assertFalse((root/'infrastructure.json').exists())

    def test_wrong_overlay_backing_image_refuses_before_identity_or_boot(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(vm,'ROOT',Path(temp)),patch.object(vm.os,'geteuid',return_value=1000):
            root=Path(temp)/'outputs/guest';manifest=self.prepare_fixture(root)
            with patch.object(vm,'run',side_effect=['[GNUPG:] VALIDSIG '+'A'*40+' details',json.dumps({'format':'qcow2','full-backing-filename':'/different/image'})]) as run,\
                 self.assertRaisesRegex(ValueError,'overlay'):
                vm.prepare(root,manifest,22490,True)
            self.assertEqual(len(run.call_args_list),2);self.assertFalse((root/'id_ed25519').exists())


if __name__=='__main__':unittest.main()
