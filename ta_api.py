import requests
import pandas as pd
import io
from urllib.parse import quote

class TADataClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/querySql"
        self.token = token

    def query_sql(self, sql_string):
        """
        执行数数报表生成的复杂 SQL
        """
        # 复杂 SQL 必须进行 URL 编码
        encoded_sql = quote(sql_string)
        
        # 构造请求 URL
        full_url = f"{self.api_url}?token={self.token}&format=csv&sql={encoded_sql}"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # 采用 POST 请求，参数通过 URL 传递（符合数数文档示例）
            response = requests.post(
                full_url, 
                headers=headers,
                timeout=60,
                verify=False
            )
            
            if response.status_code == 200:
                # 检查是否返回了错误 JSON 而非数据
                if response.text.strip().startswith('{"code"'):
                    return {"status": "error", "message": response.json()}
                
                # 读取 CSV 数据
                df = pd.read_csv(io.StringIO(response.text))
                return {"status": "success", "data": df}
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
