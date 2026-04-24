import yaml

with open("apps/agent/src/agent/rbac/rbac_config.yaml", "r") as f:
    config = yaml.safe_load(f)

config["roles"]["customer"]["tools"]["WEB_SEARCH"] = {
    "scopes": ["read"],
    "sensitivity": "low"
}

with open("apps/agent/src/agent/rbac/rbac_config.yaml", "w") as f:
    yaml.dump(config, f)
