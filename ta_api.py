import requests
import urllib3
from urllib.parse import quote

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TAClient:
    def __init__(self, base_url, token):
        self.api_url = f"{base_url.rstrip('/')}/querySql"
        self.token = token

    def execute_query(self, sql):
        """执行 SQL 并返回原始响应文本"""
        encoded_sql = quote(sql)
        full_url = f"{self.api_url}?token={self.token}&format=csv&sql={encoded_sql}"
        
        try:
            response = requests.post(full_url, timeout=60, verify=False)
            if response.status_code == 200:
                # 如果返回 JSON 说明是报错
                if response.text.strip().startswith('{"code"'):
                    return None, response.json()
                return response.text, None
            return None, f"HTTP {response.status_code}"
        except Exception as e:
            return None, str(e)
