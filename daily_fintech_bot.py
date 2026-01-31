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

# 当前年份
current_year = datetime.date.today().year

# --- 2. 关键词升级：加入“测评”、“对比”、“投诉” ---
# 这样即使没有新功能，也能看到用户在讨论什么
SEARCH_KEYWORDS = [
    # 1. 核心竞品动态 (Feature)
    f"Nu Mexico vs Stori vs RappiCard features {current_year}",
    f"DiDi Card Mexico ventajas y desventajas {current_year}", # 优缺点
    
    # 2. 用户真实口碑 (Reviews/Complaints) - PM最爱看的信息
    f"Nu Mexico opiniones usuarios {current_year}", 
    f"RappiCard Mexico quejas recientes", # 最近的投诉
    f"Stori tarjeta crédito comentarios",
    
    # 3. 市场大盘与榜单
    f"Mejores tarjetas de crédito fintech México {current_year}", # 最佳信用卡榜单
    f"CNBV regulación fintech cambios {current_year}"
]

def search_web():
    print(f"🔍 [1/3] 正在进行深度市场调研 (过去1个月)...")
    results = []
    
    try:
        with DDGS() as ddgs:
            for keyword in SEARCH_KEYWORDS:
                print(f"   -> 调研: {keyword}")
                try:
                    # ✅ 修改点：timelimit="m" (过去一个月)，扩大搜索范围
                    # max_results=2 保持不变，防止信息太多
                    keywords_results = list(ddgs.text(keyword, max_results=2, backend="html", timelimit="m"))
                    
                    if not keywords_results:
                        print(f"      ⚠️ '{keyword}' 无近期数据")
                        continue

                    for r in keywords_results:
                        results.append(f"【主题: {keyword}】\n标题: {r['title']}\n摘要: {r['body']}\n链接: {r['href']}")
                        
                except Exception as e:
                    print(f"      ❌ 搜索跳过: {e}")
                    
    except Exception as e:
        print(f"❌ 搜索组件异常: {e}")
    
    return "\n\n".join(results)

def analyze_with_deepseek(raw_data):
    if not raw_data:
        return "📅 最近一个月市场非常平静，主要竞品无重大公开动态或热门讨论。"

    print("🧠 [2/3] 正在呼叫 DeepSeek 进行深度总结...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    # --- Prompt 升级：要求分析趋势和口碑 ---
    prompt = f"""
    你是一位资深的墨西哥Fintech产品专家。
    请根据以下【过去一个月】的搜索数据，写一份**市场深度观察日报**。
    
    即使没有突发新闻，也请从“用户评论”、“功能对比”或“优缺点分析”中提炼价值。

    搜索数据：
    {raw_data}

    **撰写要求 (Markdown格式)**：
    1. **🔥 市场热点/竞品大动作**：如果有发布新功能、融资或监管新闻，放在第一位。
    2. **🗣️ 用户口碑与槽点 (重点)**：用户最近在夸谁？骂谁？(例如：Rappi的服务态度、Nu的额度问题、Stori的利率)。
    3. **🛡️ 监管风向**：CNBV 或政策是否有新动向。
    4. **💡 产品经理洞察**：根据以上信息，给出一句简短的策略建议。

    注意：保持客观，引用必须附带链接。
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, # 稍微增加一点创造性
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
            "title": "墨西哥Fintech市场观察",
            "text": f"### 🌮 墨西哥 Fintech 市场观察 ({datetime.date.today()})\n\n{content}"
        }
    }
    requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))

if __name__ == "__main__":
    raw_news = search_web()
    final_report = analyze_with_deepseek(raw_news)
    send_dingtalk(final_report)
