import os
import json
import requests
import datetime
from duckduckgo_search import DDGS
from openai import OpenAI

# --- 1. 配置区域 ---
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com") 
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

# 获取当前年份
current_year = datetime.date.today().year

# 关键词列表
SEARCH_KEYWORDS = [
    f"Nu Mexico product updates {current_year}",
    f"Stori Mexico new features {current_year}",
    f"RappiCard Mexico news {current_year}",
    f"CNBV Mexico fintech regulation {current_year}"
]

def search_web():
    print(f"🔍 [1/3] 正在搜索 {current_year} 年的最新情报 (限制过去一周)...")
    results = []
    
    try:
        with DDGS() as ddgs:
            for keyword in SEARCH_KEYWORDS:
                print(f"   -> 搜索: {keyword}")
                try:
                    # --- 关键修改：backend='html' 和 timelimit='w' ---
                    keywords_results = list(ddgs.text(keyword, max_results=2, backend="html", timelimit="w"))
                    
                    if not keywords_results:
                        print(f"      ⚠️ '{keyword}' 最近一周无结果")
                        continue

                    for r in keywords_results:
                        results.append(f"【标题】{r['title']}\n【摘要】{r['body']}\n【链接】{r['href']}")
                        
                except Exception as e:
                    print(f"      ❌ 单个关键词搜索异常: {e}")
                    
    except Exception as e:
        print(f"❌ 搜索组件错误: {e}")
    
    return "\n\n".join(results)

def analyze_with_deepseek(raw_data):
    if not raw_data:
        return "📅 最近一周内，市场上没有关于 Nu、Stori 或 CNBV 的重大公开新闻。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 进行分析...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    prompt = f"""
    今天是 {datetime.date.today()}。
    你是一位墨西哥Fintech专家。请分析以下【过去一周】的搜索结果，写一份日报。

    搜索数据：
    {raw_data}

    要求：
    1. **只关注新消息**：如果内容是旧闻，请直接忽略。
    2. **格式**：Markdown。
    3. **重点**：竞品的新功能、新UI、监管新规。

    请开始分析：
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 分析失败: {e}"

def send_dingtalk(content):
    print("🚀 [3/3] 正在发送到钉钉...")
    if not DINGTALK_WEBHOOK:
        print("❌ 未设置 Webhook")
        return

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "墨西哥Fintech日报",
            "text": f"### 🌮 墨西哥 Fintech 每日速递 ({datetime.date.today()})\n\n{content}"
        }
    }
    requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))

if __name__ == "__main__":
    raw_news = search_web()
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
