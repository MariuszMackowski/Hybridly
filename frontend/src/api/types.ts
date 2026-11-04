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
  suggestions: { weight_kg: number; reps: number; kind: SuggestionKind; reason?: string | null }[]
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

export interface ActivitySummary {
  id: number
  source: 'coros' | 'upload'
  sport: string
  name: string | null
  started_at: string
  duration_s: number
  distance_m: number | null
  avg_hr: number | null
  avg_speed: number | null
  training_load: number | null
  avg_pace_s_per_km: number | null
}

export interface ActivityLap {
  index: number
  start_offset_s: number
  duration_s: number
  distance_m: number | null
  avg_hr: number | null
  max_hr: number | null
  avg_speed: number | null
  avg_cadence_spm: number | null
  avg_power_w: number | null
  avg_stride_m: number | null
}

export interface ActivityStreams {
  t: number[]
  hr?: (number | null)[]
  speed?: (number | null)[]
  alt?: (number | null)[]
  lat?: (number | null)[]
  lon?: (number | null)[]
  cad?: (number | null)[]
  stride?: (number | null)[]
  power?: (number | null)[]
  gct?: (number | null)[]
  vo?: (number | null)[]
  vr?: (number | null)[]
}

export interface ActivityDetail extends ActivitySummary {
  sport_type: number | null
  external_id: string | null
  max_hr: number | null
  ascent_m: number | null
  calories: number | null
  avg_cadence_spm: number | null
  avg_stride_m: number | null
  avg_power_w: number | null
  avg_gct_ms: number | null
  avg_vo_cm: number | null
  avg_vr_pct: number | null
  aerobic_te: number | null
  anaerobic_te: number | null
  laps: ActivityLap[]
  streams: ActivityStreams
  plan: PlanSession | null
}

export interface UploadResult {
  filename: string
  status: 'created' | 'duplicate' | 'error'
  id: number | null
  detail: string | null
}

export interface CorosStatus {
  status: 'disconnected' | 'connected' | 'needs_reconnect'
  syncing: boolean
  last_sync_at: string | null
  last_sync_status: {
    imported?: number
    skipped_existing?: number
    skipped_strength?: number
    deferred?: number
    unparsable?: number
    errors?: string[]
  } | null
  redirect_uri: string
}

export type HistoryKind = 'all' | 'gym' | 'run' | 'walk' | 'other'

export interface HistoryItem {
  kind: 'workout' | 'activity'
  id: number
  started_at: string
  title: string | null
  sport: string
  duration_s: number | null
  distance_m: number | null
  avg_pace_s_per_km: number | null
  avg_speed: number | null
  avg_hr: number | null
  training_load: number | null
  exercise_count: number | null
  set_count: number | null
  pr_count: number | null
}

export interface Comparison {
  distance_pct: number | null
  pace_s: number | null
  pace_status: 'in' | 'faster' | 'slower' | null
  hr_below_pct: number | null
  hr_in_pct: number | null
  hr_above_pct: number | null
  interval_laps: { index: number; distance_m: number; pace_s: number; in_range: boolean | null }[]
}

export interface PlanSession {
  id: number
  date: string
  type: string
  title: string
  description: string
  distance_km: number | null
  pace_min_s: number | null
  pace_max_s: number | null
  hr_min: number | null
  hr_max: number | null
  intervals: { reps: number; distance_m?: number; pace?: { min: string; max: string }; recovery?: string } | null
  activity_id: number | null
  comparison: Comparison | null
}

export interface PlanWeek {
  week: number
  start: string
  phase: string | null
  flags: string[]
  target_km: number | null
  note: string | null
  day_notes: { date: string; text: string }[]
  sessions: PlanSession[]
}

export interface Plan {
  id: number
  name: string
  goal: { race?: string; date?: string; target_time?: string } | null
  notes: string[]
  effective_from: string
  weeks: PlanWeek[]
}

export interface Video {
  id: number
  url: string
  youtube_id: string | null
  title: string
  thumbnail_url: string | null
  note: string | null
}

export interface Routine {
  id: number
  name: string
  note: string | null
  video_ids: number[]
  videos: Video[]
}

export interface TodayFull extends Today {
  runs: PlanSession[]
  week: { week: number; phase: string | null; flags: string[]; target_km: number | null; done_km: number } | null
  day_notes: string[]
  routines: { routine: Routine; done: boolean }[]
  recovery: { recovery_pct?: number; level?: string; full_recovery_h?: number } | null
  strength_hint: string | null
}

export interface RecoveryState {
  recovery_pct: number
  hours_to_full: number
  acute: number
  capacity: number
  coros_pct: number | null
  muscles: Record<string, number>
  regions: { region: string; recovery_pct: number; hours_to_ready: number }[]
  daily: { day: string; strength: number; cardio: number }[]
}
