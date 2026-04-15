import re

with open("apps/frontend/app/pages/red-team/run/[id].vue", "r") as f:
    content = f.read()

# Remove Header demo chip
content = re.sub(
    r'\n\s*<v-chip\n\s*v-if="isDemo"[\s\S]*?</v-chip>',
    '',
    content
)

# Remove computed property
content = re.sub(
    r'\nconst isDemo = computed\(\(\) => runDetail\.value\?\.target_type === \'demo\'\)',
    '',
    content
)

with open("apps/frontend/app/pages/red-team/run/[id].vue", "w") as f:
    f.write(content)

