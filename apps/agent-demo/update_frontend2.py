with open("apps/frontend/app/pages/middleware.vue", "r") as f:
    content = f.read()

old_arr = """const integrations = ref([
  { name: 'WEATHERMAP', icon: 'mdi-weather-cloudy', enabled: false, preGate: false, postGate: false },
  { name: 'GITHUB', icon: 'mdi-github', enabled: false, preGate: false, postGate: false },
  { name: 'SLACK', icon: 'mdi-slack', enabled: false, preGate: false, postGate: false },
  { name: 'FILETOOL', icon: 'mdi-folder', enabled: false, preGate: false, postGate: false },
  { name: 'GMAIL', icon: 'mdi-gmail', enabled: false, preGate: false, postGate: false },
])"""

new_arr = """const integrations = ref([
  { name: 'WEB_SEARCH', icon: 'mdi-web', enabled: false, preGate: false, postGate: false },
  { name: 'GITHUB', icon: 'mdi-github', enabled: false, preGate: false, postGate: false },
  { name: 'SLACK', icon: 'mdi-slack', enabled: false, preGate: false, postGate: false },
  { name: 'FILETOOL', icon: 'mdi-folder', enabled: false, preGate: false, postGate: false },
  { name: 'GMAIL', icon: 'mdi-gmail', enabled: false, preGate: false, postGate: false },
])"""

content = content.replace(old_arr, new_arr)

with open("apps/frontend/app/pages/middleware.vue", "w") as f:
    f.write(content)
