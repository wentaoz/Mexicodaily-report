import os
import json
import requests
import datetime
from tavily import TavilyClient
from openai import OpenAI

# --- 配置区域 ---
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com") 
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# 获取当前月份，例如 "February 2026"
current_month = datetime.date.today().strftime("%B %Y")

# --- 🎯 广角搜索关键词 ---
SEARCH_QUERIES = [
    # 1. 💰 利率与收益 (最核心竞争点)
    f"Nu Mexico vs Klar vs Ualá tasas de rendimiento {current_month}",
    
    # 2. 🚗 滴滴 (DiDi) 专项监测
    f"DiDi Card México tarjeta crédito beneficios y opiniones {current_month}",
    
    # 3. 💳 竞品对比与吐槽 (找用户真实痛点)
    f"RappiCard vs Stori vs Nu comentarios quejas usuarios {current_month}",
    
    # 4. ⚖️ 监管与大盘
    "CNBV regulación fintech México noticias recientes"
]

def search_with_tavily():
    print("🔍 [1/3] 正在调用 Tavily 全网搜索...")
    if not TAVILY_API_KEY:
        return "❌ 错误：未设置 TAVILY_API_KEY"

    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    combined_results = []

    for query in SEARCH_QUERIES:
        print(f"   -> 搜索: {query}")
        try:
            # 关键参数调整：
            # topic="general": 包含博客、论坛、官网 (比 news 数据更多)
            # days=30: 只要是本月的内容都算
            response = tavily.search(
                query=query,
                search_depth="advanced",
                topic="general", 
                days=30,
                max_results=2
            )
            
            for res in response.get('results', []):
                # 过滤掉太短的内容
                if len(res['content']) > 50:
                    combined_results.append(f"【话题: {query}】\n标题: {res['title']}\n摘要: {res['content']}\n链接: {res['url']}")
        
        except Exception as e:
            print(f"      ❌ Tavily 搜索异常: {e}")

    return "\n\n".join(combined_results)

def analyze_with_deepseek(raw_data):
    if not raw_data:
        return "⚠️ Tavily 未搜索到数据，请检查 Key 或关键词设置。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 进行分析...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    prompt = f"""
    你是一位专注于拉美市场的 Fintech 产品经理。
    请根据以下【Tavily 搜索到的全网数据】，写一份**墨西哥市场竞品日报**。

    【搜索数据】：
    {raw_data}

    【撰写要求】：
    1. **核心竞品**：重点关注 **Nu, DiDi (滴滴), Rappi, Stori**。
    2. **不仅是新闻**：请从搜索结果中提炼**“用户正在讨论什么”**（例如：谁家额度高？谁家客服烂？谁家利息涨了？）。
    3. **板块划分** (Markdown)：
       - **🔥 市场热点** (Yield Wars/监管)
       - **🚀 竞品动态** (DiDi/Nu/Rappi 功能或营销)
       - **🗣 用户舆情** (真实口碑与吐槽 - 重点)
    4. **来源**：必须附带链接。

    请直接输出报告：
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 分析失败: {e}"

def send_dingtalk(content):
    print("🚀 [3/3] 正在推送...")
    if not DINGTALK_WEBHOOK:
        return

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "墨西哥Fintech日报",
            "text": f"### 🌮 墨西哥 Fintech 竞品监测\n\n{content}"
        }
    }
    requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))

if __name__ == "__main__":
    raw_news = search_with_tavily()
    # 简单的 Debug，看看搜到了多少字
    print(f"📊 搜集到原始情报: {len(raw_news)} 字符")
    
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
