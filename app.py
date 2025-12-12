import streamlit as st
import requests
import json

# 1. 页面配置
st.set_page_config(page_title="AI 创业导师 (自适应版)", page_icon="🛡️")
st.title("🛡️ SoloForce: 创业点子毒舌分析器")
st.caption("自动检测可用模型，不再盲目猜测")

# 2. 获取 API Key
api_key = st.text_input("请输入你的 Google Gemini API Key:", type="password")

# 3. 动态获取模型列表 (这是新的魔法步骤)
available_models = []
if api_key:
    try:
        # 询问 Google: 你现在有哪些模型可用？
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(list_url)
        
        if resp.status_code == 200:
            data = resp.json()
            # 筛选出支持生成的模型 (名字里带 generateContent 的)
            # 或者简单点，筛选出名字里带 gemini 的
            for item in data.get('models', []):
                if 'generateContent' in item.get('supportedGenerationMethods', []) and 'gemini' in item['name']:
                    available_models.append(item['name'])
        else:
            st.error(f"无法获取模型列表，请检查 API Key 是否正确。错误码: {resp.status_code}")
    except Exception as e:
        st.error(f"连接错误: {e}")

# 4. 让用户选择模型 (如果没有获取到，就默认给一个备用)
if available_models:
    # 默认选第一个，通常是 flash
    selected_model_name = st.selectbox("选择要使用的 AI 模型:", available_models, index=0)
else:
    # 备用方案，万一列表获取失败
    st.warning("⚠️ 没能自动获取到模型列表，将尝试使用默认值。")
    selected_model_name = "models/gemini-1.5-flash" 

# 5. 用户输入区
user_idea = st.text_area("输入你想做的产品或服务：", height=150, 
                         placeholder="例如：我想做一个专门给留学生用的二手家具交易平台...")

# 6. 核心逻辑
if st.button("开始分析") and api_key and user_idea:
    
    with st.spinner(f'正在使用 {selected_model_name} 进行分析...'):
        # 动态构建 URL
        # 注意：selected_model_name 已经是 "models/xxxx" 的格式了，不需要再加 models/
        # 但有些时候 API 返回的是 "models/gemini-1.5-flash"，而 URL 需要 .../models/gemini-1.5-flash:generateContent
        
        # 修正 URL 拼接逻辑
        clean_model_name = selected_model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
        
        headers = {'Content-Type': 'application/json'}
        
        prompt_text = f"""
        你是一个极其严厉、说话直接的创业导师。
        请针对用户的想法："{user_idea}"
        
        请做三件事：
        1. 列出 3 个最致命的弱点。
        2. 给出一个 pivot (转型) 建议。
        3. 请用 Markdown 格式输出，条理清晰。
        """
        
        data = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            
            if response.status_code == 200:
                result_json = response.json()
                try:
                    ai_text = result_json['candidates'][0]['content']['parts'][0]['text']
                    st.markdown("### 📊 分析报告")
                    st.markdown(ai_text)
                    st.balloons() # 成功撒花！
                    st.success("分析完成！")
                except:
                    st.warning("结果生成了，但解析有点问题，原始内容如下：")
                    st.json(result_json)
            else:
                st.error(f"请求失败，状态码：{response.status_code}")
                st.code(response.text) # 把错误详情打印出来
                
        except Exception as e:
            st.error(f"发生错误：{e}")