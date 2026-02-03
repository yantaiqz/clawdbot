import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
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
    page_title="全球合规风云 | Agent Sim", 
    page_icon="🌏", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# --- 1. Agent 角色定义 (扩充版) ---
# -------------------------------------------------------------

AGENTS = {
    # --- 原有角色 ---
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
    
    # --- 新增：北美区域 ---
    "lawyer_us": {
        "name": "Mike Ross",
        "role": "美国IP律师",
        "icon": "⚖️",
        "style": "color: #fff; background: #3949ab;", # 深蓝
        "desc": "美国执业律师，专门处理TRO（临时限制令）、专利流氓诉讼和337调查。说话直击要害，强调诉讼风险。"
    },
    
    # --- 新增：欧洲区域 ---
    "regulator_eu": {
        "name": "欧盟监管局",
        "role": "欧盟官员",
        "icon": "🇪🇺",
        "style": "color: #fff; background: #003399;", # 欧盟蓝
        "desc": "关注GDPR数据安全、VAT税务、以及ESG环保法规（如德国包装法）。"
    },

    # --- 新增：东南亚区域 ---
    "logistics_sea": {
        "name": "印尼通-阿强",
        "role": "东南亚物流商",
        "icon": "🛵",
        "style": "color: #333; background: #fff9c4;", # 浅黄
        "desc": "深耕东南亚（印尼/越南/泰国），熟悉灰关、红灯期、COD货到付款的坑。说话接地气，知道很多潜规则。"
    },

    # --- 新增：香港/金融 ---
    "cpa_hk": {
        "name": "Jason Lam",
        "role": "香港CPA/财税",
        "icon": "🏙️",
        "style": "color: #333; background: #e0f7fa;", # 青色
        "desc": "香港注册会计师，精通离岸账户、资金跨境回流、架构搭建。关注审计和CRS信息交换。"
    },

    # --- 新增：中东区域 ---
    "partner_me": {
        "name": "Amir",
        "role": "中东本地保人",
        "icon": "🕌",
        "style": "color: #fff; background: #004d40;", # 深绿
        "desc": "中东（沙特/阿联酋）本地合作伙伴。强调本地化（保人制度）、伊斯兰合规（Halal认证）和斋月习俗。"
    }
}

# -------------------------------------------------------------
# --- 2. CSS 注入 (适配多角色风格) ---
# -------------------------------------------------------------

st.markdown("""
<style>
    /* === 全局基础 === */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
    * { box-sizing: border-box; }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #f4f7f9 !important;
        font-family: 'Noto Sans SC', sans-serif !important;
    }
    
    /* 去除留白 */
    [data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
    .main .block-container { padding-top: 0 !important; max-width: 900px !important; margin: 0 auto; padding-bottom: 100px !important;}

    /* 顶部导航 */
    .nav-bar {
        background: white; border-bottom: 1px solid #ddd; padding: 15px 20px;
        position: sticky; top: 0; z-index: 999; display: flex; align-items: center; justify-content: space-between;
    }
    .logo-text { font-size: 1.1rem; font-weight: 700; color: #003567; }
    
    /* 聊天气泡布局 */
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

    /* 底部控制栏 */
    .control-panel {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background: white; padding: 15px; border-top: 1px solid #ddd;
        display: flex; justify-content: center; gap: 15px; z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    
    /* 统计面板 */
    .metric-container { display: flex; gap: 15px; justify-content: center; margin: 20px 0; font-size: 0.8rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# --- 3. 核心逻辑 ---
# -------------------------------------------------------------

gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

def get_system_prompt():
    agents_desc = "\n".join([f"- ID: {k}, 名称: {v['name']}, 角色: {v['role']}, 人设: {v['desc']}" for k, v in AGENTS.items()])
    return f"""
    你是一个全球跨境电商合规社区的模拟器。你需要扮演以下角色进行群聊讨论：
    {agents_desc}

    **任务规则：**
    1. 根据上下文历史，决定**下一个最应该发言的角色**是谁。
       - 例如：提到TRO/专利，美国律师必须发言。
       - 提到清关/COD/印尼，东南亚物流商发言。
       - 提到资金回流/架构，香港CPA发言。
       - 提到中东/沙特，中东保人发言。
    2. 生成该角色的发言内容。内容必须简短有力（50-100字），符合其人设和利益立场。
    3. 话题必须围绕跨境出海的痛点：资金合规、税务稽查、知识产权、物流灰关、本地化壁垒等。
    4. 偶尔可以发生争论（例如卖家抱怨成本，监管机构强调法规）。
    5. **严格仅输出 JSON 格式**，格式如下：
       {{"agent_id": "agent的ID", "content": "发言内容"}}
    """

def generate_next_turn(history):
    """调用 Gemini 生成下一句话"""
    if not gemini_api_key: return None
    
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=get_system_prompt(),
        generation_config={"response_mime_type": "application/json"}
    )
    
    # 构建上下文 (保留最近12条以保持连贯性)
    history_text = "\n".join([f"[{msg['role_name']}]: {msg['content']}" for msg in history[-12:]]) 
    prompt = f"当前对话历史：\n{history_text}\n\n请生成下一条发言（请优先选择之前发言较少或与当前话题最相关的角色）："
    
    try:
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        return None

# -------------------------------------------------------------
# --- 4. 状态管理 ---
# -------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

# 初始化开场白（随机选择一个痛点开场）
if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "最近太难了！美国那边TRO搞得人心惶惶，印尼那边听说海关又红灯了，货都卡在港口。兄弟们，咱们这出海怎么全是坑啊？"
    })

# -------------------------------------------------------------
# --- 5. 页面渲染 & 自动滚动 JS ---
# -------------------------------------------------------------

# 导航栏
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌏 Global Compliance | Agent Community</div>
    <div style="font-size:0.8rem; color:green;">● AI Simulating</div>
</div>
""", unsafe_allow_html=True)

