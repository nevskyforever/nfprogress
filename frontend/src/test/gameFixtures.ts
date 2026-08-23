import type { GameState } from '@/types/game'

export function gameStateFixture(overrides: Partial<GameState> = {}): GameState {
  const state: GameState = {
    enabled: true,
    server_time: '2026-08-15T12:00:00',
    profile: {
      level: 3,
      experience: 250,
      next_level_experience: 1_000,
      coins: 2_000,
      inflation: 1,
      health: 80,
      max_health: 100,
      inspiration: 50,
      max_inspiration: 100,
      writing_session_streak: 4,
      session_streak_shields: 1,
      session_grade_boosts: 0,
      pending_bonuses: { writing: 0, session: 0, challenge: 0, manuscript: 0 },
    },
    skills: {
      available_points: 2,
      points_per_level: 2,
      items: [
        { key: 'productivity', name: 'Продуктивность', points: 1, target: 'exp', bonus: 0.05 },
      ],
      coefficients: [],
    },
    buffs: { server_time: '2026-08-15T12:00:00', positive: [], negative: [] },
    notifications: { unread: [], read: [], unread_count: 0 },
    streak_freezes: {
      date: '2026-08-15',
      inventory_count: 2,
      global_available: true,
      projects: [
        {
          project_id: 'project-id',
          name: 'Дом у моря',
          source_count: 2,
          max_streak: 8,
          sources: [
            { id: 'project-id', name: 'Дом у моря', is_stage: false, streak_length: 8 },
            { id: 'stage-id', name: 'Черновик', is_stage: true, streak_length: 3 },
          ],
        },
      ],
    },
    inventory: { categories: [{ key: 'Зелья', name: 'Зелья', items: [] }] },
    quests: { items: [], by_status: { available: [], active: [], completed: [] } },
    daily_challenge: {
      change_cost: 15,
      current: {
        option_id: 'symbols:normal',
        date: '2026-08-15',
        type: 'symbols',
        name: 'Объём дня',
        description: 'Написать выбранный объём текста за день.',
        difficulty: 'normal',
        difficulty_name: 'Обычно',
        target: 1_000,
        progress: 250,
        completed: false,
        reward: { coins: 100, experience: 300, inspiration: 10 },
      },
      options: [],
      history: [],
    },
    weekly_challenge: {
      current: null,
      catalog: [
        {
          key: 'symbols',
          name: 'Марафон',
          description: 'Написать 10 000 символов за неделю.',
          target: 10_000,
          reward: { coins: 500, experience: 1_500, inspiration: 20 },
        },
      ],
    },
    writing_session: {
      server_time: '2026-08-15T12:00:00',
      active: null,
      streak: 4,
      history: [],
      modes: [
        {
          key: 'sprint',
          name: 'Спринт',
          description: 'Быстрый результат.',
          reward_bonus: 0.15,
        },
        {
          key: 'flow',
          name: 'Поток',
          description: 'Сбалансированный режим.',
          reward_bonus: 0,
        },
        {
          key: 'deep',
          name: 'Глубокая работа',
          description: 'Длительная концентрация.',
          reward_bonus: 0.25,
        },
        {
          key: 'editing',
          name: 'Редакторский проход',
          description: 'Учитывает отредактированные символы.',
          reward_bonus: 0.2,
        },
      ],
      grades: [
        { key: 'bronze', name: 'Бронза', target_ratio: 1, reward_multiplier: 1 },
      ],
      allowed_durations_minutes: [15, 25, 45, 60],
    },
    inspiration: { abilities: [], creative_event: null, creative_event_history: [] },
    specializations: {
      selected: null,
      unlocks_at_level: 5,
      change_cooldown_days: 7,
      change_days_remaining: 0,
      mastery_thresholds: [0, 100],
      items: [],
    },
    manuscripts: { journeys: [], milestones: [], cabinet: { relics: [], sets: [] } },
    bank: {
      credit_score: 500,
      credit_limit: 1_000,
      max_credit_days: 30,
      credit_rate: 3,
      deposit_rate: 1,
      can_open_credit: true,
      can_open_deposit: true,
      credit: null,
      deposit: null,
    },
    custom_awards: { items: [] },
    shop: {
      categories: [{ key: 'Зелья', name: 'Зелья', items: [] }],
      custom_awards: { items: [] },
    },
  }
  return { ...state, ...overrides }
}
