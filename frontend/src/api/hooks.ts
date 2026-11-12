import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiSend } from './client'
import type {
  Records,
  RecoveryState,
  PlanSession,
  Plan,
  Routine,
  TodayFull,
  Video,
  HistoryItem,
  HistoryKind,
  ActivityDetail,
  CorosStatus,
  UploadResult,
  BodyweightEntry,
  ExerciseProgress,
  ExerciseContext,
  ExerciseIn,
  ExerciseOut,
  TemplateIn,
  TemplateOut,
  WeekItem,
  WorkoutCreate,
  WorkoutOut,
  WorkoutSummary,
} from './types'

export const PAGE_SIZE = 20

export const useToday = () => useQuery({ queryKey: ['today'], queryFn: () => apiGet<TodayFull>('/today') })

export const useTemplates = () =>
  useQuery({ queryKey: ['templates'], queryFn: () => apiGet<TemplateOut[]>('/templates') })

export const useTemplate = (id: number | null) =>
  useQuery({
    queryKey: ['templates', id],
    queryFn: () => apiGet<TemplateOut>(`/templates/${id}`),
    enabled: id !== null,
  })

export const useExercises = (includeArchived = false) =>
  useQuery({
    queryKey: ['exercises', includeArchived],
    queryFn: () => apiGet<ExerciseOut[]>(`/exercises?include_archived=${includeArchived}`),
  })

export const useMuscles = () =>
  useQuery({ queryKey: ['muscles'], queryFn: () => apiGet<string[]>('/muscles'), staleTime: Infinity })

export const useWeek = () => useQuery({ queryKey: ['week'], queryFn: () => apiGet<WeekItem[]>('/week') })

export const useExerciseProgress = (id: number, grip: string | null) =>
  useQuery({
    queryKey: ['workouts', 'progress', id, grip],
    queryFn: () =>
      apiGet<ExerciseProgress>(`/exercises/${id}/progress` + (grip ? `?grip=${encodeURIComponent(grip)}` : '')),
    placeholderData: keepPreviousData,
  })

export const useBodyweight = () =>
  useQuery({ queryKey: ['bodyweight'], queryFn: () => apiGet<BodyweightEntry[]>('/bodyweight') })

export const useWorkout = (id: number) =>
  useQuery({ queryKey: ['workouts', id], queryFn: () => apiGet<WorkoutOut>(`/workouts/${id}`) })

export const useWorkouts = () =>
  useInfiniteQuery({
    queryKey: ['workouts', 'list'],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      apiGet<WorkoutSummary[]>(`/workouts?limit=${PAGE_SIZE}&offset=${pageParam}`),
    getNextPageParam: (last, pages) => (last.length < PAGE_SIZE ? undefined : pages.length * PAGE_SIZE),
  })

/** Fetch logger context for one exercise with the slot's targets (grip: last used when omitted). */
export const fetchContext = (exerciseId: number, sets = 3, repMin = 8, repMax = 10, grip?: string | null) =>
  apiGet<ExerciseContext>(
    `/exercises/${exerciseId}/context?sets=${sets}&rep_min=${repMin}&rep_max=${repMax}` +
      (grip ? `&grip=${encodeURIComponent(grip)}` : ''),
  )

/** Mutation helper that invalidates the given query keys on success. */
function useInvalidatingMutation<TVars, TResult>(
  fn: (vars: TVars) => Promise<TResult>,
  keys: string[][],
) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => keys.forEach((queryKey) => client.invalidateQueries({ queryKey })),
  })
}

export const useSaveWorkout = () =>
  useInvalidatingMutation((body: WorkoutCreate) => apiSend<WorkoutOut>('POST', '/workouts', body), [
    ['workouts'],
    ['history'],
  ])

export const useDeleteWorkout = () =>
  useInvalidatingMutation((id: number) => apiSend<void>('DELETE', `/workouts/${id}`), [['workouts'], ['history']])

export const useSaveExercise = () =>
  useInvalidatingMutation(
    ({ id, body }: { id: number | null; body: ExerciseIn }) =>
      id === null
        ? apiSend<ExerciseOut>('POST', '/exercises', body)
        : apiSend<ExerciseOut>('PUT', `/exercises/${id}`, body),
    [['exercises']],
  )

export const useArchiveExercise = () =>
  useInvalidatingMutation((id: number) => apiSend<ExerciseOut>('POST', `/exercises/${id}/archive`), [
    ['exercises'],
  ])

export const useSaveTemplate = () =>
  useInvalidatingMutation(
    ({ id, body }: { id: number | null; body: TemplateIn }) =>
      id === null
        ? apiSend<TemplateOut>('POST', '/templates', body)
        : apiSend<TemplateOut>('PUT', `/templates/${id}`, body),
    [['templates'], ['today'], ['week']],
  )

export const useArchiveTemplate = () =>
  useInvalidatingMutation((id: number) => apiSend<void>('POST', `/templates/${id}/archive`), [
    ['templates'],
    ['today'],
    ['week'],
  ])

export const useSaveWeek = () =>
  useInvalidatingMutation((items: WeekItem[]) => apiSend<WeekItem[]>('PUT', '/week', items), [
    ['week'],
    ['today'],
  ])

export const useSaveBodyweight = () =>
  useInvalidatingMutation(
    ({ day, kg }: { day: string; kg: number }) => apiSend<BodyweightEntry>('PUT', `/bodyweight/${day}`, { kg }),
    [['bodyweight'], ['workouts']],
  )

export const useActivity = (id: number) =>
  useQuery({ queryKey: ['activities', 'detail', id], queryFn: () => apiGet<ActivityDetail>(`/activities/${id}`) })

