import re

with open("apps/frontend/app/pages/red-team/results/[id]/index.vue", "r") as f:
    content = f.read()

# remove onRerunProtected function
content = re.sub(
    r'\nasync function onRerunProtected\(\) \{[\s\S]*?\}\n',
    '\n',
    content
)

with open("apps/frontend/app/pages/red-team/results/[id]/index.vue", "w") as f:
    f.write(content)
