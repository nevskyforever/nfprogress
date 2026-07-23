import datetime

import engine
import game
import game_data


def disable_persistence(monkeypatch):
    monkeypatch.setattr(game.Gamer, 'save', lambda self: None)
    monkeypatch.setattr(game.engine, 'load_data', lambda: {})
    monkeypatch.setattr(game.engine, 'save_data', lambda data: None)


def test_stage_completion_bonus_is_reduced(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=1)

    gamer.give_complete_bonus(
        'завершен',
        1000,
        'stage:Book:stage-id',
        game_data.STAGE_COMPLETION_BONUS_MULTIPLIER,
    )

    assert gamer.coins == 50
    assert gamer.exp == 5000


def test_project_completion_bonus_remains_full(monkeypatch):
    disable_persistence(monkeypatch)
    gamer = game.Gamer(level=1)

    gamer.give_complete_bonus('завершен', 1000, 'Book')

    assert gamer.coins == 200
    assert gamer.exp == 20000


def test_completing_parent_includes_only_unfinished_stages():
    completed_stage = engine.Stage(name='Draft', goal=100, status='завершен')
    active_stage = engine.Stage(name='Edit', goal=100)
    project = engine.Project(name='Book', goal=200)
    project.enable_stages = True
    project.stages = [completed_stage, active_stage]

    entities = engine.get_completion_entities(project)
    completion_date = datetime.date(2026, 7, 22)
    for entity in entities:
        entity.status = 'завершен'
        entity.complete_date = completion_date

    assert entities == [active_stage, project]
    assert completed_stage.complete_date is None
    assert active_stage.complete_date == completion_date
    assert project.complete_date == completion_date


def test_completing_stage_does_not_include_parent_or_siblings():
    stage = engine.Stage(name='Draft', goal=100)

    assert engine.get_completion_entities(stage) == [stage]
