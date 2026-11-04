"""Write a parsed Gravitus export into the database (idempotent)."""

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exercises.models import Exercise
from app.exercises.service import find_by_name, upsert_catalog
from app.imports.gravitus.parser import GSet, GTemplate, GWorkout, parse_export
from app.templates.models import TemplateSlot, WorkoutTemplate
from app.workouts.models import Workout, WorkoutExercise, WorkoutSet
from app.workouts.stats import recompute_stats

SOURCE = "gravitus"


@dataclass
class ImportReport:
    """Summary printed by the CLI."""

    workouts_created: int = 0
    workouts_skipped: int = 0
    exercises_created: list[str] = field(default_factory=list)
    templates_created: int = 0


class _ExerciseResolver:
    """Resolves names to exercises, creating unknown ones once."""

    def __init__(self, db: Session, report: ImportReport):
        """Keep a per-import cache of resolved names."""
        self.db, self.report, self.cache = db, report, {}

    def __call__(self, name: str) -> Exercise:
        """Return the exercise for a name, creating it without muscles if unknown."""
        if name not in self.cache:
            exercise = find_by_name(self.db, name)
            if exercise is None:
                exercise = Exercise(name=name, primary_muscles=[])
                self.db.add(exercise)
                self.db.flush()
                self.report.exercises_created.append(name)
            self.cache[name] = exercise
        return self.cache[name]


def _build_workout(g: GWorkout, resolve: _ExerciseResolver) -> Workout:
    """Map a parsed workout to ORM rows: one entry per (group, exercise), sets by set_number."""
    entries: dict[tuple[int, str], list[GSet]] = {}
    for s in sorted(g.sets, key=lambda s: (s.group_number, s.set_number)):
        entries.setdefault((s.group_number, s.exercise), []).append(s)
    workout = Workout(
        started_at=g.started_at,
        ended_at=g.started_at + timedelta(seconds=g.duration_s) if g.duration_s else None,
        title=g.title,
        source=SOURCE,
        external_id=g.external_id,
    )
    for position, ((_, name), sets) in enumerate(entries.items()):
        workout.exercises.append(
            WorkoutExercise(
                position=position,
                exercise=resolve(name),
                sets=[
                    WorkoutSet(
                        set_index=i,
                        weight_kg=s.weight_kg,
                        reps=s.reps,
                        seconds=s.seconds if s.reps is None else None,
                        distance_m=s.distance_m,
                        is_warmup=s.is_warmup,
                    )
                    for i, s in enumerate(sets)
                ],
            )
        )
    return workout


def _build_template(t: GTemplate, resolve: _ExerciseResolver) -> WorkoutTemplate:
    """Template with default 3 x 8-10 targets; multi-exercise groups become supersets."""
    template = WorkoutTemplate(name=t.name)
    position = 0
    for group_number, names in enumerate(t.groups):
        for name in names:
            template.slots.append(
                TemplateSlot(
                    position=position,
                    exercise=resolve(name),
                    sets=3,
                    rep_min=8,
                    rep_max=10,
                    superset_group=group_number if len(names) > 1 else None,
                )
            )
            position += 1
    return template


def import_gravitus(db: Session, text: str) -> ImportReport:
    """Import workouts and templates from a Gravitus export; existing ones are skipped."""
    report = ImportReport()
    upsert_catalog(db)
    resolve = _ExerciseResolver(db, report)
    workouts, templates = parse_export(text)
    existing = set(db.scalars(select(Workout.external_id).where(Workout.source == SOURCE)))
    for g in workouts:
        if g.external_id in existing:
            report.workouts_skipped += 1
            continue
        db.add(_build_workout(g, resolve))
        report.workouts_created += 1
    known_templates = set(db.scalars(select(WorkoutTemplate.name)))
    for t in templates:
        if t.name not in known_templates:
            db.add(_build_template(t, resolve))
            report.templates_created += 1
    db.flush()
    recompute_stats(db)
    db.commit()
    return report
