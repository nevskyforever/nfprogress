from types import SimpleNamespace

import engine
from main_UI import MainWindow


def _selection_owner(reference=None):
    return SimpleNamespace(
        _selected_project_reference=reference,
        _is_stage=lambda project: MainWindow._is_stage(None, project),
    )


def test_selected_stage_reference_restores_stage_after_list_rebuild():
    stage = engine.Stage(name='Черновик', goal=1000, parent_project_name='Роман')
    project = engine.Project(name='Роман', goal=1000)
    project.enable_stages = True
    project.stages = [stage]
    data = {'projects': {project.name: project}}

    owner = _selection_owner()
    reference = MainWindow._selection_reference(owner, stage)

    assert reference == {
        'project_name': 'Роман',
        'stage_id': stage.stage_id,
    }

    owner._selected_project_reference = reference
    assert MainWindow._get_saved_selected_project(owner, data) is stage


def test_selected_project_name_remains_compatible_with_existing_settings():
    project = engine.Project(name='Роман', goal=1000)
    owner = _selection_owner('Роман')

    assert MainWindow._get_saved_selected_project(
        owner,
        {'projects': {project.name: project}},
    ) is project
