// Temporary development switch while the custom editor reaches full parity.
// It is intentionally disabled in production until the final switchover.
export const USE_CUSTOM_DOCUMENT_EDITOR = import.meta.env.DEV
  && import.meta.env.VITE_USE_CUSTOM_DOCUMENT_EDITOR === 'true'
