import os
import json
import requests
from duckduckgo_search import DDGS
from openai import OpenAI

# --- 1. 配置区域 ---
# 这里的 getenv 意思是：优先读 GitHub 设置的，读不到就用默认的 (DeepSeek配置)
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
LLM_API_KEY = os.getenv("LLM_API_KEY")

# DeepSeek 官方配置
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com") 
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

# 搜索关键词（针对墨西哥市场）
SEARCH_KEYWORDS = [
    "Nu Mexico features update 2025",
    "Stori Mexico credit card news",
    "RappiCard Mexico latest updates",
    "CNBV Mexico fintech regulation 2025"
]

def search_web():
    print("🔍 [1/3] 正在搜索墨西哥市场情报...")
    results = []
    
    # 使用 DuckDuckGo 搜索
    # 尝试使用 html 后端，它对 GitHub 服务器 IP 更友好
    try:
        with DDGS() as ddgs:
            for keyword in SEARCH_KEYWORDS:
                print(f"   -> 搜索: {keyword}")
                try:
                    # backend="html" 是关键，专治 IP 被墙
                    keywords_results = list(ddgs.text(keyword, max_results=2, backend="html"))
                    
                    if not keywords_results:
                        print(f"      ⚠️ 关键词 '{keyword}' 未返回结果 (可能是反爬虫)")
                        continue

                    for r in keywords_results:
                        results.append(f"【来源: {r['title']}】\n内容: {r['body']}\n链接: {r['href']}")
                        
                except Exception as e:
                    print(f"      ❌ 单个关键词搜索失败: {e}")
                    
    except Exception as e:
        print(f"❌ 搜索组件严重错误: {e}")
    
    # 如果实在搜不到，返回一个硬编码的提示，防止 AI 瞎编
    if not results:
        print("❌ 所有搜索均失败，可能是 GitHub IP 被完全封锁。")
        return ""
    
    return "\n\n".join(results)


def analyze_with_deepseek(raw_data):
    if not raw_data:
        return "⚠️ 今日搜索接口未返回数据，请手动检查网络或关键词。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 进行分析...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    # 专门针对 DeepSeek 优化的 Prompt
    prompt = f"""
    你是一个精通墨西哥Fintech市场的资深产品经理。请根据以下抓取的搜索结果，写一份【每日竞品监测日报】。

    搜索数据：
    {raw_data}

    要求：
    1. **去伪存真**：过滤掉广告、无关信息，只保留确定的事实。
    2. **结构化输出**：请严格按照 Markdown 格式输出，包含两个板块：
       - **🚀 竞品新动向** (关注 Nu, Stori, Rappi 的 App 更新、新功能、UI/UX 调整)
       - **⚖️ 政策与市场** (关注 CNBV 监管、利率变化、新玩家入局)
    3. **一句话洞察**：在结尾加一句你作为 PM 对这些信息的个人简评。
    4. **引用**：每条信息后必须附带来源链接。
    
    如果搜索数据中没有实质性新内容，请直接回复：“今日暂无重大更新。”
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, # 调低温度，让 DeepSeek 更严谨，不瞎编
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ DeepSeek 调用失败: {e}"

def send_dingtalk(content):
    print("🚀 [3/3] 正在发送到钉钉...")
    if not DINGTALK_WEBHOOK:
        print("❌ 错误：未设置 DINGTALK_WEBHOOK，无法发送。")
        return

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "墨西哥Fintech日报",
            "text": f"### 🌮 墨西哥 Fintech 每日速递\n\n{content}"
        }
    }
    
    try:
        resp = requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))
        print(f"✅ 发送结果: {resp.text}")
    except Exception as e:
        print(f"❌ 发送异常: {e}")

if __name__ == "__main__":
    if not LLM_API_KEY:
        print("❌ 错误：未设置 LLM_API_KEY (DeepSeek Key)")
        exit(1)

    raw_news = search_web()
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
