import google.generativeai as genai
import streamlit as st
import streamlit.components.v1 as components
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
    page_title="全球合规风云 | Gemini Agent Sim",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# --- 1. Gemini 模型初始化配置 ---
# -------------------------------------------------------------
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
else:
    st.error("⚠️ 未配置 Gemini_API_KEY，请检查 .streamlit/secrets.toml 配置")

# -------------------------------------------------------------
# --- 2. Agent 角色定义 ---
# -------------------------------------------------------------
AGENTS = {
    "seller": {
        "name": "深圳大卖-老王",
        "role": "跨境企业主",
        "icon": "👨‍💼",
        "style": "color: #333; background: #e3f2fd;",
        "desc": "焦虑的卖家，关注利润。经常抱怨账号被封、资金被冻结，对合规成本敏感。"
    },
    "legal_inhouse": {
        "name": "总部法务-Lisa",
        "role": "企业合规官",
        "icon": "👩‍💻",
        "style": "color: #333; background: #fff3e0;",
        "desc": "谨慎负责。在业务增长和全球风险之间走钢丝，经常泼冷水提示风险。"
    },
    "platform": {
        "name": "平台风控经理",
        "role": "电商平台(Amz/TT)",
        "icon": "📦",
        "style": "color: #333; background: #e8f5e9;",
        "desc": "代表平台方，强调规则，语气官方且强硬，动辄下架警告。"
    },
    "lawyer_us": {
        "name": "Mike Ross",
        "role": "美国IP律师",
        "icon": "⚖️",
        "style": "color: #fff; background: #3949ab;",
        "desc": "美国律师，擅长处理TRO、专利诉讼。说话直击要害，强调法律赔偿。"
    },
    "regulator_eu": {
        "name": "欧盟监管局",
        "role": "欧盟官员",
        "icon": "🇪🇺",
        "style": "color: #fff; background: #003399;",
        "desc": "关注GDPR数据安全、欧盟VAT税务及包装法等合规审计。"
    },
    "logistics_sea": {
        "name": "印尼通-阿强",
        "role": "东南亚物流商",
        "icon": "🛵",
        "style": "color: #333; background: #fff9c4;",
        "desc": "深谙印尼、越南红灯期和清关潜规则。说话接地气，熟悉COD风险。"
    },
    "cpa_hk": {
        "name": "Jason Lam",
        "role": "香港CPA/财税",
        "icon": "🏙️",
        "style": "color: #333; background: #e0f7fa;",
        "desc": "精通离岸账户和架构搭建，关注CRS审计和合法资金回流。"
    },
    "partner_me": {
        "name": "Amir",
        "role": "中东本地保人",
        "icon": "🕌",
        "style": "color: #fff; background: #004d40;",
        "desc": "中东本地合作伙伴，强调本地化保人制度、Halal认证和斋月习俗。"
    }
}

# -------------------------------------------------------------
# --- 3. CSS 注入 ---
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
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# --- 4. 核心逻辑 (Gemini 修复版) ---
# -------------------------------------------------------------
def get_system_prompt():
    agents_desc = "\n".join([f"- {k}: {v['name']} ({v['role']}), {v['desc']}" for k, v in AGENTS.items()])
    return f"""你是一个全球跨境电商合规社区模拟器。根据上下文，选择一个角色生成下一条发言。
要求：
1. 仅输出标准JSON对象。
2. 发言50-100字，符合人设立场。
3. 话题围绕资金合规、税务、知识产权、清关等。
4. 格式：{{"agent_id":"角色ID", "content":"内容"}}
角色列表：
{agents_desc}"""

def generate_next_turn(history):
    if not gemini_api_key: return None
    
    # 初始化模型并传入 System Instruction
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=get_system_prompt()
    )

    history_lines = []
    for msg in history[-12:]:
        role = msg.get('role_name', 'Unknown')
        content = msg.get('content', '')
        history_lines.append(f"[{role}]: {content}")
    history_text = "\n".join(history_lines)

    try:
        # 配置 JSON 输出模式
        response = model.generate_content(
            f"对话历史：\n{history_text}\n\n请生成下一条讨论内容。",
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.8,
            )
        )
        
        if not response.text:
            raise ValueError("Empty Response")

        # 清洗可能存在的 Markdown 标签（双保险）
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)

        if result.get("agent_id") in AGENTS:
            return result
        else:
            raise ValueError("Invalid Agent ID")

    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        st.toast("AI 生成故障，切换至预设剧本...", icon="🔄")

    # ========== 降级方案 (Fallback) ==========
    fid = random.choice(list(AGENTS.keys()))
    fcontents = {
        "seller": "真的难顶，美国TRO之后，我印尼的号也被查了，大家怎么规避？",
        "legal_inhouse": "Lisa 建议大家先把合规审计做了，别等收到法院传票才着急。",
        "platform": "请各位卖家注意，合规是平台长期经营的唯一标准。",
        "lawyer_us": "商标和外观专利是美国站的重灾区，一定要提前布局。",
        "regulator_eu": "欧盟VAT税务稽查是认真的，历史欠款建议尽快补缴。",
        "logistics_sea": "东南亚那边又开始红灯了，走正规贸易才是正道。",
        "cpa_hk": "资金回流一定要有贸易闭环证据，现在银行查得很严。",
        "partner_me": "中东市场本地化很重要，一定要找靠谱的本地保人合作。"
    }
    return {"agent_id": fid, "content": fcontents[fid]}

# -------------------------------------------------------------
# --- 5. 状态管理 ---
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "最近出海圈太动荡了，美国TRO之后又是印尼红灯期，大家还好吗？"
    })

# -------------------------------------------------------------
# --- 6. 渲染界面 ---
# -------------------------------------------------------------
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌏 Global Compliance | Agent Community</div>
    <div style="font-size:0.8rem; color:#003567;">● Powered by Google Gemini 1.5</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content-wrapper" id="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    agent_id = msg.get("agent_id", "seller")
    agent_cfg = AGENTS.get(agent_id, AGENTS["seller"])
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

# 自动滚动脚本
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
# --- 7. 模拟控制 ---
# -------------------------------------------------------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.session_state.simulation_active:
        if st.button("⏹ 停止模拟 (Pause)", use_container_width=True):
            st.session_state.simulation_active = False
            st.rerun()
    else:
        if st.button("▶️ 开始全球合规模拟", use_container_width=True, type="primary"):
            st.session_state.simulation_active = True
            st.rerun()

if st.session_state.simulation_active:
    wait_time = random.randint(5, 12)
    prog_bar = status_placeholder.progress(0, text="Agent 正在输入...")
    for i in range(wait_time):
        time.sleep(1)
        prog_bar.progress((i + 1) / wait_time, text=f"下一位发言者准备中... ({wait_time - i}s)")
    
    new_turn = generate_next_turn(st.session_state.messages)
    if new_turn:
        st.session_state.messages.append({
            "agent_id": new_turn["agent_id"],
            "role_name": AGENTS[new_turn["agent_id"]]["name"],
            "content": new_turn["content"]
        })
        st.rerun()

# -------------------------------------------------------------
# --- 8. 访客统计 (隐藏数据库逻辑) ---
# -------------------------------------------------------------
DB_FILE = "stats_sim.db"
def track_stats():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
        today = datetime.datetime.utcnow().date().isoformat()
        c.execute("INSERT OR IGNORE INTO daily_traffic VALUES (?, 0)", (today,))
        c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today,))
        conn.commit()
        conn.close()
    except: pass

track_stats()
