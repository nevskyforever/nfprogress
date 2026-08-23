import { apiRequest } from './client'
import type {
  BankProductRequest,
  GameCommandResponse,
  GameState,
  InventoryCommand,
  ShopCatalog,
  WritingSessionStart,
} from '@/types/game'

const GAME_PATH = '/api/game'

function command(path: string, body?: unknown, method = 'POST'): Promise<GameCommandResponse> {
  return apiRequest<GameCommandResponse>(`${GAME_PATH}${path}`, { method, body })
}

function awardPath(awardId: string): string {
  return `/custom-awards/${encodeURIComponent(awardId)}`
}

export const gameApi = {
  state(signal?: AbortSignal): Promise<GameState> {
    return apiRequest<GameState>(`${GAME_PATH}/state`, { signal })
  },

  catalog(signal?: AbortSignal): Promise<ShopCatalog> {
    return apiRequest<ShopCatalog>(`${GAME_PATH}/catalog`, { signal })
  },

  startWritingSession(payload: WritingSessionStart): Promise<GameCommandResponse> {
    return command('/writing-sessions/start', payload)
  },

  finishWritingSession(): Promise<GameCommandResponse> {
    return command('/writing-sessions/finish')
  },

  cancelWritingSession(): Promise<GameCommandResponse> {
    return command('/writing-sessions/cancel')
  },

  applyStreakFreeze(
    target: 'global' | 'project',
    projectId?: string,
  ): Promise<GameCommandResponse> {
    return command('/streak-freezes/apply', {
      target,
      ...(projectId ? { project_id: projectId } : {}),
    })
  },

  selectDailyChallenge(optionId: string): Promise<GameCommandResponse> {
    return command('/daily-challenge/select', { option_id: optionId })
  },

  startWeeklyChallenge(challengeId: string): Promise<GameCommandResponse> {
    return command('/weekly-challenge/start', { challenge_id: challengeId })
  },

  activateInspirationAbility(abilityId: string): Promise<GameCommandResponse> {
    return command(`/inspiration-abilities/${encodeURIComponent(abilityId)}/activate`)
  },

  resolveCreativeEvent(choice: 'safe' | 'risk'): Promise<GameCommandResponse> {
    return command('/creative-events/resolve', { choice })
  },

  selectSpecialization(specializationId: string): Promise<GameCommandResponse> {
    return command('/specialization/select', { specialization_id: specializationId })
  },

  activateSpecializationAbility(): Promise<GameCommandResponse> {
    return command('/specialization/ability/activate')
  },

  increaseSkill(skillId: string, points = 1): Promise<GameCommandResponse> {
    return command(`/skills/${encodeURIComponent(skillId)}/increase`, { points })
  },

  startQuest(questId: string): Promise<GameCommandResponse> {
    return command(`/quests/${encodeURIComponent(questId)}/start`)
  },

  abandonQuest(questId: string): Promise<GameCommandResponse> {
    return command(`/quests/${encodeURIComponent(questId)}/abandon`)
  },

  buyItem(payload: InventoryCommand): Promise<GameCommandResponse> {
    return command('/inventory/buy', payload)
  },

  sellItem(payload: InventoryCommand): Promise<GameCommandResponse> {
    return command('/inventory/sell', payload)
  },

  useItem(payload: InventoryCommand): Promise<GameCommandResponse> {
    return command('/inventory/use', payload)
  },

  createCustomAward(name: string, price: number): Promise<GameCommandResponse> {
    return command('/custom-awards', { name, price })
  },

  updateCustomAward(
    awardId: string,
    payload: { name?: string; price?: number },
  ): Promise<GameCommandResponse> {
    return command(awardPath(awardId), payload, 'PATCH')
  },

  deleteCustomAward(awardId: string): Promise<GameCommandResponse> {
    return command(awardPath(awardId), undefined, 'DELETE')
  },

  buyCustomAward(awardId: string, count = 1): Promise<GameCommandResponse> {
    return command(`${awardPath(awardId)}/buy`, { count })
  },

  sellCustomAward(awardId: string, count = 1): Promise<GameCommandResponse> {
    return command(`${awardPath(awardId)}/sell`, { count })
  },

  useCustomAward(awardId: string, count = 1): Promise<GameCommandResponse> {
    return command(`${awardPath(awardId)}/use`, { count })
  },

  previewBankProduct(payload: BankProductRequest): Promise<GameCommandResponse> {
    return command('/bank/preview', payload)
  },

  openBankCredit(amount: number, days: number): Promise<GameCommandResponse> {
    return command('/bank/credit', { amount, days })
  },

  openBankDeposit(
    amount: number,
    days: number,
    allowInterestWithdrawal: boolean,
  ): Promise<GameCommandResponse> {
    return command('/bank/deposit', {
      amount,
      days,
      allow_interest_withdrawal: allowInterestWithdrawal,
    })
  },

  processBankEvents(autoPay = true): Promise<GameCommandResponse> {
    return command('/bank/process', { auto_pay: autoPay })
  },

  makeBankLoanPayment(): Promise<GameCommandResponse> {
    return command('/bank/credit/payment')
  },

  partiallyRepayBankCredit(amount: number): Promise<GameCommandResponse> {
    return command('/bank/credit/partial-repayment', { amount })
  },

  repayBankCredit(): Promise<GameCommandResponse> {
    return command('/bank/credit/repay')
  },

  topUpBankDeposit(amount: number): Promise<GameCommandResponse> {
    return command('/bank/deposit/top-up', { amount })
  },

  withdrawBankDeposit(allowEarly = false): Promise<GameCommandResponse> {
    return command('/bank/deposit/withdraw', { allow_early: allowEarly })
  },

  withdrawBankDepositInterest(): Promise<GameCommandResponse> {
    return command('/bank/deposit/interest/withdraw')
  },
}
