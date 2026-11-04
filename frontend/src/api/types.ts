export type SuggestionKind = 'increase' | 'hold' | 'reduce'
export type Measure = 'reps' | 'time'
export type Block = 'main' | 'finisher'

export interface ExerciseIn {
  name: string
  aliases: string[]
  primary_muscles: string[]
  secondary_muscles: string[]
  measure: Measure
  load_factor: number
  increment_kg: number
  is_bodyweight: boolean
  per_side: boolean
  note: string | null
}

export interface ExerciseOut extends ExerciseIn {
  id: number
  archived: boolean
}

export interface PreviousSet {
  weight_kg: number | null
  reps: number | null
  seconds: number | null
  is_warmup: boolean
}

export interface ExerciseContext {
  exercise: ExerciseOut
  previous: { workout_id: number; started_at: string; sets: PreviousSet[] } | null
  suggestions: { weight_kg: number; reps: number; kind: SuggestionKind }[]
}

export interface SlotIn {
  block: Block
  exercise_id: number
  alternative_exercise_ids: number[]
  warmup_sets: number
  sets: number
  rep_min: number
  rep_max: number
  superset_group: number | null
  note: string | null
}

export interface SlotOut extends SlotIn {
  position: number
  exercise_name: string
  alternatives: { id: number; name: string }[]
}

export interface TemplateIn {
  name: string
  note: string | null
  warmup_items: string[]
  cooldown_items: string[]
  slots: SlotIn[]
}

export interface TemplateOut extends Omit<TemplateIn, 'slots'> {
  id: number
  archived: boolean
  slots: SlotOut[]
}

export interface WeekItem {
  weekday: number
  template_id: number | null
  template_name?: string | null
}

export interface Today {
  date: string
  weekday: number
  template: TemplateOut | null
}

export interface SetIn {
  weight_kg: number | null
  reps: number | null
  seconds: number | null
  is_warmup: boolean
}

export interface WorkoutCreate {
  client_id: string
  started_at: string
  ended_at: string | null
  template_id: number | null
  title: string | null
  note: string | null
  exercises: { exercise_id: number; superset_group: number | null; sets: SetIn[] }[]
}

export interface SetOut extends SetIn {
  set_index: number
  e1rm_kg: number | null
  is_pr: boolean
}

export interface WorkoutOut {
  id: number
  started_at: string
  ended_at: string | null
  template_id: number | null
  title: string | null
  note: string | null
  source: string
  exercises: {
    exercise_id: number
    exercise_name: string
    per_side: boolean
    superset_group: number | null
    sets: SetOut[]
  }[]
}

export interface WorkoutSummary {
  id: number
  started_at: string
  ended_at: string | null
  title: string | null
  template_name: string | null
  exercise_count: number
  set_count: number
  pr_count: number
}

export interface BodyweightEntry {
  day: string
  kg: number
}
