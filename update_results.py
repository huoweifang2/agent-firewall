import re

with open("apps/frontend/app/pages/red-team/results/[id]/index.vue", "r") as f:
    content = f.read()

# Remove Header demo chip
content = re.sub(
    r'\n\s*<v-chip\n\s*v-if="isDemoTarget"\n[^\>]+>\n\s*Demo\n\s*</v-chip>',
    '',
    content
)

# Remove Recommended next step v-if
content = re.sub(
    r'\n\s*<v-btn\n\s*v-if="isDemoTarget"\n[\s\S]*?</v-btn>\n\s*<v-btn\n\s*v-else\n',
    r'\n                <v-btn\n',
    content
)
# remove p class isDemoTarget
content = re.sub(
    r'\s*<p v-if="isDemoTarget"[^>]*>[\s\S]*?</p>',
    '',
    content
)

# No failures baseline v-if
content = re.sub(
    r'\s*<v-btn\n\s*v-if="isDemoTarget"[\s\S]*?</v-btn>\s*<v-btn\n\s*v-else',
    r'\n            <v-btn',
    content
)

# Text center link v-if
content = re.sub(
    r'\s*<a\n\s*v-if="isDemoTarget"[\s\S]*?</a>\s*<a\n\s*v-else',
    r'\n            <a',
    content
)

# Sticky cta v-if
content = re.sub(
    r'\s*<v-btn\n\s*v-if="isDemoTarget"[\s\S]*?</v-btn>\s*<v-btn\n\s*v-else',
    r'\n            <v-btn',
    content
)

# Remove computed property
content = re.sub(
    r'const isDemoTarget = computed\(\(\) => \{\n  const t = run\.value\?\.target_type \?\? \'\'\n  return t === \'demo\' \|\| t === \'demo_agent\'\n\}\)\n',
    '',
    content
)

with open("apps/frontend/app/pages/red-team/results/[id]/index.vue", "w") as f:
    f.write(content)

