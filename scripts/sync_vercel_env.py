import json
import urllib.request
import urllib.error
import os
from dotenv import dotenv_values

auth_path = os.path.expandvars(r'%APPDATA%\com.vercel.cli\Data\auth.json')
with open(auth_path) as f:
    token = json.load(f).get('token')

project_id = 'prj_6ZVyeYpNFvzbwyzHrveMxrjIwmqr'
team_id = 'team_AVnfIjuj7mwQP9pSKr9oULue'

# 1. Fetch existing env vars
url = f'https://api.vercel.com/v9/projects/{project_id}/env?teamId={team_id}'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})

existing_keys = set()
try:
    with urllib.request.urlopen(req) as resp:
        envs = json.loads(resp.read().decode())
        for e in envs.get('envs', []):
            existing_keys.add(e.get('key'))
        print(f"Existing env vars ({len(existing_keys)}):", list(existing_keys))
except Exception as e:
    print('Error fetching envs:', e)

# 2. Read local .env
local_env = dotenv_values(".env")
print("Local env keys:", list(local_env.keys()))

required_keys = [
    'SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY',
    'SUPABASE_ANON_KEY',
    'OPEN_METEO_BASE_URL',
    'APP_ENV',
    'APP_VERSION',
    'FRONTEND_ORIGIN'
]

# Provide fallback/defaults if not in .env
defaults = {
    'OPEN_METEO_BASE_URL': 'https://api.open-meteo.com/v1/forecast',
    'APP_ENV': 'production',
    'APP_VERSION': '1.0.0',
    'FRONTEND_ORIGIN': 'https://flood-prediction-roan.vercel.app'
}

for k in required_keys:
    val = local_env.get(k) or defaults.get(k)
    if not val:
        print(f"Warning: No value found for {k}")
        continue
    if k in existing_keys:
        print(f"Env {k} already exists on Vercel.")
    else:
        print(f"Adding {k} to Vercel...")
        post_data = {
            "key": k,
            "value": val,
            "type": "encrypted" if "KEY" in k or "SECRET" in k else "plain",
            "target": ["production", "preview", "development"]
        }
        post_req = urllib.request.Request(
            url,
            data=json.dumps(post_data).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        try:
            with urllib.request.urlopen(post_req) as post_resp:
                print(f"Successfully added {k}")
        except Exception as err:
            print(f"Failed to add {k}: {err}")
