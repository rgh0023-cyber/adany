import requests
import urllib3
from urllib.parse import quote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TAClient:
    def __init__(self, base_url, token):
        self.api_url = f"{base_url.rstrip('/')}/querySql"
        self.token = token

    def execute_query(self, sql):
        encoded_sql = quote(sql)
        full_url = f"{self.api_url}?token={self.token}&format=csv&sql={encoded_sql}"
        try:
            response = requests.post(full_url, timeout=60, verify=False)
            if response.status_code == 200:
                if response.text.strip().startswith('{"code"'):
                    return None, response.json()
                return response.text, None
            return None, f"HTTP Error: {response.status_code}"
        except Exception as e:
            return None, str(e)
