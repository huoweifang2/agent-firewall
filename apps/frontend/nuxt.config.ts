// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // SPA mode — this is a dashboard app with no SEO needs.
  // Avoids hydration mismatches from browser-only APIs
  // (DOMPurify, localStorage, sessionStorage) used throughout.
  ssr: false,

  modules: [
    'vuetify-nuxt-module',
    '@pinia/nuxt',
    '@nuxt/eslint',
    '@nuxtjs/google-fonts',
  ],

  googleFonts: {
    families: {
      Lora: [400, 500, 600, 700]
    },
    display: 'swap',
  },

  css: ['~/assets/global.scss'],

  vuetify: {
    moduleOptions: {
      styles: 'sass',
    },
    vuetifyOptions: {
      theme: {
        defaultTheme: 'light',
        themes: {
          light: {
            colors: {
              primary: '#4F5FB5',
              secondary: '#009688',
              info: '#0EA5E9',
              error: '#DC2626',
              warning: '#D97706',
              success: '#16A34A',
              background: '#F5F5F5',
              surface: '#FFFFFF',
              'surface-bright': '#FFFFFF',
              'surface-light': '#EEEEEE',
              'surface-variant': '#424242',
              'on-surface-variant': '#EEEEEE',
            },
          },
        },
      },
      icons: {
        defaultSet: 'mdi',
      },
    },
  },

  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
      agentApiBase: 'http://localhost:8002',
      deepseekApiBase: 'https://api.deepseek.com',
    },
  },

  typescript: {
    strict: true,
  },
})
