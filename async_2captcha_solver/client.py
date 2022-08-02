from distutils.log import debug
import aiohttp
import asyncio
from . import errors
from urllib import parse


class Client:
    def __init__(self, api_key, debug=False) -> None:
        self.api_key = api_key
        self._base = "http://2captcha.com"
        self._session = None
        self.debug = debug

    def escape(self, value: str):
        return parse.quote(str(value).encode("UTF-8"))

    def _param_dict_parse(self, params: dict):
        parsed = f"key={self.api_key}&json=1"
        if self.debug:
            parsed = f"{parsed}&debug_dump=1"
        for k, v in params.items():
            if parsed != "":
                parsed = f"{parsed}&{k}={self.escape(v)}"
            else:
                parsed = f"{k}={self.escape(v)}"
        return parsed

    async def _request(self, path: str, params: dict, method: str):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        url = f"{self._base}{path}?{self._param_dict_parse(params)}"
        r = await self._session.request(method=method, url=url)
        if r.status == 200:
            return await r.json()

    async def solve_hcaptcha(self, site_key: str,
                             page_url: str,
                             rq_data: str,
                             user_agent: str,
                             invisible=0,
                             wait_for_solve: bool = True,
                             proxy: str = None
                             ):
        params = {
            "method": "hcaptcha",
            "sitekey": site_key,
            "pageurl":  page_url,
            "userAgent": user_agent,
            "data": rq_data,
            "invisible": invisible,
            "header_acao": 1
        }
        if proxy is not None:
            params.update({

            })
        path = "/in.php"
        method = "POST"
        r = await self._request(path, params, method=method)
        if r.get("status") == 1:
            req_id = r.get("request")
            if wait_for_solve:
                try:
                    return await self.wait_for_captcha_solve(req_id)
                except errors.CaptchaUnsolvable:
                    return await self.solve_hcaptcha(site_key, page_url, user_agent, invisible)
            return req_id

    async def wait_for_captcha_solve(self, request_id: str):
        path = "/res.php"
        params = {
            "action": "get",
            "id": request_id,
        }
        while True:
            r = await self._request(path, params, "GET")
            status = r.get("status")
            response = r.get("request")
            if status == 1:
                # Captcha solved. Return response code.
                return response
            if response == "ERROR_CAPTCHA_UNSOLVABLE":
                raise errors.CaptchaUnsolvable(response, 400)
            await asyncio.sleep(5)