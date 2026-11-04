import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiSend } from './client'
import type {
  HistoryItem,
  HistoryKind,
  ActivityDetail,
  CorosStatus,
  UploadResult,
  BodyweightEntry,
  ExerciseContext,
  ExerciseIn,
  ExerciseOut,
  TemplateIn,
  TemplateOut,
  Today,
  WeekItem,
  WorkoutCreate,
  WorkoutOut,
  WorkoutSummary,
} from './types'

export const PAGE_SIZE = 20

export const useToday = () => useQuery({ queryKey: ['today'], queryFn: () => apiGet<Today>('/today') })

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

/** Fetch logger context for one exercise with the slot's targets. */
export const fetchContext = (exerciseId: number, sets = 3, repMin = 8, repMax = 10) =>
  apiGet<ExerciseContext>(
    `/exercises/${exerciseId}/context?sets=${sets}&rep_min=${repMin}&rep_max=${repMax}`,
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

export const useHistory = (kind: HistoryKind) =>
  useInfiniteQuery({
    queryKey: ['history', kind],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      apiGet<HistoryItem[]>(`/history?kind=${kind}&limit=${PAGE_SIZE}&offset=${pageParam}`),
    getNextPageParam: (last, pages) => (last.length < PAGE_SIZE ? undefined : pages.length * PAGE_SIZE),
  })
