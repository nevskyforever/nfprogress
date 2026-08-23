export const NOTE_COLORS = [
  { value: 'default', label: 'По умолчанию' },
  { value: 'coral', label: 'Коралловый' },
  { value: 'orange', label: 'Оранжевый' },
  { value: 'yellow', label: 'Жёлтый' },
  { value: 'green', label: 'Зелёный' },
  { value: 'teal', label: 'Бирюзовый' },
  { value: 'blue', label: 'Синий' },
  { value: 'purple', label: 'Фиолетовый' },
  { value: 'pink', label: 'Розовый' },
  { value: 'brown', label: 'Коричневый' },
  { value: 'gray', label: 'Серый' },
] as const

export type NoteColor = (typeof NOTE_COLORS)[number]['value']
