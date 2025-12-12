import streamlit as st
import requests
import json

# --- 1. 页面配置 ---
st.set_page_config(page_title="SoloForce AI 顾问 (v2.0)", page_icon="🧠", layout="wide")

# --- 2. 初始化 Session State (这是让网页有记忆的关键) ---
# 如果是第一次打开，初始化聊天记录和分析状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "current_scores" not in st.session_state:
    st.session_state.current_scores = None

# --- 3. 侧边栏配置 (API Key & MBTI) ---
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
    
    st.info(f"💡 AI 将会根据 {user_mbti.split(' ')[0]} 的特质为你定制创业路径。")

    # 获取模型列表 (逻辑同之前)
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
    
    selected_model_name = "models/gemini-1.5-flash" # 默认值
    if available_models:
        # 优先找 flash 或 pro
        index = 0
        for i, m in enumerate(available_models):
            if 'flash' in m:
                index = i 
                break
        selected_model_name = st.selectbox("选择模型:", available_models, index=index)

# --- 4. 主界面标题 ---
st.title("🧠 SoloForce: AI 深度创业咨询")
st.caption(f"基于 {user_mbti} 性格特质的个性化分析与指导")

# --- 5. 核心功能函数 (调用 API) ---
def call_gemini(messages):
    clean_model_name = selected_model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    # 把聊天记录转换成 Google API 需要的格式
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

# --- 6. 初始分析区域 ---
if not st.session_state.analysis_done:
    user_idea = st.text_area("输入你的创业想法：", height=100, placeholder="例如：我想做一个帮助内向者练习演讲的 VR 工具...")
    
    if st.button("开始深度分析") and api_key and user_idea:
        with st.spinner('正在结合你的 MBTI 性格进行深度剖析...'):
            # 构建超级详细的 Prompt
            initial_prompt = f"""
            你是一位精通商业分析和心理学的创业导师。
            
            用户信息：
            - 创业点子："{user_idea}"
            - MBTI 人格："{user_mbti}"
            
            请完成以下任务：
            1. **打分**：给出市场、技术、竞争三个维度的打分 (0-100)。
            2. **深度分析**：针对每个分数，详细解释“为什么这么打分”，指出具体依据。
            3. **MBTI 适配建议**：结合用户的 MBTI 性格，给出具体的执行建议。
               - 例如：如果是 INTJ，重点讲系统架构和长期战略；如果是 ENFP，重点讲社群运营和愿景。
               - 推荐一种最适合该性格的“单人创业工作流”。
            
            【重要】请严格按照以下 JSON 格式返回，不要加 markdown 标记：
            {{
                "scores": {{
                    "market": 85,
                    "tech": 60,
                    "competition": 90
                }},
                "analysis_text": "这里放入详细的打分理由分析...",
                "mbti_advice": "这里放入针对 MBTI 的建议..."
            }}
            """
            
            # 调用 API
            response_text = call_gemini([{"role": "user", "content": initial_prompt}])
            
            # 解析结果
            try:
                # 清洗可能存在的 markdown 标记
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                result_data = json.loads(clean_text)
                
                # 保存到 Session State
                st.session_state.analysis_done = True
                st.session_state.current_scores = result_data['scores']
                
                # 将分析结果存入聊天记录的第一条
                st.session_state.messages.append({"role": "user", "content": f"我的点子是：{user_idea}，我是 {user_mbti}"})
                
                # 构建一个漂亮的回复显示
                ai_response_content = f"""
### 📊 深度评估报告

**💰 市场潜力**: {result_data['scores']['market']}/100
**🛠️ 技术难度**: {result_data['scores']['tech']}/100
**⚔️ 竞争程度**: {result_data['scores']['competition']}/100

---
### 🧐 为什么这么打分？
{result_data['analysis_text']}

---
### 🧘 为 {user_mbti} 定制的创业指南
{result_data['mbti_advice']}
                """
                st.session_state.messages.append({"role": "assistant", "content": ai_response_content})
                
                # 强制刷新页面以进入聊天模式
                st.rerun()
                
            except Exception as e:
                st.error("解析数据失败，请重试。")
                st.expander("查看原始返回").write(response_text)

# --- 7. 分析完成后的展示与聊天区域 ---
else:
    # 顶部显示分数仪表盘 (固定显示)
    if st.session_state.current_scores:
        s = st.session_state.current_scores
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 市场潜力", f"{s['market']}/100")
        c2.metric("🛠️ 技术难度", f"{s['tech']}/100")
        c3.metric("⚔️ 竞争程度", f"{s['competition']}/100")
        st.markdown("---")

    # 显示聊天历史
    for msg in st.session_state.messages:
        if msg["role"] != "user": # 第一条用户输入不重复显示在气泡里，只显示 AI 回复
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        elif msg == st.session_state.messages[0]:
            pass # 跳过初始 prompt 的显示
        else:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 聊天输入框
    if prompt := st.chat_input("针对以上分析，你有什么想追问的？(例如：我该怎么改进技术分？)"):
        # 1. 显示用户问题
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. AI 思考并回答
        with st.chat_message("assistant"):
            with st.spinner("AI 正在思考..."):
                response = call_gemini(st.session_state.messages)
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    # 重置按钮
    if st.button("🔄 开始新的分析"):
        st.session_state.messages = []
        st.session_state.analysis_done = False
        st.session_state.current_scores = None
        st.rerun()
