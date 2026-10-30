import { emit, listen, type UnlistenFn } from '@tauri-apps/api/event'

const EVENT = 'nfprogress-local-note-write'

/** Only the native local writer publishes this event, after its command succeeds. */
export function announceLocalNoteWrite(projectId: string): void {
  void Promise.resolve().then(() => emit(EVENT, projectId)).catch(() => {
    // A notification failure must not turn a committed local write into a failure.
  })
}

export function onLocalNoteWrite(listener: (projectId: string) => void): Promise<UnlistenFn> {
  return listen<unknown>(EVENT, event => {
    if (typeof event.payload === 'string' && event.payload) listener(event.payload)
  })
}
