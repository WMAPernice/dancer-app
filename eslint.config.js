import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import pluginVitest from '@vitest/eslint-plugin'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{js,mjs,jsx,vue}'],
  },

  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**'],
  },

  {
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  
  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },
  skipFormatting,
]

module.exports = {
    env: {
        browser: true,
        es2021: true,
    },
    extends: ['eslint:recommended'],
    parserOptions: {
        ecmaVersion: 12,
        sourceType: 'module',
    },
    rules: {
        'no-unused-vars': 'warn',
        'no-console': 'warn',
    },
};
