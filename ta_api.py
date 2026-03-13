import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TAClient:
    def __init__(self, base_url, token):
        self.api_url = f"{base_url.rstrip('/')}/querySql"
        self.token = token

    def execute_query(self, sql):
        # 414 修复：不再拼接 URL，而是构建表单数据
        payload = {
            "token": self.token,
            "format": "csv",
            "sql": sql
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # 使用 data=payload 将参数放入 HTTP Body
            response = requests.post(
                self.api_url, 
                data=payload, 
                headers=headers,
                timeout=120, # 归因 SQL 较重，增加超时时间
                verify=False
            )
            
            if response.status_code == 200:
                # 检查返回的是否是错误 JSON
                if response.text.strip().startswith('{"code"'):
                    return None, response.json()
                return response.text, None
            else:
                return None, f"HTTP Error: {response.status_code} - {response.reason}"
        except Exception as e:
            return None, str(e)
