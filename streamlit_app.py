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
# 从Streamlit Secrets获取Gemini API Key（本地运行需配置 .streamlit/secrets.toml）
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    # 初始化Gemini模型（选用flash版本，兼顾速度和效果，适合Agent模拟）
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash" )
else:
    gemini_model = None
    st.error("⚠️ 未配置 Gemini_API_KEY，请检查 .streamlit/secrets.toml 配置")

# -------------------------------------------------------------
# --- 2. Agent 角色定义（保留原有8类角色，无修改）---
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
# --- 3. CSS 注入（仅修改Powered by标识，其余保留）---
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
# --- 4. 核心逻辑 (Gemini 修复版) ---
# -------------------------------------------------------------
def get_system_prompt():
    """生成Gemini系统提示词，保留原有角色规则"""
    agents_desc = "\n".join([f"- ID: {k}, 名称: {v['name']}, 角色: {v['role']}, 人设: {v['desc']}" for k, v in AGENTS.items()])
    return f"""
    你是一个全球跨境电商合规社区的模拟器。你需要扮演以下角色进行群聊讨论：
    {agents_desc}

    **任务规则：**
    1. 根据上下文历史，决定下一个最应该发言的角色。
    2. 生成该角色的发言内容（50-100字），符合其人设。
    3. 话题围绕跨境出海痛点。
    4. 必须输出 JSON。格式如下：
    {{"agent_id": "agent的ID", "content": "发言内容"}}
    """

def generate_next_turn(history):
    """调用Gemini生成下一句Agent发言"""
    if not gemini_api_key:
        st.toast("⚠️ Gemini API Key 未配置", icon="❌")
        return None
    
    # 修正点 1: 使用正确的模型名称 (1.5-flash 是目前最稳的)
    # 修正点 2: 建议将 System Instruction 放在初始化中
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=get_system_prompt()
    )
    
    # 构建对话历史上下文
    history_lines = []
    for msg in history[-12:]:
        role = msg.get('role_name', 'Unknown')
        content = msg.get('content', '')
        history_lines.append(f"[{role}]: {content}")
    history_text = "\n".join(history_lines)

    user_prompt = f"当前对话历史：\n{history_text}\n\n请生成下一条发言。"
    
    try:
        # 修正点 3: 简化的调用方式，配合 GenerationConfig
        response = model.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.8,
                top_p=0.9,
            )
        )
        
        # 修正点 4: 检查结果是否存在
        if not response.text:
            raise ValueError("Empty response")
            
        raw_text = response.text.strip()
        
        # 解析JSON
        result = json.loads(raw_text)

        # 校验必要字段
        if not result.get("agent_id") or not result.get("content"):
            raise ValueError("JSON缺少必要字段")

        return result

    except Exception as e:
        # 仅在调试时打开，生产环境可换成 st.toast
        print(f"Gemini API Error: {e}") 
        st.toast(f"API 异常: {str(e)[:20]}...", icon="⚠️")

    # ========== 降级机制 (保持不变) ==========
    fallback_agent_id = random.choice(list(AGENTS.keys()))
    fallback_contents = {
        "seller": "最近平台审核越来越严了，大家有没有什么经验？",
        "legal_inhouse": "建议先自查风险，合规才是长久之计。",
        "platform": "请各位严格遵守规则，以免影响店铺运营。",
        "lawyer_us": "美国站的知识产权风险一定要重视。",
        "regulator_eu": "欧盟VAT最近查得很凶，别抱侥幸心理。",
        "logistics_sea": "东南亚清关最近变慢了，大家提前做好准备。",
        "cpa_hk": "审计报税要按时，离岸账户被查就麻烦了。",
        "partner_me": "中东市场本地保人合作一定要选靠谱的。"
    }

    return {
        "agent_id": fallback_agent_id,
        "content": fallback_contents.get(fallback_agent_id, "同步中...")
    }


# -------------------------------------------------------------
# --- 5. 状态管理（保留原有逻辑，无修改）---
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

# 初始化开场白（保留原有内容）
if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "最近太难了！美国那边TRO搞得人心惶惶，印尼那边听说海关又红灯了，货都卡在港口。兄弟们，咱们这出海怎么全是坑啊？"
    })

# -------------------------------------------------------------
# --- 6. 页面渲染 & 自动滚动 JS（仅修改Powered by标识）---
# -------------------------------------------------------------
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌏 Global Compliance | Gemini Agent Sim</div>
    <div style="font-size:0.8rem; color:#003567;">● Powered by Google Gemini</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content-wrapper" id="chat-container">', unsafe_allow_html=True)

# 渲染聊天消息（保留原有样式，无修改）
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

# 自动滚动 JS（保留原有逻辑，无修改）
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
# --- 7. 模拟控制循环（保留原有逻辑，无修改）---
# -------------------------------------------------------------
control_container = st.container()

with control_container:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.simulation_active:
            if st.button("⏹ 停止模拟 (Pause)", use_container_width=True, type="secondary"):
                st.session_state.simulation_active = False
                st.rerun()
        else:
            if st.button("▶️ 开始 Gemini 驱动模拟", use_container_width=True, type="primary"):
                st.session_state.simulation_active = True
                st.rerun()

if st.session_state.simulation_active:
    wait_seconds = random.randint(5, 15)
    prog_bar = status_placeholder.progress(0, text="Agents 正在思考中...")
    
    for i in range(wait_seconds):
        time.sleep(1)
        prog_bar.progress((i + 1) / wait_seconds, text=f"下一位专家正在输入... ({wait_seconds - i}s)")
    
    status_placeholder.empty()

    new_turn = generate_next_turn(st.session_state.messages)
    
    if new_turn:
        agent_id = new_turn.get("agent_id")
        if agent_id not in AGENTS:
            agent_id = random.choice(list(AGENTS.keys()))
        
        st.session_state.messages.append({
            "agent_id": agent_id,
            "role_name": AGENTS[agent_id]["name"],
            "content": new_turn.get("content")
        })
        st.rerun()
    else:
        st.session_state.simulation_active = False
        st.error("生成回复失败，模拟已暂停。")

# -------------------------------------------------------------
# --- 8. 访客统计（保留原有逻辑，仅修改数据库文件名）---
# -------------------------------------------------------------
DB_FILE = "visit_stats_gemini.db"  # 区分Gemini版本统计数据

def track_and_get_stats():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS visitors (visitor_id TEXT PRIMARY KEY, first_visit_date TEXT, last_visit_date TEXT)''')
        try: c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
        except: pass

        today_str = datetime.datetime.utcnow().date().isoformat()
        if "visitor_id" not in st.session_state: st.session_state["visitor_id"] = str(uuid.uuid4())
        
        if "has_counted" not in st.session_state:
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))
            c.execute("INSERT OR REPLACE INTO visitors (visitor_id, first_visit_date, last_visit_date) VALUES (?, ?, ?)",
                      (st.session_state["visitor_id"], today_str, today_str))
            conn.commit()
            st.session_state["has_counted"] = True

        c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
        pv = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM visitors")
        uv = c.fetchone()[0]
        conn.close()
        return uv, pv
    except:
        return 0, 0

uv, pv = track_and_get_stats()
st.markdown(f"<div style='text-align:center;color:#ccc;font-size:12px;margin-top:20px;'>👀 PV: {pv} | 👥 UV: {uv}</div>", unsafe_allow_html=True)
