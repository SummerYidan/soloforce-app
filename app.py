import streamlit as st
import requests
import json
import re # 引入正则表达式库，用来提取 JSON

# --- 1. 页面配置 ---
st.set_page_config(page_title="SoloForce AI 顾问 (v2.1)", page_icon="🧠", layout="wide")

# --- 2. 初始化 Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "current_scores" not in st.session_state:
    st.session_state.current_scores = None

# --- 3. 辅助函数：强力 JSON 提取器 (关键修复) ---
def extract_json(text):
    """
    无论 AI 返回什么乱七八糟的文本，只提取第一个 { 到最后一个 } 之间的内容
    """
    try:
        # 1. 尝试直接解析
        return json.loads(text)
    except:
        # 2. 如果失败，使用正则表达式寻找 JSON 对象
        # 寻找第一个 '{' 和最后一个 '}'
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group()
            try:
                return json.loads(json_str)
            except:
                return None
        return None

# --- 4. 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = st.text_input("Google Gemini API Key:", type="password")
    
    st.markdown("---")
    st.subheader("👤 你的性格档案")
    mbti_options = ["INTJ (建筑师)", "INTP (逻辑学家)", "ENTJ (指挥官)", "ENTP (辩论家)",
                    "INFJ (提倡者)", "INFP (调停者)", "ENFJ (主人公)", "ENFP (竞选者)",
                    "ISTJ (物流师)", "ISFJ (守卫者)", "ESTJ (总经理)", "ESFJ (执政官)",
                    "ISTP (鉴赏家)", "ISFP (探险家)", "ESTP (企业家)", "ESFP (表演者)"]
    user_mbti = st.selectbox("选择你的 MBTI 人格类型:", mbti_options, index=0)
    
    # 获取模型列表
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
    
    selected_model_name = "models/gemini-1.5-flash"
    if available_models:
        index = 0
        for i, m in enumerate(available_models):
            if 'flash' in m:
                index = i 
                break
        selected_model_name = st.selectbox("选择模型:", available_models, index=index)

# --- 5. 主界面标题 ---
st.title("🧠 SoloForce: AI 深度创业咨询")
st.caption(f"基于 {user_mbti} 性格特质的个性化分析与指导")

# --- 6. 核心 API 调用函数 ---
def call_gemini(messages):
    clean_model_name = selected_model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    contents_payload = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents_payload.append({"role": role, "parts": [{"text": msg["content"]}]})
        
    data = {"contents": contents_payload}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {e}"

# --- 7. 初始分析逻辑 ---
if not st.session_state.analysis_done:
    user_idea = st.text_area("输入你的创业想法：", height=100, placeholder="例如：我想做一个帮助内向者练习演讲的 VR 工具...")
    
    if st.button("开始深度分析") and api_key and user_idea:
        with st.spinner(f'正在结合 {user_mbti} 性格进行深度剖析...'):
            
            initial_prompt = f"""
            你是一位精通商业分析和心理学的创业导师。
            
            用户信息：
            - 创业点子："{user_idea}"
            - MBTI 人格："{user_mbti}"
            
            请完成以下任务，并严格以 JSON 格式输出：
            1. 打分 (market, tech, competition)
            2. analysis_text: 详细解释打分理由。
            3. mbti_advice: 针对该 MBTI 的具体建议。
            
            JSON 格式示例：
            {{
                "scores": {{ "market": 80, "tech": 50, "competition": 90 }},
                "analysis_text": "分析内容...",
                "mbti_advice": "建议内容..."
            }}
            """
            
            response_text = call_gemini([{"role": "user", "content": initial_prompt}])
            
            # 🔥 使用新的提取函数
            result_data = extract_json(response_text)
            
            if result_data:
                st.session_state.analysis_done = True
                st.session_state.current_scores = result_data.get('scores', {'market':0, 'tech':0, 'competition':0})
                
                # 保存历史
                st.session_state.messages.append({"role": "user", "content": f"我的点子是：{user_idea}，我是 {user_mbti}"})
                
                ai_response_content = f"""
### 📊 深度评估报告

**💰 市场潜力**: {st.session_state.current_scores['market']}/100
**🛠️ 技术难度**: {st.session_state.current_scores['tech']}/100
**⚔️ 竞争程度**: {st.session_state.current_scores['competition']}/100

---
### 🧐 为什么这么打分？
{result_data.get('analysis_text', '解析文本失败')}

---
### 🧘 为 {user_mbti} 定制的创业指南
{result_data.get('mbti_advice', '解析建议失败')}
                """
                st.session_state.messages.append({"role": "assistant", "content": ai_response_content})
                st.rerun()
            else:
                st.error("分析生成了，但格式有点乱，正在重试...请再点一次按钮。")
                with st.expander("查看 AI 的原始回复 (Debugging)"):
                    st.text(response_text)

# --- 8. 结果展示与聊天 ---
else:
    # 顶部仪表盘
    if st.session_state.current_scores:
        s = st.session_state.current_scores
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 市场潜力", f"{s['market']}/100")
        c2.metric("🛠️ 技术难度", f"{s['tech']}/100")
        c3.metric("⚔️ 竞争程度", f"{s['competition']}/100")
        st.markdown("---")

    # 聊天记录
    for msg in st.session_state.messages:
        if msg["role"] != "user":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        elif msg == st.session_state.messages[0]:
            pass
        else:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 聊天输入
    if prompt := st.chat_input("想继续追问什么？"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = call_gemini(st.session_state.messages)
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    if st.button("🔄 开始新的分析"):
        st.session_state.messages = []
        st.session_state.analysis_done = False
        st.session_state.current_scores = None
        st.rerun()
