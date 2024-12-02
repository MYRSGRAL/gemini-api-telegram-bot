import aiohttp
from user_agent import generate_user_agent

import skysmart.api_variables as api


class SkysmartAPIClient:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.token = ''
        self.user_agent = generate_user_agent()

    async def close(self):
        await self.session.close()

    async def _authenticate(self):
        headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent
        }
        async with self.session.post(api.url_auth2, headers=headers) as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                self.token = json_resp["jwtToken"]
            else:
                raise Exception(f"Authentication failed with status: {resp.status}")

    async def _get_headers(self):
        if not self.token:
            await self._authenticate()
        return {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Authorization': f'Bearer {self.token}'
        }

    async def get_room(self, task_hash):
        payload = {"taskHash": task_hash}
        headers = await self._get_headers()
        async with self.session.post(api.url_room, headers=headers, json=payload) as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                return json_resp['meta']['stepUuids']
            else:
                raise Exception(f"get_room failed with status: {resp.status}")

    async def get_task_html(self, uuid):
        headers = await self._get_headers()
        async with self.session.get(f"{api.url_steps}{uuid}", headers=headers) as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                return json_resp['content']
            else:
                raise Exception(f"get_task_html failed with status: {resp.status}")

    async def get_room_info(self, task_hash):
        payload = {"taskHash": task_hash}
        headers = await self._get_headers()
        async with self.session.post(api.url_room_preview, headers=headers, json=payload) as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                return json_resp
            else:
                raise Exception(f"get_room_info failed with status: {resp.status}")
