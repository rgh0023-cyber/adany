import requests
import pandas as pd
import io

class TADataClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip('/')
        # 对应文档中的接口路径
        self.api_url = f"{self.base_url}/querySql"
        self.token = token

    def query_sql(self, sql_string):
        """
        执行 SQL 查询
        """
        # 参数根据文档：token, format, sql
        params = {
            "token": self.token,
            "format": "csv", # 使用 csv 格式方便 pandas 直接读取，节省解析时间
            "sql": sql_string
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            # SQL 接口通常通过 POST 提交表单数据
            response = requests.post(
                self.api_url, 
                params=params, # 对应文档中在 URL 后拼参数
                headers=headers,
                timeout=60,
                verify=False
            )
            
            if response.status_code == 200:
                # 如果返回的是 CSV 文本
                if "text/csv" in response.headers.get("Content-Type", "") or not response.text.startswith('{'):
                    df = pd.read_csv(io.StringIO(response.text))
                    return {"status": "success", "data": df}
                else:
                    # 如果返回的是 JSON (通常是报错信息)
                    return {"status": "error", "message": response.json()}
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
