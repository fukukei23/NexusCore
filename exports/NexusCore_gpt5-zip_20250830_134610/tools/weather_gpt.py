from openai import OpenAI
import requests, os, json, sys

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    sys.exit("OPENAI_API_KEY が設定されていません")

client = OpenAI(api_key=API_KEY)

# ----------------------------------------------------------
# 外部関数：Open-Meteo で現在気温を取得
# ----------------------------------------------------------
def get_weather(city="Kyoto"):
    lat, lon = 35.0116, 135.7680  # Kyoto
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=temperature_2m,weathercode"
    )
    data = requests.get(url, timeout=10).json()["current"]
    return {"city": city, "temperature": data["temperature_2m"]}

# OpenAI に渡す関数仕様
tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "指定都市の現在の天気・気温を取得",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "都市名。例: Kyoto"}
        },
        "required": ["city"],
        "additionalProperties": False
    }
}]

messages = [{"role": "user", "content": "京都の今の天気は？"}]

# ----------------- 1st 呼び出し（関数を提案させる） -----------------
resp1 = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools
)
msg1 = resp1.choices[0].message

if msg1.tool_call:  # モデルが関数を呼びたいと提案
    args = json.loads(msg1.tool_call.arguments)
    result = get_weather(**args)

    messages += [
        msg1,  # function_call メッセージ
        {
            "role": "tool",
            "tool_call_id": msg1.tool_call.call_id,
            "content": json.dumps(result, ensure_ascii=False),
        },
    ]

    # -------------- 2nd 呼び出し（結果を踏まえて回答） --------------
    resp2 = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    print(resp2.choices[0].message.content)
else:
    print("Function was not called")
