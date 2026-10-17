# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Connect the recovered settings view to current public Native host controls."""


def bind_appearance(owner,dialog):
    dialog.changed.connect(owner.apply_appearance)
    publish=getattr(owner,'publish_dictation_appearance',None)
    if publish is not None:dialog.changed.connect(publish)


def scrolled_editor(dialog):
    from .surfaces import AppearanceDialog
    from .dictation_settings import DictationSettingsDialog
    return isinstance(dialog,(AppearanceDialog,DictationSettingsDialog))


def quit_owner(panel):
    owner=panel.owner
    if panel.accept():owner.quit_augmentor()


def add_host_actions(panel,layout):
    from .dictation_settings import DictationSettingsDialog
    def dictation():
        panel.open_editor('Voice dictation · Handy',lambda:DictationSettingsDialog(panel.owner))
    panel.action(layout,'Voice dictation · Powered by Handy    ›',dictation)
    controller=panel.owner.controller
    if getattr(controller,'harness',None)=='pi':
        panel.inspector_action=panel.action(layout,'Trajectory && Context    ›',panel.owner.open_inspector)
        from .reasoning_settings import ReasoningDialog
        from .mcp_settings import McpDialog
        panel.pi_settings_actions={}
        for title,capability,dialog in [('Reasoning','reasoning',ReasoningDialog),('MCP servers','mcpManagement',McpDialog)]:
            def open_dialog(_=False,title=title,dialog=dialog):
                panel.open_editor(title,lambda:dialog(panel.owner))
            panel.pi_settings_actions[capability]=panel.action(layout,title+'    ›',open_dialog)
        refresh_host_actions(panel)


def refresh_host_actions(panel):
    button=getattr(panel,'inspector_action',None)
    if button is None:return
    controller=panel.owner.controller
    caps=getattr(controller,'capabilities',{})
    is_pi=getattr(controller,'harness',None)=='pi'
    button.setEnabled(bool(is_pi and controller.session and controller.online and caps.get('inspection')))
    for capability,action in getattr(panel,'pi_settings_actions',{}).items():
        action.setEnabled(bool(is_pi and caps.get(capability) is True))
