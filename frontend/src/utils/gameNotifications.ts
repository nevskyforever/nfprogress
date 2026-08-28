import type { GameCommandResponse } from '@/types/game'

export function gameResponseMessages(
  response: Pick<GameCommandResponse, 'message' | 'messages'>,
): string[] {
  const messages = response.messages.filter(
    (message): message is string => typeof message === 'string' && message.trim().length > 0,
  )
  if (messages.length) return messages

  return response.message && response.message.trim() ? [response.message] : []
}