# 渲染对话历史
st.markdown('<div class="main-content-wrapper" id="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    agent_id = msg.get("agent_id", "seller")
    if agent_id not in AGENTS: agent_id = "seller" # Fallback
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

# 占位符：用于显示正在输入的动画 或 倒计时
status_placeholder = st.empty()

st.markdown('</div>', unsafe_allow_html=True) 

# === 核心修改：自动滚动 JS ===
# 只要页面刷新（rerun），就会执行这段 JS，将页面滚动到底部
scroll_js = """
<script>
    function scrollToBottom() {
        var mainContainer = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
        if (mainContainer) {
            mainContainer.scrollTop = mainContainer.scrollHeight;
        }
    }
    // 延迟一点执行，确保DOM渲染完毕
    setTimeout(scrollToBottom, 300);
</script>
"""
components.html(scroll_js, height=0, width=0)


# -------------------------------------------------------------
# --- 6. 模拟控制循环 ---
# -------------------------------------------------------------

# 底部控制面板
control_container = st.container()

with control_container:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.simulation_active:
            if st.button("⏹ 停止模拟 (Pause)", use_container_width=True, type="secondary"):
                st.session_state.simulation_active = False
                st.rerun()
        else:
            if st.button("▶️ 开始全球合规模拟 (Auto-Run)", use_container_width=True, type="primary"):
                st.session_state.simulation_active = True
                st.rerun()

# 自动运行逻辑
if st.session_state.simulation_active:
    
    # 1. 倒计时
    # 注意：为了演示不让你等太久，这里设置为 5-15秒随机。
    # 实际要求30-60秒，你可以将 (5, 15) 改为 (30, 60)
    wait_seconds = random.randint(5, 15) 
    
    prog_bar = status_placeholder.progress(0, text="Agents 正在思考中...")
    
    for i in range(wait_seconds):
        time.sleep(1)
        prog_bar.progress((i + 1) / wait_seconds, text=f"下一位专家正在输入... ({wait_seconds - i}s)")
    
    status_placeholder.empty()

    # 2. 生成新对话
    new_turn = generate_next_turn(st.session_state.messages)
    
    if new_turn:
        agent_id = new_turn.get("agent_id")
        # 容错：如果ID不存在，随机分配一个
        if agent_id not in AGENTS:
            agent_id = random.choice(list(AGENTS.keys()))
        
        st.session_state.messages.append({
            "agent_id": agent_id,
            "role_name": AGENTS[agent_id]["name"],
            "content": new_turn.get("content")
        })
        
        # 3. 刷新页面 -> 触发JS滚动 -> 显示新消息
        st.rerun()

# -------------------------------------------------------------
# --- 7. 访客统计 ---
# -------------------------------------------------------------

DB_FILE = "visit_stats_sim.db"

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
