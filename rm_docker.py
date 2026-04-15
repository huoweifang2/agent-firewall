import re
with open('infra/docker-compose.yml', 'r') as f:
    text = f.read()

# Aggressive clean up of any key or text having 'ollama'.
# We can just iterate by lines, dropping any block that starts with model-pull or ollama
lines = text.split('\n')
new_lines = []
in_skip_block = False
for line in lines:
    if line.strip() == 'ollama:' or line.strip() == 'model-pull:':
        in_skip_block = True
    if in_skip_block:
        if line.strip() == '' or not line.startswith('    ') and not line.startswith('      ') and not line.startswith('  #') and not line.strip() in ['ollama:', 'model-pull:']:
            in_skip_block = False
    
    if not in_skip_block and 'ollama' not in line.lower():
        new_lines.append(line)

with open('infra/docker-compose.yml', 'w') as f:
    f.write('\n'.join(new_lines))

