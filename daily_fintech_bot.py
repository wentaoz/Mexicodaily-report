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

# --- 智能时间窗口计算 (去重核心逻辑) ---
def get_search_window():
    """
    根据今天是周几，决定回溯几天，防止内容重复。
    周一运行 -> 回溯 4 天 (覆盖上周四到周日)
    周四运行 -> 回溯 3 天 (覆盖周一到周三)
    其他时间(手动运行) -> 默认回溯 7 天
    """
    today_weekday = datetime.datetime.today().weekday() # 0是周一, 3是周四
    
    if today_weekday == 0: # Monday
        return 4
    elif today_weekday == 3: # Thursday
        return 3
    else:
        return 7 # 手动测试时，看一周

days_back = get_search_window()
current_month = datetime.date.today().strftime("%B %Y")

# --- 关键词策略 ---
SEARCH_QUERIES = [
    f"Nu Mexico vs Klar vs Ualá tasas de rendimiento updates {current_month}",
    f"DiDi Card México beneficios y opiniones recientes",
    f"RappiCard vs Stori comentarios quejas usuarios",
    "CNBV regulación fintech México noticias recientes"
]

def search_with_tavily():
    print(f"🔍 [1/3] 正在执行智能搜索 (回溯过去 {days_back} 天)...")
    if not TAVILY_API_KEY:
        return "❌ 错误：未设置 TAVILY_API_KEY"

    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    combined_results = []

    for query in SEARCH_QUERIES:
        print(f"   -> 搜索: {query}")
        try:
            # ✅ 关键点：days 参数是动态的
            response = tavily.search(
                query=query,
                search_depth="advanced",
                topic="general", 
                days=days_back, # 动态时间，天然去重
                max_results=2
            )
            
            for res in response.get('results', []):
                # 过滤掉太短的内容
                if len(res['content']) > 50:
                    combined_results.append(f"【来源: {res['title']}】\n内容: {res['content']}\n链接: {res['url']}")
        
        except Exception as e:
            print(f"      ❌ Tavily 搜索异常: {e}")

    return "\n\n".join(combined_results)

def analyze_with_deepseek(raw_data):
    if not raw_data:
        return f"⚠️ 过去 {days_back} 天内，市场无关于 Nu/DiDi/Rappi 的重大更新。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 进行差异化分析...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    prompt = f"""
    你是一位墨西哥 Fintech 产品经理。
    这是**过去 {days_back} 天**（自上次播报以来）的最新市场情报。
    
    请根据这些信息写一份简报。

    【搜索数据】：
    {raw_data}

    【撰写要求】：
    1. **去重检查**：只关注最近几天的新变化。如果是老生常谈的信息（例如去年的旧闻），请直接忽略。
    2. **如果没有新动态**：请明确回复“本周期内（近{days_back}天）核心竞品无重大费率或功能调整”。
    3. **核心关注**：
       - **Nu/DiDi/Rappi** 的费率(Yield)是否有微调？
       - 社交媒体上是否有突发的**集中投诉**？
    4. **格式**：Markdown。

    请输出报告：
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
            "title": "墨西哥Fintech半周报",
            "text": f"### 🌮 墨西哥 Fintech 半周报 ({datetime.date.today()})\n*覆盖周期：过去 {days_back} 天*\n\n{content}"
        }
    }
    requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))

if __name__ == "__main__":
    raw_news = search_with_tavily()
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
