from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from agent_runtime.infrastructure.telegram_bridge import load_telegram_bridge_config


def _settings(**overrides):
    data = {
        "telegram_bridge_enabled": True,
        "telegram_bridge_poll_timeout_seconds": 10,
        "telegram_bridge_poll_interval_seconds": 1.0,
        "default_policy": "balanced",
        "default_model": "deepseek-chat",
        "agent_id": "",
        "openclaw_agent_id": "coder",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_load_bridge_config_reads_openclaw_accounts(monkeypatch, tmp_path: Path):
    home = tmp_path
    cfg_dir = home / ".openclaw"
    cfg_dir.mkdir()
    (cfg_dir / "agent-firewall.json").write_text(
        json.dumps(
            {
                "telegramBridge": {
                    "enabled": True,
                    "accounts": ["default"],
                    "policy": "strict",
                    "model": "deepseek-chat",
                    "userRole": "customer",
                }
            }
        ),
        encoding="utf-8",
    )
    (cfg_dir / "openclaw.json").write_text(
        json.dumps(
            {
                "channels": {
                    "telegram": {
                        "enabled": False,
                        "accounts": {
                            "default": {
                                "botToken": "123456:test-token",
                                "allowFrom": ["42"],
                            },
                            "other": {
                                "botToken": "654321:other-token",
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: home)

    config = load_telegram_bridge_config(_settings())

    assert config.enabled is True
    assert len(config.accounts) == 1
    assert config.accounts[0].name == "default"
    assert config.accounts[0].allow_from == {"42"}
    assert config.accounts[0].policy == "strict"
    assert config.accounts[0].model == "deepseek-chat"


def test_env_flag_disables_bridge_even_when_openclaw_enabled(monkeypatch, tmp_path: Path):
    home = tmp_path
    cfg_dir = home / ".openclaw"
    cfg_dir.mkdir()
    (cfg_dir / "agent-firewall.json").write_text(
        json.dumps({"telegramBridge": {"enabled": True}}),
        encoding="utf-8",
    )
    (cfg_dir / "openclaw.json").write_text(
        json.dumps(
            {
                "channels": {"telegram": {"botToken": "123456:test-token"}},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: home)

    config = load_telegram_bridge_config(_settings(telegram_bridge_enabled=False))

    assert config.enabled is False
    assert len(config.accounts) == 1
