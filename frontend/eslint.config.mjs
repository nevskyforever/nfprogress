import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import { globalIgnores } from 'eslint/config'
import pluginVue from 'eslint-plugin-vue'

export default defineConfigWithVueTs(
  {
    name: 'nfprogress/files-to-lint',
    files: ['**/*.{ts,tsx,vue}'],
  },
  globalIgnores([
    'dist/**',
    'coverage/**',
    'node_modules/**',
    'public/mindmap-assets/**',
  ]),
  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
)
