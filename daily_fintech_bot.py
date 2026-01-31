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

# --- 2. 关键词升级 (包含 Nu, Stori, Rappi, DiDi) ---
SEARCH_KEYWORDS = [
    # Nu (市场老大)
    f"Nu Mexico product updates {current_year}",
    # Stori (独角兽竞品)
    f"Stori Mexico credit card new features {current_year}",
    # RappiCard (重点关注)
    f"RappiCard Mexico latest news {current_year}",
    f"RappiCard Mexico app design changes {current_year}",
    # DiDi (滴滴 - 新增)
    f"DiDi Card Mexico updates {current_year}",
    f"DiDi Préstamos Mexico news {current_year}",
    # 监管 (CNBV)
    f"CNBV Mexico fintech regulation {current_year}"
]

def search_web():
    print(f"🔍 [1/3] 正在全网搜罗 {current_year} 年最新情报 (Nu/Stori/Rappi/DiDi)...")
    results = []
    
    try:
        with DDGS() as ddgs:
            for keyword in SEARCH_KEYWORDS:
                print(f"   -> 正在抓取: {keyword}")
                try:
                    # backend="html" 防封, timelimit="w" 只看本周
                    keywords_results = list(ddgs.text(keyword, max_results=2, backend="html", timelimit="m"))
                    
                    if not keywords_results:
                        print(f"      ⚠️ 暂无本周新消息: {keyword}")
                        continue

                    for r in keywords_results:
                        # 拼接来源，方便 AI 识别是谁家的消息
                        results.append(f"【搜索词: {keyword}】\n标题: {r['title']}\n摘要: {r['body']}\n链接: {r['href']}")
                        
                except Exception as e:
                    print(f"      ❌ 单个关键词搜索跳过: {e}")
                    
    except Exception as e:
        print(f"❌ 搜索组件异常: {e}")
    
    return "\n\n".join(results)

def analyze_with_deepseek(raw_data):
    if not raw_data:
        return "📅 本周监测范围内 (Nu, Stori, Rappi, DiDi) 暂无重大公开新闻。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 整理情报...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    # 这里的 Prompt 专门加强了对 DiDi 和 Rappi 的关注
    prompt = f"""
    你是墨西哥Fintech市场专家。请根据以下【本周搜索结果】写一份日报。

    搜索数据：
    {raw_data}

    撰写要求：
    1. **核心竞品**：重点关注 **Nu, RappiCard, DiDi (滴滴), Stori** 的动态。
    2. **去重去噪**：忽略旧闻和无意义的SEO广告，只保留实质性更新（如：新功能、新设计、利率调整、监管罚款/新规）。
    3. **格式结构** (Markdown)：
       - **🚀 竞品新功能/设计** (谁？更新了什么？)
       - **💳 市场与监管** (CNBV新规或宏观动态)
    4. **来源**：每条情报后附上链接。

    若某家竞品本周无消息，则不需要强行提及。直接输出报告。
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, # 低温度，保证事实准确
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 分析失败: {e}"

def send_dingtalk(content):
    print("🚀 [3/3] 正在推送至钉钉群...")
    if not DINGTALK_WEBHOOK:
        print("❌ 错误：未设置 Webhook")
        return

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            # 标题包含“墨西哥”以通过钉钉拦截
            "title": "墨西哥Fintech竞品日报",
            "text": f"### 🌮 墨西哥 Fintech 竞品日报 ({datetime.date.today()})\n\n{content}"
        }
    }
    
    try:
        requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))
        print("✅ 推送成功！")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    raw_news = search_web()
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
