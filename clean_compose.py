import re

# Clean infra/docker-compose.yml properly
with open('infra/docker-compose.yml', 'r') as f:
    text = f.read()

# remove ollama service block
text = re.sub(r'  # ── Ollama ────────────────────────────────────────────\n  ollama:(?:.|\n)*?    healthcheck:(?:.|\n)*?      start_period: 2s\n', '', text)
# remove model-pull block completely
text = re.sub(r'  # ── Init.*?\n  model-pull:(?:.|\n)*?    profiles:\n      - full\n', '', text, flags=re.MULTILINE|re.DOTALL)
# remove ollama volume
text = re.sub(r'      - ollama_models:/root/\.ollama\n', '', text)
text = re.sub(r'      OLLAMA_BASE_URL: http://ollama:11434\n', '', text)
text = re.sub(r'      OLLAMA_HOST: \$\{OLLAMA_HOST:-http://host\.docker\.internal:11434\}\n', '', text)
text = re.sub(r'      - ollama\n', '', text)
text = re.sub(r'volumes:\n  db_data:\n  redis_data:\n  ollama_models:\n', 'volumes:\n  db_data:\n  redis_data:\n', text)
text = text.replace('#   make demo    → demo mode (mock LLM, no Ollama)\n#   make up      → full stack (Ollama + real LLM)', '#   make demo    → demo mode (mock LLM)\n#   make up      → full stack (real API LLM)')

# Some remnants could be left because regex didn't match.

with open('infra/docker-compose.yml', 'w') as f:
    f.write(text)

