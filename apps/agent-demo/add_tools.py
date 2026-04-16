with open("src/agent/tools/registry.py", "r") as f:
    content = f.read()

func = """
def get_tools_description(allowed_tools: list[str]) -> str:
    # We no longer strictly list allowed tools here since we dynamically fetch schemas and LLMs use schemas.
    # Just return a generic note.
    return "You have access to the dynamic tools provided in the API tools schema array."

def get_allowed_tools"""

content = content.replace("def get_allowed_tools", func)

with open("src/agent/tools/registry.py", "w") as f:
    f.write(content)
