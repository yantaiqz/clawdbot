import streamlit as st
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
    page_title="跨境合规圆桌会 | Agent Sim", 
    page_icon="🌍", 
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
        "style": "color: #333; background: #e3f2fd;", # 蓝色系
        "desc": "关注利润、发货速度，对合规成本敏感，经常抱怨由于合规导致的账号冻结。"
    },
    "legal_inhouse": {
        "name": "公司法务-Lisa",
        "role": "企业内部合规",
        "icon": "👩‍💻",
        "style": "color: #333; background: #fff3e0;", # 橙色系
        "desc": "谨慎、焦虑，需要在业务增长和合规风险之间找平衡，经常提醒老王注意风险。"
    },
    "lawyer_de": {
        "name": "Dr. Weber",
        "role": "德国执业律师",
        "icon": "⚖️",
        "style": "color: #333; background: #f3e5f5;", # 紫色系
        "desc": "严谨、专业，引用德国法条（如UStG, ProdSG），说话滴水不漏，费用昂贵。"
    },
    "regulator": {
        "name": "欧盟合规监管局",
        "role": "监管机构",
        "icon": "🏛️",
        "style": "color: #fff; background: #2c3e50;", # 深色严肃系
        "desc": "代表官方立场，强调消费者保护、税务合规、数据安全，态度强硬。"
    },
    "platform": {
        "name": "平台合规经理",
        "role": "电商平台方",
        "icon": "📦",
        "style": "color: #333; background: #e8f5e9;", # 绿色系
        "desc": "代表Amazon/Temu/TikTok，强调平台规则，如果不合规就封号或下架产品。"
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
    .main .block-container { padding-top: 0 !important; max-width: 900px !important; margin: 0 auto; }

    /* 顶部导航 */
    .nav-bar {
        background: white; border-bottom: 1px solid #ddd; padding: 15px 20px;
        position: sticky; top: 0; z-index: 999; display: flex; align-items: center; justify-content: space-between;
    }
    .logo-text { font-size: 1.1rem; font-weight: 700; color: #003567; }
    
    /* 聊天气泡布局 */
    .chat-row { display: flex; margin-bottom: 15px; width: 100%; align-items: flex-start; }
    .chat-avatar { 
        width: 40px; height: 40px; border-radius: 50%; 
        display: flex; align-items: center; justify-content: center; 
        font-size: 22px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        background: white; border: 1px solid #eee;
    }
    
    .chat-bubble-container { max-width: 80%; margin-left: 12px; }
    
    .chat-info { font-size: 0.75rem; color: #666; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;}
    .chat-role-tag { background: #eee; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
    
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
    你是一个跨境电商合规社区的模拟器。你需要扮演以下几个角色进行群聊讨论：
    {agents_desc}

    **任务规则：**
    1. 根据上下文历史，决定**下一个最应该发言的角色**是谁。
    2. 生成该角色的发言内容。内容必须简短有力（50-100字），符合其人设和利益立场。
    3. 话题必须围绕：德国/欧盟税务稽查、产品合规、环保法、账户冻结、数据安全等话题。
    4. 偶尔可以发生争论（例如卖家抱怨成本，监管机构强调法规）。
    5. **严格仅输出 JSON 格式**，格式如下：
       {{"agent_id": "agent的ID", "content": "发言内容"}}
    """

def generate_next_turn(history):
    """调用 Gemini 生成下一句话"""
    if not gemini_api_key:
        return None
    
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=get_system_prompt(),
        generation_config={"response_mime_type": "application/json"}
    )
    
    # 构建上下文 Prompt
    history_text = "\n".join([f"[{msg['role_name']}]: {msg['content']}" for msg in history[-10:]]) # 仅保留最近10条上下文
    prompt = f"当前对话历史：\n{history_text}\n\n请生成下一条发言："
    
    try:
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        return result
    except Exception as e:
        st.error(f"Gemini 生成错误: {e}")
        return None

# -------------------------------------------------------------
# --- 4. 状态管理 ---
# -------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

# 初始化开场白（如果为空）
if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "兄弟们，最近德国那边的税务稽查是不是又严了？我听说好几个同行的号被冻结了，这这这怎么搞啊？"
    })

# -------------------------------------------------------------
# --- 5. 页面渲染 ---
# -------------------------------------------------------------

# 导航栏
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌍 Global Compliance | Agent Community</div>
    <div style="font-size:0.8rem; color:green;">● 在线模拟中</div>
</div>
""", unsafe_allow_html=True)

# 渲染对话历史
st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

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

st.markdown('</div>', unsafe_allow_html=True) # End wrapper

# -------------------------------------------------------------
# --- 6. 模拟控制循环 (核心修改) ---
# -------------------------------------------------------------

# 底部控制面板占位
control_container = st.container()

with control_container:
    # 使用 st.columns 来居中按钮，或者自定义 CSS
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.simulation_active:
            if st.button("⏹ 停止模拟", use_container_width=True, type="secondary"):
                st.session_state.simulation_active = False
                st.rerun()
        else:
            if st.button("▶️ 开始社区对话模拟", use_container_width=True, type="primary"):
                st.session_state.simulation_active = True
                st.rerun()

# 自动运行逻辑
if st.session_state.simulation_active:
    
    # 1. 倒计时 (模拟 30-60秒间隔)
    # 为了演示效果，这里设置为 5-10秒。如果要严格30-60秒，请修改 range(5) 为 range(30)
    wait_seconds = random.randint(5, 10) # <--- 修改这里调整时间间隔
    
    prog_bar = status_placeholder.progress(0, text="Agents 正在思考中...")
    
    for i in range(wait_seconds):
        time.sleep(1)
        prog_bar.progress((i + 1) / wait_seconds, text=f"社区活跃中... 下一位发言者正在输入 ({wait_seconds - i}s)")
    
    status_placeholder.empty()

    # 2. 生成新对话
    with st.spinner("✍️ 正在生成回复..."):
        new_turn = generate_next_turn(st.session_state.messages)
        
        if new_turn:
            agent_id = new_turn.get("agent_id")
            # 容错处理：如果Gemini返回的ID不在列表里，随机分配一个
            if agent_id not in AGENTS:
                agent_id = random.choice(list(AGENTS.keys()))
            
            st.session_state.messages.append({
                "agent_id": agent_id,
                "role_name": AGENTS[agent_id]["name"],
                "content": new_turn.get("content")
            })
            
            # 3. 刷新页面以显示新消息
            st.rerun()

# -------------------------------------------------------------
# --- 7. 访客统计 (保留并简化) ---
# -------------------------------------------------------------

DB_FILE = "visit_stats.db"

def track_and_get_stats():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS visitors (visitor_id TEXT PRIMARY KEY, first_visit_date TEXT, last_visit_date TEXT)''')
        
        # Schema Migration Check (简化版)
        try:
            c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
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

st.markdown(f"""
<div class="metric-container">
    <span>👀 今日 PV: {pv}</span> | <span>👥 总访客 UV: {uv}</span>
</div>
""", unsafe_allow_html=True)
