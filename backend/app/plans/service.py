"""Import running plans and resolve which plan applies to a given day."""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.plans.format import parse_plan_yaml
from app.plans.models import PlanSession, PlanWeek, TrainingPlan


def _plan_for(db: Session, day: date) -> TrainingPlan | None:
    """Newest imported plan already in effect on that day."""
    return db.scalar(
        select(TrainingPlan)
        .where(TrainingPlan.effective_from <= day)
        .order_by(TrainingPlan.imported_at.desc(), TrainingPlan.id.desc())
        .limit(1)
    )


def week_of(db: Session, day: date) -> PlanWeek | None:
    """Plan week containing the day, from the plan in effect."""
    plan = _plan_for(db, day)
    if plan is None:
        return None
    return db.scalar(
        select(PlanWeek)
        .where(PlanWeek.plan_id == plan.id, PlanWeek.start <= day)
        .order_by(PlanWeek.start.desc())
        .limit(1)
        .options(selectinload(PlanWeek.sessions))
    )


def sessions_on(db: Session, day: date) -> list[PlanSession]:
    """Planned runs for a day from the plan in effect on that day."""
    plan = _plan_for(db, day)
    if plan is None:
        return []
    return list(
        db.scalars(
            select(PlanSession)
            .where(PlanSession.plan_id == plan.id, PlanSession.date == day)
            .order_by(PlanSession.id)
        )
    )


def _build(plan_file, text: str, effective_from: date) -> TrainingPlan:
    """ORM tree from a validated plan file."""
    plan = TrainingPlan(
        name=plan_file.name,
        goal=plan_file.goal.model_dump(mode="json") if plan_file.goal else None,
        notes=plan_file.notes,
        source_yaml=text,
        imported_at=datetime.now(UTC),
        effective_from=effective_from,
    )
    for w in plan_file.weeks:
        week = PlanWeek(
            week=w.week,
            start=w.start,
            phase=w.phase,
            flags=list(w.flags),
            target_km=w.target_km,
            note=w.note,
            day_notes=[n.model_dump(mode="json") for n in w.day_notes],
        )
        for s in w.sessions:
            week.sessions.append(
                PlanSession(
                    plan=plan,
                    date=s.date,
                    type=s.type,
                    title=s.title,
                    description=s.description,
                    distance_km=s.distance_km,
                    pace_min_s=s.pace.min_s if s.pace else None,
                    pace_max_s=s.pace.max_s if s.pace else None,
                    hr_min=s.hr.min if s.hr else None,
                    hr_max=s.hr.max if s.hr else None,
                    intervals=s.intervals.model_dump(mode="json") if s.intervals else None,
                )
            )
        plan.weeks.append(week)
    return plan


def import_plan(db: Session, text: str, today: date) -> TrainingPlan:
    """Validate and store a plan; it takes over from max(its first week, today).

    The very first plan applies from its first week so past runs can be matched.
    """
    from app.plans.matching import rematch_from

    plan_file = parse_plan_yaml(text)
    first_day = min(w.start for w in plan_file.weeks)
    has_previous = db.scalar(select(TrainingPlan.id).limit(1)) is not None
    effective_from = max(first_day, today) if has_previous else first_day
    plan = _build(plan_file, text, effective_from)
    db.add(plan)
    db.flush()
    # Older plans no longer own days from effective_from on: release their matches.
    superseded = select(PlanSession).where(
        PlanSession.plan_id != plan.id, PlanSession.date >= effective_from
    )
    for session in db.scalars(superseded):
        session.activity_id = None
    db.flush()
    rematch_from(db, effective_from)
    db.commit()
    return plan
