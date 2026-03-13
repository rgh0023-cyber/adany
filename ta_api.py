
import requests
import json
import pandas as pd

class TADataClient:
    def __init__(self, base_url, token):
        """
        :param base_url: https://ta-open.jackpotlandslots.com
        :param token: 在数数后台“数据 API”页面获取的 API Token
        """
        self.base_url = base_url.rstrip('/')
        self.token = token

    def fetch_report_data(self, report_params):
        """
        通过报表参数获取数据
        接口路径参考文档中的 /api/v1/report/data
        """
        url = f"{self.base_url}/api/v1/report/data"
        
        # 构造请求头
        headers = {
            "Content-Type": "application/json",
            "token": self.token
        }
        
        try:
            # 发送 POST 请求，传入你提供的 JSON 配置
            response = requests.post(url, data=json.dumps(report_params), headers=headers)
            response.raise_for_status() # 检查 HTTP 状态码
            
            res_json = response.json()
            
            if res_json.get("code") == 0:
                # 提取数据部分（根据 TA 不同的报表返回格式，这里可能需要根据实际返回微调）
                # 通常数据在 res_json['data']['rows'] 或类似位置
                data = res_json.get("data", {})
                return data
            else:
                print(f"❌ API 报错: {res_json.get('msg')}")
                return None
        except Exception as e:
            print(f"⚠️ 请求发生异常: {e}")
            return None

# --- 测试代码 ---
if __name__ == "__main__":
    # 请在此处填入你的 Token（重要：不要泄露）
    MY_TOKEN = "你的_API_TOKEN" 
    API_URL = "https://ta-open.jackpotlandslots.com"
    
    # 你提供的 JSON 示例
    example_params = {
        "eventView": {
            "comparedByTime": False,
            "endTime": "2026-03-12 23:59:59",
            "filts": [],
            "groupBy": [],
            "recentDay": "1-7",
            "relation": "and",
            "startTime": "2026-03-06 00:00:00",
            "timeParticleSize": "day"
        },
        "events": [
            {
                "analysis": "TRIG_USER_NUM",
                "analysisParams": "",
                "eventName": "level_start",
                "eventNameDisplay": "level_start.触发用户数",
                "eventUuid": "qZds731N",
                "filts": [],
                "quota": "",
                "quotaEntities": [
                    {
                        "index": 0,
                        "taIdMeasure": {"columnDesc": "用户唯一ID", "columnName": "#user_id", "tableType": "event"}
                    }
                ],
                "relation": "and",
                "type": "normal"
            }
        ],
        "projectId": 46
    }

    client = TADataClient(API_URL, MY_TOKEN)
    data = client.fetch_report_data(example_params)
    
    if data:
        print("✅ 成功获取数据：")
        print(json.dumps(data, indent=2, ensure_ascii=False))
