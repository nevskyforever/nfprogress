export type DataChangeScope = 'projects' | 'game'

const EVENT_NAME = 'nfprogress:data-changed'

export function announceDataChange(scope: DataChangeScope): void {
  window.dispatchEvent(new CustomEvent<DataChangeScope>(EVENT_NAME, { detail: scope }))
}

export function onDataChange(listener: (scope: DataChangeScope) => void): () => void {
  const handler = (event: Event) => listener((event as CustomEvent<DataChangeScope>).detail)
  window.addEventListener(EVENT_NAME, handler)
  return () => window.removeEventListener(EVENT_NAME, handler)
}
