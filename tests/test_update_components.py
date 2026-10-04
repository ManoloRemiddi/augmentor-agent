# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Real consent/source files at every boundary; fixture bytes are never executed."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))
from updates import components
from updates.manager import UpdateManager
from platform_adapters.private_files import atomic_json
import test_update_installation as _fixture


class ComponentConsentTests(unittest.TestCase):
    def setUp(self):
        self.f=_fixture.InstallationAuthorityTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def change_dsh(self):
        self.f.release['updateComponents']['dsh']['sha256']='f'*64
        self.f.save()

    def test_disabled_bundled_component_blocks_even_same_version_changed_bytes(self):
        self.change_dsh()
        with self.assertRaisesRegex(ValueError,'DSH.*turned off'):self.f.authority().__enter__()
        self.assertEqual(self.f.calls,0)

    def test_selected_compatible_bundled_change_is_allowed_with_live_authority(self):
        self.change_dsh();self.f.state['preferences']['components']['dsh']=True;self.f.save()
        with self.f.authority() as guard:self.assertTrue(guard.check('prepared'))

    def test_revocation_during_network_refresh_refuses_before_installation(self):
        self.change_dsh();self.f.state['preferences']['components']['dsh']=True;self.f.save()
        with self.f.authority() as guard:
            def revoke():
                result=self.f.repository()
                self.f.state['preferences']['components']['dsh']=False;self.f.save()
                return result
            guard.repository=revoke
            with self.assertRaisesRegex(ValueError,'DSH.*turned off'):guard.check('installer-ready')

    def test_augmentor_off_and_legacy_consent_never_authorize_bundle(self):
        self.f.state['preferences']['components']['augmentor']=False;self.f.save()
        with self.assertRaisesRegex(ValueError,'Augmentor Agent.*turned off'):self.f.authority().__enter__()
        self.f.state['preferences'].pop('components');self.f.save()
        with self.assertRaises(ValueError):self.f.authority().__enter__()

    def test_external_codex_cannot_be_replaced_by_application_controller(self):
        self.f.state['preferences']['components']['codex']=True
        self.f.release['updateComponents']['codex']['version']='2.0.0';self.f.save()
        with self.assertRaisesRegex(ValueError,'separately verified Codex'):self.f.authority().__enter__()

    def test_changed_source_contract_and_misdeclared_staged_target_refuse(self):
        with self.f.authority() as guard:
            self.f.component_contract['pi']['sha256']='f'*64
            (self.f.root/'release/update-components.json').write_text(json.dumps(
                {'schema':components.SCHEMA,'components':self.f.component_contract}))
            with self.assertRaisesRegex(ValueError,'installed harness identities changed'):guard.check('prepared')
        with self.assertRaisesRegex(ValueError,'staged harness identities differ'):
            components.verify_target(self.f.root,self.f.release)

    def test_legacy_preferences_migrate_without_inheriting_bundle_wide_install_consent(self):
        self.f.state['preferences'].pop('components');self.f.save()
        # Test only the settings migration, with a valid fresh manager state.
        m=UpdateManager(self.f.base/'manager',root=self.f.root);self.addCleanup(m.close)
        state=deepcopy(m.state);state['preferences'].pop('components')
        state['preferences'].update(automaticDownload=True,automaticInstall=True)
        atomic_json(m.file,state)
        newer=UpdateManager(m.base,root=m.root);self.addCleanup(newer.close)
        self.assertFalse(newer.state['preferences']['automaticInstall'])
        self.assertEqual(newer.state['preferences']['components'],components.defaults())
        choices={key:True for key in components.NAMES}
        prefs=deepcopy(newer.state['preferences']);prefs['components']=choices
        newer.configure({'revision':newer.state['revision'],'preferences':prefs})
        legacy=deepcopy(newer.state['preferences']);legacy.pop('components')
        newer.configure({'revision':newer.state['revision'],'preferences':legacy})
        self.assertEqual(newer.state['preferences']['components'],choices)

    def test_unknown_or_non_boolean_component_choices_and_incomplete_identity_refuse(self):
        for value in ({**components.defaults(),'claude':True},{**components.defaults(),'pi':'true'},{}):
            with self.subTest(value=value),self.assertRaises(ValueError):components.validate_choices(value)
        for value in ({},self.f.component_contract|{'dsh':{'version':'1.0.0','sha256':'a'*64,'ownership':'external'}}):
            with self.subTest(value=value),self.assertRaises(ValueError):components.validate_contract(value)

    def test_actual_reviewed_build_contract_has_bundled_pi_dsh_and_external_codex(self):
        contract=components.build_contract(ROOT)
        self.assertEqual(set(contract),{'pi','dsh','codex'})
        self.assertEqual(contract['codex']['ownership'],'external')
        self.assertEqual(contract['pi']['ownership'],'bundled')
        self.assertEqual(contract,components.build_contract(ROOT))


if __name__=='__main__':unittest.main()
