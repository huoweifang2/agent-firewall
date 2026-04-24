# Agent-Firewall

Agent-Firewall is a single-person graduation project focused on providing guardrails and security scanning for tool-calling AI agents. It aims to find prompt injection and unauthorized tool use with deterministic enforcement, keeping the LLM out of the decision loop.

*👉 [中文说明 (Chinese Version)](README_zh.md)*

---

## Quickstart & Local Development

### Prerequisites
- **Docker & Docker Compose** 
- **uv** (for Python dependency management): `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`)
- **Node.js & npm** (for frontend)

### Start the Stack

The most common way to run the project for testing or development is starting all local application services concurrently:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Szesnasty/agent-firewall.git
   cd agent-firewall
   ```

2. **Install dependencies:**
   ```bash
   make setup
   ```

3. **Configure API Keys:**
   Create or edit the `.env` files in `apps/agent/` and `apps/proxy-service/` to include the required API keys for the LLM providers and Composio tools. For example:
   ```env
   # Example .env configuration
   DEEPSEEK_API_KEY="your-deepseek-api-key"
   COMPOSIO_API_KEY="your-composio-api-key"
   ```

4. **Start the full development environment:**
   ```bash
   ./start-local.sh
   ```
   *(This starts the backend proxy, agent service, frontend portal, as well as the required Docker infrastructure (DB, Redis, Langfuse) concurrently.)*

5. **Access the portal:**
   Open **http://localhost:3000** in your browser.

> Note: To cleanly shut down the services and infrastructure, use `Ctrl+C` first to stop the terminal apps, and run `make down` to stop the Docker backend.

---

## Core Features

### 🛡️ Proxy Firewall
5 detection layers run locally on every LLM call (~50 ms overhead, no external APIs):
- **Rules:** Denylist phrases, length limits, encoding checks
- **Intent classifier:** Regex patterns for attack type classification
- **LLM Guard:** DeBERTa injection detection, DistilBERT toxicity
- **Presidio PII:** Entity scrubbing (names, emails, cards, phone numbers)
- **NeMo Guardrails:** Semantic similarity via FastEmbed embeddings

### 🔍 Agent-Level Enforcement
Intercepts and enforces policy at two gates during tool execution:
- **Tool Integrations:** Powered by the Composio SDK for seamless and extensive third-party application execution.
- **Pre-tool gate:** RBAC, argument injection scan, budget, confirmation
- **Post-tool gate:** PII redaction, secrets scan, indirect injection

### 📊 Security Scan
Run curated attack scenarios against an target endpoint to test vulnerabilities and measure the effectiveness of your guardrails deterministically.

---

## Performance

| Metric | Value |
|---|---|
| Attacks blocked | **97.9%** (331 / 338) |
| False positive rate | **0 / 20** safe prompts blocked |
| Pipeline overhead | ~50 ms per request (balanced policy) |
| Memory | ~1.1 GB RAM (all scanners loaded) |

→ [Full internal benchmark](BENCHMARK.md) · [JailbreakBench results](BENCHMARK_JAILBREAKBENCH.md)

---

## Known Limitations
Agent-Firewall serves as an experimental proof of concept for tool security. It reduces practical risk but does not eliminate it entirely (e.g., semantic attacks bypassing regex).
