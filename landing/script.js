(() => {
  const root = document.documentElement
  const themeButton = document.querySelector('.theme-toggle')
  const menuButton = document.querySelector('.menu-toggle')
  const navigation = document.querySelector('#primary-nav')
  const accessNote = document.querySelector('#access-note')
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

  function readTheme() {
    try {
      const saved = window.localStorage.getItem('worta-landing-theme')
      return saved === 'light' || saved === 'dark' ? saved : null
    } catch {
      return null
    }
  }

  function updateThemeButton(theme) {
    if (!themeButton) return
    const nextTheme = theme === 'dark' ? 'light' : 'dark'
    themeButton.setAttribute('aria-label', `Включить ${nextTheme === 'dark' ? 'тёмную' : 'светлую'} тему`)
    themeButton.querySelector('.theme-icon').textContent = theme === 'dark' ? '☼' : '◐'
  }

  const savedTheme = readTheme()
  if (savedTheme) root.dataset.theme = savedTheme
  updateThemeButton(savedTheme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))

  themeButton?.addEventListener('click', () => {
    const current = root.dataset.theme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    const next = current === 'dark' ? 'light' : 'dark'
    root.dataset.theme = next
    try {
      window.localStorage.setItem('worta-landing-theme', next)
    } catch {
      // Theme selection still works for this page view.
    }
    updateThemeButton(next)
  })

  document.body.classList.add('js-enabled')
  if (menuButton && navigation) {
    menuButton.hidden = false
    menuButton.addEventListener('click', () => {
      const isOpen = menuButton.getAttribute('aria-expanded') === 'true'
      menuButton.setAttribute('aria-expanded', String(!isOpen))
      menuButton.querySelector('.visually-hidden').textContent = isOpen ? 'Открыть меню' : 'Закрыть меню'
      navigation.classList.toggle('menu-open', !isOpen)
    })

    navigation.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        navigation.classList.remove('menu-open')
        menuButton.setAttribute('aria-expanded', 'false')
        menuButton.querySelector('.visually-hidden').textContent = 'Открыть меню'
      })
    })

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
        navigation.classList.remove('menu-open')
        menuButton.setAttribute('aria-expanded', 'false')
        menuButton.querySelector('.visually-hidden').textContent = 'Открыть меню'
        menuButton.focus()
      }
    })
  }

  document.querySelectorAll('.access-action').forEach((button) => {
    button.addEventListener('click', () => {
      accessNote.textContent = button.dataset.access === 'register'
        ? 'Регистрация пока закрыта. Объявление о запуске появится здесь.'
        : 'Вход пока закрыт. Доступ откроется после запуска веб-версии.'
      document.querySelector('#availability-title')?.focus({ preventScroll: true })
      document.querySelector('#availability')?.scrollIntoView({ behavior: reducedMotion.matches ? 'auto' : 'smooth' })
      navigation?.classList.remove('menu-open')
      menuButton?.setAttribute('aria-expanded', 'false')
    })
  })

  const downloadNote = document.querySelector('#download-note')
  const supportedPlatforms = new Set(['windows', 'macos-arm', 'macos-intel'])
  const allowedDownloadHosts = new Set(['github.com', 'nfproject.ru', 'worta.ru', 'www.worta.ru'])

  function validRelease(release) {
    if (!release || typeof release !== 'object') return false
    if (!supportedPlatforms.has(release.platform)) return false
    if (typeof release.version !== 'string' || !/^\d+\.\d+\.\d+(?:[-+][\da-z.-]+)?$/i.test(release.version)) return false
    if (typeof release.url !== 'string') return false

    try {
      const url = new URL(release.url)
      return url.protocol === 'https:' && !url.username && !url.password && allowedDownloadHosts.has(url.hostname)
    } catch {
      return false
    }
  }

  async function loadDesktopReleases() {
    if (!downloadNote) return

    try {
      const response = await fetch('releases.json', { cache: 'no-cache' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      if (!data || !Array.isArray(data.releases)) throw new Error('Invalid release list')

      const releases = data.releases.filter(validRelease)
      const uniqueReleases = new Map(releases.map((release) => [release.platform, release]))
      uniqueReleases.forEach((release, platform) => {
        const card = document.querySelector(`.download-card[data-platform="${platform}"]`)
        if (!card) return

        const version = card.querySelector('.download-version')
        const status = card.querySelector('.download-status')
        version.textContent = `Версия ${release.version}`
        status.textContent = 'Установочный файл опубликован.'

        const link = document.createElement('a')
        link.className = 'download-button'
        link.href = release.url
        link.textContent = 'Скачать'
        card.append(link)
      })

      if (uniqueReleases.size) {
        downloadNote.textContent = typeof data.message === 'string' ? data.message : 'Выберите сборку для своей платформы.'
      } else {
        downloadNote.textContent = typeof data.message === 'string'
          ? data.message
          : 'Сейчас нет подтверждённых ссылок на актуальные настольные сборки.'
      }
    } catch {
      downloadNote.textContent = 'Не удалось загрузить список релизов. Попробуйте позже.'
    }
  }

  loadDesktopReleases()

  if (!reducedMotion.matches && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries, currentObserver) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          currentObserver.unobserve(entry.target)
        }
      })
    }, { threshold: 0.12 })

    document.querySelectorAll('.reveal').forEach((element) => observer.observe(element))
    document.body.classList.add('motion-ready')
  }
})()
