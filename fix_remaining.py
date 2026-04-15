import re

with open("apps/frontend/app/pages/red-team/results/[id]/index.vue", "r") as f:
    content = f.read()

# remove other isDemoTarget usages
content = re.sub(
    r'\n\s*<v-chip\n\s*v-if="isDemoTarget"[^>]*>\n\s*Demo\n\s*</v-chip>',
    '',
    content
)

content = re.sub(
    r'\n\s*<p v-if="isDemoTarget"[^>]*>[\s\S]*?</p>',
    '',
    content
)

content = re.sub(
    r'\n\s*<div\n\s*v-if="isDemoTarget"[\s\S]*?</div<blockquote>.*?',
    '',
    content
)
content = re.sub(
    r'\n\s*<div\n\s*v-if="isDemoTarget"[^>]*>\n\s*<v-icon[^>]*>.*?</v-icon>\n\s*.*?</div\n?>',
    '',
    content
)

with open("apps/frontend/app/pages/red-team/results/[id]/index.vue", "w") as f:
    f.write(content)
