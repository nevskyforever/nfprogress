import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { projectFixture } from '@/test/fixtures'

import ProjectCard from './ProjectCard.vue'

describe('ProjectCard', () => {
  it('renders API project progress as an accessible project link', () => {
    const wrapper = mount(ProjectCard, {
      props: { project: projectFixture() },
      global: {
        plugins: [createPinia()],
        stubs: {
          IonIcon: true,
          RouterLink: {
            props: ['to'],
            template: '<a href="/projects/project-id"><slot /></a>',
          },
        },
      },
    })

    expect(wrapper.get('h2').text()).toBe('Дом у моря')
    expect(wrapper.get('[role="img"]').attributes('aria-label')).toContain('Дом у моря')
    expect(wrapper.get('[role="img"]').text()).toContain('25%')
    expect(wrapper.get('a').attributes('aria-label')).toContain('Открыть проект')
  })
})
