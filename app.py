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
    🔥 增强版：同时支持提取 List [...] 和 Object {...}
    """
    text = text.strip()
    
    # 1. 第一招：先试着简单粗暴地去掉 Markdown 标记
    try:
        # 去掉 ```json 和 ``` 以及可能存在的首尾空白
        clean_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        pass # 如果失败，继续尝试第二招

    # 2. 第二招：用正则找列表 [...] (对应7天计划)
    try:
        # re.DOTALL 让点号也能匹配换行符
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass

    # 3. 第三招：用正则找对象 {...} (对应打分分析)
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
        
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
        st.session_state.user_idea = user_idea  # <--- 🔥 必须加这一行！保存点子
        with st.spinner(f'正在结合 {user_mbti} 性格进行深度剖析...'):
            # ... 下面是 prompt ...
            
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

# --- 9. 新增功能：生成执行计划 (v3.0 雏形) ---
    st.markdown("---")
    st.subheader("🗓️ 你的行动蓝图")
    
    # 只有当分析做完，且还没有生成过计划时，才显示按钮
    if st.session_state.analysis_done:
        if "action_plan" not in st.session_state:
            st.session_state.action_plan = None

        if st.button("🚀 把这个计划变成 '7天执行清单'"):
            with st.spinner("AI 正在为你拆解任务，生成甘特图..."):
                # 这是一个新的 Prompt，专门用来拆解任务
                plan_prompt = f"""
                基于之前的创业点子分析和 MBTI 性格（{user_mbti}），
                请为我生成一个极其具体的“7天启动清单”。
                
                要求：
                1. 任务必须非常微小、可执行（Actionable）。
                2. 结合 MBTI 特点（例如 INTJ 多做规划，ENFP 多做社交）。
                3. 每天 1 个核心任务。
                
                请严格返回以下 JSON 格式：
                [
                    {{"day": 1, "task": "具体的任务内容...", "reason": "为什么先做这个"}},
                    {{"day": 2, "task": "...", "reason": "..."}},
                    ...
                ]
                """
                
                # 调用 AI
                # 注意：这里我们把新的 prompt 加入到对话历史中，这样 AI 知道上下文
                st.session_state.messages.append({"role": "user", "content": plan_prompt})
                response_text = call_gemini(st.session_state.messages)
                
                # 提取 JSON
                plan_data = extract_json(response_text)
                
                if plan_data:
                    st.session_state.action_plan = plan_data
                    # 把 AI 的回复也存进去，保持对话连贯
                    st.session_state.messages.append({"role": "assistant", "content": "我已经为你生成了7天行动计划，请看下方👇"})
                    st.rerun()
                else:
                    st.error("生成计划失败，请重试。")
        
        # 展示计划（如果有的话）
        if st.session_state.action_plan:
            st.info("💡 这是一个基于你性格定制的 Launch Plan。请尝试每完成一项就打个勾。")
            
            for item in st.session_state.action_plan:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(f"**Day {item['day']}**")
                with col2:
                    # 使用 checkbox，虽然刷新会重置，但能模拟“打卡”的感觉
                    done = st.checkbox(f"{item['task']}", key=f"task_{item['day']}")
                    if done:
                        st.caption(f"✅ 干得漂亮！(设计意图：{item['reason']})")
                    else:
                        st.caption(f"🎯 目标：{item['reason']}")
            
            st.markdown("---")
            st.success("这只是第一步。真正的监督者功能（保存进度、每日提醒）需要连接数据库。")

# --- 10. (v2.2) 导出功能：把这一页变成文档带走 ---
    st.markdown("---")
    st.subheader("📥 存档你的创业蓝图")
    
    if st.session_state.analysis_done:
        # 1. 拼接要导出的文本内容
        # 确保 user_idea 存在（为了防止极端情况，加个默认值）
        saved_idea = st.session_state.get("user_idea", "未记录")
        report_content = f"""
# 🚀 SoloForce 创业深度评估报告

## 1. 基本信息
- **创业点子**: {saved_idea}
- **创业者性格**: {user_mbti}
- **评估时间**: 2025年...

## 2. 核心打分
- 💰 市场潜力: {st.session_state.current_scores['market']}/100
- 🛠️ 技术难度: {st.session_state.current_scores['tech']}/100
- ⚔️ 竞争程度: {st.session_state.current_scores['competition']}/100

## 3. 深度分析
{st.session_state.messages[1]['content']} 
(注：以上为AI生成的详细分析)

## 4. 7天启动清单 (Action Plan)
"""
        # 如果生成了计划，就拼接到文本里
        if st.session_state.action_plan:
            for item in st.session_state.action_plan:
                report_content += f"- [ ] **Day {item['day']}**: {item['task']} (设计意图: {item['reason']})\n"
        else:
            report_content += "\n(暂未生成行动清单)"

        # 2. 生成下载按钮
        st.download_button(
            label="📄 下载完整报告 (.md)",
            data=report_content,
            file_name="soloforce_plan.md",
            mime="text/markdown"
        )
        st.caption("提示：下载后可以用 Notion、Obsidian 或任何 Markdown 阅读器打开。")

    if st.button("🔄 开始新的分析"):
        st.session_state.messages = []
        st.session_state.analysis_done = False
        st.session_state.current_scores = None
        st.rerun()
