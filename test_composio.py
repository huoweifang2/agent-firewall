import json
import os
os.environ["COMPOSIO_API_KEY"] = "ak_mISJAU2K6fDlkLedOqMa"
from composio import Composio

try:
    composio_client = Composio()
    print("Has create?", hasattr(composio_client, "create"))
    print("Has get_tools?", hasattr(composio_client.tools, "get"))
    # Let's see what tools look like
    # tools = composio_client.tools.get(user_id="test")
    # print("Tools type:", type(tools))
except Exception as e:
    print("Error:", e)
