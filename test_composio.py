import requests

response = requests.get('https://backend.composio.dev/api/v1/apps')
data = response.json()
apps = [app['name'] for app in data.get('items', []) if 'file' in app['name'].lower() or 'tool' in app['name'].lower()]
print("Matching apps:", apps)
