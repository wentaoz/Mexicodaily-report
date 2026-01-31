import os
import json
import requests
import datetime
from duckduckgo_search import DDGS
from openai import OpenAI

# --- 配置区域 ---
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com") 
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

# 获取当前月份，例如 "February 2026"
current_month_str = datetime.date.today().strftime("%Y") 

# --- 关键词策略：覆盖 利率、营销、舆情、竞品 ---
SEARCH_QUERIES = [
    # 1. 💰 收益率大战 (最容易搜到数据)
    f"Nu Mexico vs Klar vs Stori tasas de rendimiento {current_month_str}",
    
    # 2. 🎁 营销与羊毛 (Cashback/Promos)
    f"Mejores tarjetas crédito fintech México cashback promociones {current_month_str}",
    
    # 3. 🗣 真实评价与吐槽 (Reviews)
    f"RappiCard Mexico vs DiDi Card opiniones quejas {current_month_str}",
    
    # 4. 🚀 竞品新功能 (Features)
    f"Nu Mexico nuevas funciones app actualización {current_month_str}",
    
    # 5. ⚖️ 监管 (Regulation)
    f"CNBV ley fintech México cambios {current_month_str}"
]

def search_web_duckduckgo():
    print("🔍 [1/3] 正在使用 DuckDuckGo 广角扫描 (过去1个月)...")
    results = []
    
    # 尝试连接 DuckDuckGo
    try:
        with DDGS() as ddgs:
            for query in SEARCH_QUERIES:
                print(f"   -> 扫描: {query}")
                try:
                    # backend="html": 关键参数，模拟浏览器访问，防止被 GitHub 封 IP
                    # timelimit="m": 过去一个月，保证有内容
                    keywords_results = list(ddgs.text(query, max_results=2, backend="html", timelimit="m"))
                    
                    if not keywords_results:
                        print(f"      ⚠️ 该话题暂无数据")
                        continue

                    for r in keywords_results:
                        # 格式化数据
                        results.append(f"【话题: {query}】\n标题: {r['title']}\n摘要: {r['body']}\n链接: {r['href']}")
                        
                except Exception as e:
                    print(f"      ❌ 单个搜索报错 (可能是网络波动): {e}")
                    
    except Exception as e:
        print(f"❌ DuckDuckGo 组件严重错误: {e}")
    
    return "\n\n".join(results)

def analyze_with_deepseek(raw_data):
    # 如果完全搜不到东西 (被封IP的情况)
    if not raw_data:
        return "⚠️ **搜索受限警告**：DuckDuckGo 暂时屏蔽了 GitHub 的连接，未获取到今日数据。建议稍后重试。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 进行运营分析...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    prompt = f"""
    你是一位墨西哥 Fintech 运营专家。请根据以下【过去30天】的搜索数据，写一份**市场运营动向日报**。

    【搜索数据】：
    {raw_data}

    【撰写指令】：
    1. **挖掘细节**：即使没有大新闻，也要找出“谁家的利息变了”、“谁家最近有促销”、“用户在骂谁”。
    2. **分类汇报**：
       - **💰 收益与费率** (Yield & Rates)
       - **🎁 营销活动** (Promotions)
       - **🗣 用户舆情** (Sentiment)
       - **🚀 产品动态** (Features)
    3. **去伪存真**：忽略无关广告。
    4. **语气**：专业、客观。

    请输出 Markdown 格式报告：
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
            "title": "墨西哥Fintech情报",
            "text": f"### 🌮 墨西哥 Fintech 市场监测\n\n{content}"
        }
    }
    requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))

if __name__ == "__main__":
    raw_news = search_web_duckduckgo()
    # 打印一下结果长度，方便您在 GitHub 日志里看有没有搜到东西
    print(f"📊 搜索结果长度: {len(raw_news)} 字符")
    
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
