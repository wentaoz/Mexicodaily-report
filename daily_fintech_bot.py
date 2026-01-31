import os
import json
import requests
from duckduckgo_search import DDGS  # 用于真实搜索
from openai import OpenAI  # 用于调用大模型进行总结

# --- 1. 配置区域 (从环境变量读取，安全第一) ---
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1") # 如果用别的模型(如DeepSeek/Gemini)，改这里
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o") # 指定模型

# 定义我们要关注的关键词
SEARCH_KEYWORDS = [
    "Nu Mexico new features app design 2025",
    "Stori Mexico credit card update",
    "RappiCard Mexico changes",
    "Comisión Nacional Bancaria y de Valores Mexico regulation fintech"
]

# --- 2. 核心功能：搜索 ---
def search_web():
    print("🔍 正在全网搜索最新情报...")
    results = []
    # 使用 DuckDuckGo 免费搜索
    with DDGS() as ddgs:
        for keyword in SEARCH_KEYWORDS:
            try:
                # 每个关键词抓取前 3 条最新结果
                print(f"  - 搜索: {keyword}")
                keywords_results = list(ddgs.text(keyword, max_results=3))
                for r in keywords_results:
                    results.append(f"标题: {r['title']}\n链接: {r['href']}\n摘要: {r['body']}")
            except Exception as e:
                print(f"  ❌ 搜索 '{keyword}' 时出错: {e}")
    
    return "\n---\n".join(results)

# --- 3. 核心功能：AI 分析 (大脑) ---
def analyze_content(raw_data):
    if not raw_data:
        return "⚠️ 今日未搜索到有效信息，请检查搜索源。"

    print("🧠 正在调用 AI 进行深度分析...")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    # 专门为 PM 设计的 Prompt
    prompt = f"""
    你是一位专业的Fintech产品经理，专注于墨西哥市场。
    请阅读以下从网络抓取的搜索结果（可能包含噪音），为我撰写一份【墨西哥竞品每日情报】。

    搜索结果数据：
    {raw_data}

    撰写要求：
    1. **语言**：使用中文。
    2. **格式**：Markdown。
    3. **核心关注点**：
       - **竞品动向**：Nu, Stori, Rappi 等是否有新功能、新UI设计、新交互流程？(重点提取具体的设计细节)
       - **合规风向**：CNBV 或墨西哥政府是否有新规定？
    4. **去噪**：忽略无关广告、旧闻（超过1年的）和没有实质内容的软文。
    5. **语气**：专业、简练、直接。
    6. **结尾**：必须列出1-2个最有价值的原文来源链接。

    请直接输出报告内容。
    """

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 分析失败: {e}"

# --- 4. 核心功能：发送钉钉 ---
def send_dingtalk(content):
    print("🚀 正在发送到钉钉群...")
    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "🇲🇽 墨西哥Fintech日报",
            "text": f"### 🇲🇽 墨西哥Fintech市场日报\n\n{content}"
        }
    }
    requests.post(DINGTALK_WEBHOOK, headers=headers, data=json.dumps(data))

# --- 主程序入口 ---
if __name__ == "__main__":
    # 1. 获取原始信息
    raw_search_data = search_web()
    
    # 2. AI 提炼
    final_report = analyze_content(raw_search_data)
    
    # 3. 推送
    send_dingtalk(final_report)
    print("✅ 任务完成！")
