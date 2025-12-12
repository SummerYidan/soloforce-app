import streamlit as st
import requests
import json

# 1. 页面配置
st.set_page_config(page_title="AI 创业导师 (数据版)", page_icon="📊", layout="wide")
st.title("📊 SoloForce: 创业点子毒舌分析器 v1.1")
st.caption("AI 驱动的商业可行性评分系统")

# 2. 获取 API Key
api_key = st.text_input("请输入你的 Google Gemini API Key:", type="password")

# 3. 动态获取模型列表
available_models = []
if api_key:
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(list_url)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('models', []):
                if 'generateContent' in item.get('supportedGenerationMethods', []) and 'gemini' in item['name']:
                    available_models.append(item['name'])
    except:
        pass

if available_models:
    # 默认尝试选 flash 或 pro
    index = 0
    for i, m in enumerate(available_models):
        if 'flash' in m:
            index = i
            break
    selected_model_name = st.selectbox("选择 AI 模型:", available_models, index=index)
else:
    selected_model_name = "models/gemini-1.5-flash" 

# 4. 用户输入
user_idea = st.text_area("输入你的创业想法：", height=100, 
                         placeholder="例如：做一个专门给程序员用的相亲 App...")

# 5. 核心逻辑
if st.button("生成评估报告") and api_key and user_idea:
    
    clean_model_name = selected_model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    # 🔥 核心修改：要求 AI 返回严格的 JSON 格式
    prompt_text = f"""
    你是一个极其严厉的风险投资人。针对用户的想法："{user_idea}"
    
    请严格按照以下 JSON 格式输出，不要包含 Markdown 标记（如 ```json），直接返回纯 JSON 字符串：
    {{
        "market_score": (0-100之间的整数，表示市场潜力),
        "tech_score": (0-100之间的整数，表示技术可行性),
        "competition_score": (0-100之间的整数，表示竞争激烈程度，分越高越卷),
        "critical_review": "这里写你的毒舌点评，列出3个致命弱点",
        "pivot_suggestion": "这里写一个转型建议"
    }}
    """
    
    data = {"contents": [{"parts": [{"text": prompt_text}]}]}
    
    with st.spinner('正在进行多维度打分...'):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                result_json = response.json()
                raw_text = result_json['candidates'][0]['content']['parts'][0]['text']
                
                # 清洗数据，防止 AI 加了 ```json 前缀
                clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                
                # 解析 JSON
                try:
                    analysis = json.loads(clean_text)
                    
                    # --- 可视化展示区域 ---
                    st.success("分析完成！")
                    
                    # 1. 显示三个核心指标
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 市场潜力", f"{analysis['market_score']}/100")
                    col2.metric("🛠️ 技术难度", f"{analysis['tech_score']}/100")
                    # 竞争分越高颜色越红，这里简单展示
                    col3.metric("⚔️ 竞争程度", f"{analysis['competition_score']}/100")
                    
                    # 2. 进度条视觉辅助
                    st.write("综合推荐指数：")
                    # 简单算法：市场分 - 竞争分 + 技术分 (仅作演示)
                    final_score = (analysis['market_score'] + analysis['tech_score'] + (100 - analysis['competition_score'])) / 3
                    st.progress(int(final_score) / 100)
                    
                    # 3. 毒舌点评
                    st.subheader("毒舌点评")
                    st.error(analysis['critical_review'])
                    
                    # 4. 转型建议
                    st.subheader("💡 转型建议")
                    st.info(analysis['pivot_suggestion'])
                    
                except json.JSONDecodeError:
                    st.error("AI 算晕了，返回的格式不对。请重试一下。")
                    with st.expander("查看原始返回"):
                        st.text(raw_text)
            else:
                st.error("请求失败，请检查 API Key。")
                
        except Exception as e:
            st.error(f"发生错误：{e}")