/** Multipart upload of FIT files (fetch directly: apiSend sends JSON). */
export function useUploadFit() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData()
      files.forEach((f) => form.append('files', f))
      const response = await fetch('/api/activities/upload', { method: 'POST', body: form })
      if (!response.ok) throw new Error(`Upload failed (${response.status})`)
      return (await response.json()) as UploadResult[]
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['activities'] })
      client.invalidateQueries({ queryKey: ['history'] })
    },
  })
}

export const useDeleteActivity = () =>
  useInvalidatingMutation((id: number) => apiSend<void>('DELETE', `/activities/${id}`), [['activities'], ['history']])

export const useCorosStatus = () =>
  useQuery({
    queryKey: ['coros'],
    queryFn: () => apiGet<CorosStatus>('/coros/status'),
    refetchInterval: (q) => (q.state.data?.syncing ? 3000 : false),
  })

export const useCorosConnect = () =>
  useMutation({ mutationFn: () => apiSend<{ authorize_url: string }>('POST', '/coros/connect') })

export const useCorosComplete = () =>
  useInvalidatingMutation((url: string) => apiSend<{ status: string }>('POST', '/coros/complete', { url }), [
    ['coros'],
  ])

export const useCorosSync = () =>
  useInvalidatingMutation(() => apiSend<{ status: string }>('POST', '/coros/sync'), [['coros']])

export const useHistory = (kind: HistoryKind, day: string | null = null) =>
  useInfiniteQuery({
    queryKey: ['history', kind, day],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      apiGet<HistoryItem[]>(
        `/history?kind=${kind}&limit=${PAGE_SIZE}&offset=${pageParam}${day ? `&day=${day}` : ''}`,
      ),
    getNextPageParam: (last, pages) => (last.length < PAGE_SIZE ? undefined : pages.length * PAGE_SIZE),
  })

export const useCalendar = (month: string) =>
  useQuery({
    queryKey: ['history', 'calendar', month],
    queryFn: () => apiGet<{ day: string; kinds: string[] }[]>(`/history/calendar?month=${month}`),
  })

export const useActivePlan = () =>
  useQuery({ queryKey: ['plan'], queryFn: () => apiGet<Plan | null>('/plans/active') })

export const usePlanInstructions = () =>
  useQuery({ queryKey: ['plan', 'instructions'], queryFn: () => apiGet<{ text: string }>('/plans/instructions'), staleTime: Infinity })

/** POST raw YAML (text/plain) so the backend reads the body as-is. */
export function useImportPlan() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (yamlText: string) => {
      const response = await fetch('/api/plans/import', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: yamlText,
      })
      const data = await response.json()
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Import failed')
      return data as { name: string; weeks: number; sessions: number; effective_from: string }
    },
    onSuccess: () => ['plan', 'today', 'history', 'activities'].forEach((k) => client.invalidateQueries({ queryKey: [k] })),
  })
}

export const useLinkSession = () =>
  useInvalidatingMutation(
    ({ sessionId, activityId }: { sessionId: number; activityId: number | null }) =>
      apiSend('POST', `/plans/sessions/${sessionId}/link`, { activity_id: activityId }),
    [['plan'], ['activities'], ['today'], ['history']],
  )

export const useVideos = () => useQuery({ queryKey: ['videos'], queryFn: () => apiGet<Video[]>('/videos') })

export const useAddVideo = () =>
  useInvalidatingMutation((url: string) => apiSend<Video>('POST', '/videos', { url }), [['videos']])

export const useDeleteVideo = () =>
  useInvalidatingMutation((id: number) => apiSend<void>('DELETE', `/videos/${id}`), [['videos'], ['routines']])

export const useRoutines = () => useQuery({ queryKey: ['routines'], queryFn: () => apiGet<Routine[]>('/routines') })

export const useSaveRoutine = () =>
  useInvalidatingMutation(
    ({ id, body }: { id: number | null; body: { name: string; note: string | null; video_ids: number[] } }) =>
      id === null ? apiSend<Routine>('POST', '/routines', body) : apiSend<Routine>('PUT', `/routines/${id}`, body),
    [['routines'], ['today']],
  )

export const useArchiveRoutine = () =>
  useInvalidatingMutation((id: number) => apiSend<void>('POST', `/routines/${id}/archive`), [['routines'], ['today']])

export const useRoutineWeek = () =>
  useQuery({
    queryKey: ['routines', 'week'],
    queryFn: () => apiGet<{ weekday: number; routine_ids: number[] }[]>('/routines/week'),
  })

export const useSaveRoutineWeek = () =>
  useInvalidatingMutation(
    (items: { weekday: number; routine_ids: number[] }[]) => apiSend('PUT', '/routines/week', items),
    [['routines'], ['today']],
  )

export const useToggleRoutineDone = () =>
  useInvalidatingMutation(
    ({ routineId, day, done }: { routineId: number; day: string; done: boolean }) =>
      apiSend<void>(done ? 'PUT' : 'DELETE', `/routines/${routineId}/done/${day}`),
    [['today']],
  )

export const useSessionsBetween = (start: string, end: string, enabled = true) =>
  useQuery({
    queryKey: ['plan', 'sessions', start, end],
    queryFn: () => apiGet<PlanSession[]>(`/plans/sessions?start=${start}&end=${end}`),
    enabled,
  })

export const useRoutineDone = (day: string | undefined) =>
  useQuery({
    queryKey: ['today', 'routine-done', day],
    queryFn: () => apiGet<number[]>(`/routines/done?day=${day}`),
    enabled: !!day,
  })

export const useRecovery = () =>
  useQuery({ queryKey: ['recovery'], queryFn: () => apiGet<RecoveryState>('/recovery') })

export const useRecords = () => useQuery({ queryKey: ['records'], queryFn: () => apiGet<Records>('/records') })
