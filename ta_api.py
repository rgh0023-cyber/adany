import requests
import json

class TADataClient:
    def __init__(self, base_url, token):
        # 确保基础 URL 不带结尾斜杠，并补全数数报表 API 路径
        self.base_url = base_url.rstrip('/')
        # 数数报表查询的标准端点
        self.api_url = f"{self.base_url}/api/v1/report/data"
        self.token = token

    def fetch_report_data(self, report_params):
        headers = {
            "Content-Type": "application/json",
            "token": self.token
        }
        
        try:
            # verify=False 解决私有化部署 https 证书不受信任导致请求卡死或返回空的问题
            response = requests.post(
                self.api_url, 
                data=json.dumps(report_params), 
                headers=headers,
                timeout=30,
                verify=False 
            )
            
            # 返回完整的响应对象供前端分析
            return {
                "status_code": response.status_code,
                "text": response.text,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "status_code": "EXCEPTION",
                "text": str(e),
                "data": None
            }
