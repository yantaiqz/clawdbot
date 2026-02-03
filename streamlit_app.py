import streamlit as st
import streamlit.components.v1 as components
from zhipuai import ZhipuAI  # 引入智谱SDK
import datetime
import time
import re
import sqlite3
import uuid
import json
import random

# -------------------------------------------------------------
# --- 0. 页面配置 ---
# -------------------------------------------------------------

st.set_page_config(
    page_title="全球合规风云 | GLM Agent Sim", 
    page_icon="🌏", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# --- 1. Agent 角色定义 ---
# -------------------------------------------------------------

AGENTS = {
    "seller": {
        "name": "深圳大卖-老王",
        "role": "跨境企业主",
        "icon": "👨‍💼",
        "style": "color: #333; background: #e3f2fd;",
        "desc": "焦虑的卖家，关注利润、发货速度。经常抱怨账号被封、资金被冻结，对合规成本很敏感。"
    },
    "legal_inhouse": {
        "name": "总部法务-Lisa",
        "role": "企业合规官",
        "icon": "👩‍💻",
        "style": "color: #333; background: #fff3e0;",
        "desc": "谨慎、负责。需要在业务增长(老王)和全球合规风险之间走钢丝，经常泼冷水。"
    },
    "platform": {
        "name": "平台风控经理",
        "role": "电商平台(Amz/TT)",
        "icon": "📦",
        "style": "color: #333; background: #e8f5e9;",
        "desc": "代表平台方（Amazon/TikTok/Temu），强调平台规则，语气官方且强硬，动不动就警告下架。"
    },
    "lawyer_us": {
        "name": "Mike Ross",
        "role": "美国IP律师",
        "icon": "⚖️",
        "style": "color: #fff; background: #3949ab;",
        "desc": "美国执业律师，专门处理TRO（临时限制令）、专利流氓诉讼和337调查。说话直击要害，强调诉讼风险。"
    },
    "regulator_eu": {
        "name": "欧盟监管局",
        "role": "欧盟官员",
        "icon": "🇪🇺",
        "style": "color: #fff; background: #003399;",
        "desc": "关注GDPR数据安全、VAT税务、以及ESG环保法规（如德国包装法）。"
    },
    "logistics_sea": {
        "name": "印尼通-阿强",
        "role": "东南亚物流商",
        "icon": "🛵",
        "style": "color: #333; background: #fff9c4;",
        "desc": "深耕东南亚（印尼/越南/泰国），熟悉灰关、红灯期、COD货到付款的坑。说话接地气，知道很多潜规则。"
    },
    "cpa_hk": {
        "name": "Jason Lam",
        "role": "香港CPA/财税",
        "icon": "🏙️",
        "style": "color: #333; background: #e0f7fa;",
        "desc": "香港注册会计师，精通离岸账户、资金跨境回流、架构搭建。关注审计和CRS信息交换。"
    },
    "partner_me": {
        "name": "Amir",
        "role": "中东本地保人",
        "icon": "🕌",
        "style": "color: #fff; background: #004d40;",
        "desc": "中东（沙特/阿联酋）本地合作伙伴。强调本地化（保人制度）、伊斯兰合规（Halal认证）和斋月习俗。"
    }
}

# -------------------------------------------------------------
# --- 2. CSS 注入 ---
# -------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
    * { box-sizing: border-box; }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #f4f7f9 !important;
        font-family: 'Noto Sans SC', sans-serif !important;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
    .main .block-container { padding-top: 0 !important; max-width: 900px !important; margin: 0 auto; padding-bottom: 100px !important;}

    .nav-bar {
        background: white; border-bottom: 1px solid #ddd; padding: 15px 20px;
        position: sticky; top: 0; z-index: 999; display: flex; align-items: center; justify-content: space-between;
    }
    .logo-text { font-size: 1.1rem; font-weight: 700; color: #003567; }
    
    .chat-row { display: flex; margin-bottom: 15px; width: 100%; align-items: flex-start; animation: fadeIn 0.5s ease-in; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    .chat-avatar { 
        width: 44px; height: 44px; border-radius: 8px; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 24px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        background: white; border: 1px solid #eee;
    }
    .chat-bubble-container { max-width: 85%; margin-left: 12px; }
    .chat-info { font-size: 0.75rem; color: #666; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;}
    .chat-role-tag { background: #eee; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.7rem;}
    .chat-bubble {
        padding: 12px 16px; border-radius: 0 12px 12px 12px;
        font-size: 0.95rem; line-height: 1.6;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.05);
    }
    .control-panel {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: white; padding: 15px; border-top: 1px solid #ddd;
        display: flex; justify-content: center; gap: 15px; z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    .metric-container { display: flex; gap: 15px; justify-content: center; margin: 20px 0; font-size: 0.8rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# --- 3. 核心逻辑 (GLM-4 版本) ---
# -------------------------------------------------------------

glm_api_key = st.secrets.get("GLM_API_KEY", "") # 获取智谱API Key

def get_system_prompt():
    agents_desc = "\n".join([f"- ID: {k}, 名称: {v['name']}, 角色: {v['role']}, 人设: {v['desc']}" for k, v in AGENTS.items()])
    return f"""
    你是一个全球跨境电商合规社区的模拟器。你需要扮演以下角色进行群聊讨论：
    {agents_desc}

    **任务规则：**
    1. 根据上下文历史，决定**下一个最应该发言的角色**是谁。
    2. 生成该角色的发言内容。内容必须简短有力（50-100字），符合其人设和利益立场。
    3. 话题必须围绕跨境出海的痛点：资金合规、税务稽查、知识产权、物流灰关、本地化壁垒等。
    4. 偶尔可以发生争论。
    5. **严格仅输出 JSON 格式**，格式如下（不要包裹Markdown）：
       {{"agent_id": "agent的ID", "content": "发言内容"}}
    """

def generate_next_turn(history):
    """调用 ZhipuAI GLM-4 生成下一句话"""
    if not glm_api_key:
        st.error("⚠️ 未配置 GLM_API_KEY，请检查 .streamlit/secrets.toml")
        return None
    
    # 初始化客户端
    client = ZhipuAI(api_key=glm_api_key)
    
    # 构建上下文
    history_lines = []
    for msg in history[-12:]:
        role = msg.get('role_name', 'Unknown')
        content = msg.get('content', '')
        history_lines.append(f"[{role}]: {content}")
    history_text = "\n".join(history_lines)

    user_prompt = f"当前对话历史：\n{history_text}\n\n请生成下一条发言（优先选择相关性高或未发言的角色）："
    
    try:
        # 使用 GLM-4-Flash (速度快，适合Agent模拟)
        response = client.chat.completions.create(
            model="glm-4-flash", 
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            top_p=0.8
        )
        
        raw_text = response.choices[0].message.content
        
        # 清洗 JSON
        clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_json)
        return result

    except Exception as e:
        st.toast(f"生成失败: {str(e)[:50]}...", icon="⚠️")
        return None

# -------------------------------------------------------------
# --- 4. 状态管理 ---
# -------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

# 初始化开场白
if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "最近太难了！美国那边TRO搞得人心惶惶，印尼那边听说海关又红灯了，货都卡在港口。兄弟们，咱们这出海怎么全是坑啊？"
    })

# -------------------------------------------------------------
# --- 5. 页面渲染 & 自动滚动 JS ---
# -------------------------------------------------------------

st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌏 Global Compliance | GLM Agent Sim</div>
    <div style="font-size:0.8rem; color:#003567;">● Powered by ZhipuAI</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content-wrapper" id="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    agent_id = msg.get("agent_id", "seller")
    if agent_id not in AGENTS: agent_id = "seller"
    agent_cfg = AGENTS[agent_id]
    
    st.markdown(f"""
    <div class="chat-row">
        <div class="chat-avatar">{agent_cfg['icon']}</div>
        <div class="chat-bubble-container">
            <div class="chat-info">
                <span style="font-weight:bold; color:#333;">{agent_cfg['name']}</span>
                <span class="chat-role-tag">{agent_cfg['role']}</span>
            </div>
            <div class="chat-bubble" style="{agent_cfg['style']}">
                {msg['content']}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

status_placeholder = st.empty()
st.markdown('</div>', unsafe_allow_html=True) 

# 自动滚动 JS
scroll_js = """
<script>
    function scrollToBottom() {
        var mainContainer = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
        if (mainContainer) { mainContainer.scrollTop = mainContainer.scrollHeight; }
    }
    setTimeout(scrollToBottom, 300);
</script>
"""
components.html(scroll_js, height=0, width=0)

# -------------------------------------------------------------
# --- 6. 模拟控制循环 ---
# -------------------------------------------------------------

control_container = st.container()

with control_container:
