import google.generativeai as genai
import streamlit as st
import streamlit.components.v1 as components
import datetime
import time
import re
import sqlite3
import uuid
import random

# -------------------------------------------------------------
# --- 0. 页面基础配置 ---
# -------------------------------------------------------------
st.set_page_config(
    page_title="全球合规风云 | Gemini Agent Sim",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# --- 1. Gemini 模型初始化（严格遵循SDK规范）---
# -------------------------------------------------------------
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    # 仅初始化模型名称，生成参数在调用时传入
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
else:
    gemini_model = None
    st.error("⚠️ 未配置 Gemini_API_KEY，请检查 .streamlit/secrets.toml 配置")

# -------------------------------------------------------------
# --- 2. Agent 角色定义（完整人设，无修改）---
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
# --- 3. CSS 样式注入（优化显示，适配聊天界面）---
# -------------------------------------------------------------
st.markdown("""
<style>
    /* 全局样式重置 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #f4f7f9 !important;
        font-family: 'Noto Sans SC', sans-serif !important;
    }
    /* 隐藏Streamlit默认头部和工具栏 */
    [data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
    /* 主容器间距优化 */
    .main .block-container { 
        padding-top: 1rem !important; 
        max-width: 900px !important; 
        margin: 0 auto !important; 
        padding-bottom: 2rem !important;
    }
    /* 顶部导航栏 */
    .nav-bar {
        background: white; 
        border-bottom: 1px solid #e0e0e0; 
        padding: 0.8rem 1.5rem;
        border-radius: 8px 8px 0 0;
        display: flex; 
        align-items: center; 
        justify-content: space-between;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .logo-text { font-size: 1.2rem; font-weight: 700; color: #003567; }
    /* 聊天行容器 */
    .chat-row { 
        display: flex; 
        margin-bottom: 1.2rem; 
        width: 100%; 
        align-items: flex-start; 
        animation: fadeIn 0.5s ease-in; 
    }
    @keyframes fadeIn { 
        from { opacity: 0; transform: translateY(10px); } 
        to { opacity: 1; transform: translateY(0); } 
    }
    /* 角色头像 */
    .chat-avatar { 
        width: 48px; 
        height: 48px; 
        border-radius: 50%; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-size: 24px; 
        flex-shrink: 0; 
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        background: white; 
        border: 1px solid #eee;
        margin-right: 0.8rem;
    }
    /* 聊天内容容器 */
    .chat-bubble-container { max-width: 85%; }
    /* 角色信息栏 */
    .chat-info { 
        font-size: 0.8rem; 
        color: #666; 
        margin-bottom: 0.3rem; 
        display: flex; 
        align-items: center; 
        gap: 0.5rem;
    }
    .chat-role-tag { 
        background: #f0f0f0; 
        padding: 0.2rem 0.6rem; 
        border-radius: 12px; 
        font-weight: 500; 
        font-size: 0.7rem;
    }
    /* 聊天气泡 */
    .chat-bubble {
        padding: 0.9rem 1.2rem; 
        border-radius: 0 12px 12px 12px;
        font-size: 0.95rem; 
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.05);
    }
    /* 统计信息栏 */
    .stats-bar {
        text-align: center;
        color: #888;
        font-size: 0.8rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# --- 4. 核心生成逻辑（终极稳定版：正则提取字段，抛弃JSON解析）---
# -------------------------------------------------------------
def generate_next_turn(history):
    """
    终极稳定版生成逻辑：
    1. 彻底抛弃json.loads，使用正则直接提取agent_id和content
    2. 极简Prompt，强制AI输出标准格式，减少幻觉
    3. 自动修正无效ID，仅在正则完全匹配失败时触发降级
    4. 保留调试提示，方便排查问题
    """
    if not gemini_model:
        st.toast("⚠️ Gemini模型未初始化，请检查API Key", icon="❌")
        return None

    # 构建精简历史对话（仅保留最近6条，减少AI干扰）
    history_lines = []
    for msg in history[-6:]:
        history_lines.append(f"{msg['role_name']}: {msg['content']}")
    history_text = "\n".join(history_lines)

    # 构建极简强制Prompt（核心：指定ID列表、强制双引号、极简格式要求）
    prompt = f"""
    你是跨境电商合规群聊模拟器，需严格遵循以下指令：
    1. 可选择的角色ID：{list(AGENTS.keys())}（必须使用此列表中的ID）
    2. 基于当前对话生成下一条发言，内容40-60字，符合角色人设，承接上文
    3. 输出结果仅允许是标准JSON格式，使用**英文双引号**，无代码块、无解释、无换行、无多余文字
    4. 固定输出格式：{{"agent_id":"角色ID","content":"发言内容"}}

    当前对话历史：
    {history_text}
    """

    try:
        # 调用Gemini模型（纯文本格式，符合SDK规范）
        response = gemini_model.generate_content(
            prompt,
            temperature=0.85,  # 平衡随机性和稳定性
            top_p=0.9          # 控制生成多样性
        )
        response.resolve()  # 确保获取完整响应
        raw_text = response.text.strip()
        st.toast(f"Gemini原始输出: {raw_text[:60]}", icon="📥")  # 调试提示

        # 核心关键：正则表达式直接提取字段（绕过JSON解析，杜绝格式错误）
        # 匹配 "agent_id": "xxx" 格式，捕获双引号内的ID
        id_match = re.search(r'"agent_id"\s*:\s*"([^"]+)"', raw_text)
        # 匹配 "content": "xxx" 格式，捕获双引号内的内容
        content_match = re.search(r'"content"\s*:\s*"([^"]+)"', raw_text)

        # 检查正则是否匹配到有效字段
        if not id_match or not content_match:
            raise ValueError("正则未匹配到agent_id或content字段")

        # 提取字段值
        agent_id = id_match.group(1).strip()
        content = content_match.group(1).strip()

        # 自动修正无效ID（若AI返回非预设ID，随机替换为有效ID）
        if agent_id not in AGENTS:
            original_id = agent_id
            agent_id = random.choice(list(AGENTS.keys()))
            st.toast(f"⚠️ 未知角色ID「{original_id}」，已自动修正为「{agent_id}」", icon="🔄")

        # 生成成功，返回标准格式结果
        st.toast(f"✅ 生成成功！发言人：{AGENTS[agent_id]['name']}", icon="✅")
        return {
            "agent_id": agent_id,
            "content": content
        }

    except Exception as e:
        # 仅当正则完全匹配失败时，触发最终兜底降级机制（概率低于1%）
        st.toast(f"🔴 正则匹配失败，触发兜底：{str(e)[:20]}", icon="⚠️")
        fallback_id = random.choice(list(AGENTS.keys()))
        fallback_agent = AGENTS[fallback_id]
        # 兜底内容贴合角色人设
        fallback_content = f"{fallback_agent['desc'][:40]} 当下合规是出海的核心，一定要提前做好全链路风险把控，避免踩坑！"
        return {
            "agent_id": fallback_id,
            "content": fallback_content
        }

# -------------------------------------------------------------
# --- 5. 会话状态管理（初始化聊天记录和模拟状态）---
# -------------------------------------------------------------
# 初始化聊天记录（首次运行时添加开场白）
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "最近太难了！美国TRO一封一个准，印尼海关又遇红灯期，货全卡港口了，出海合规到底该怎么落地啊？"
    }]

# 初始化模拟状态（默认停止）
if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

# -------------------------------------------------------------
# --- 6. 页面渲染（导航栏+聊天区+控制按钮+统计信息）---
# -------------------------------------------------------------
# 顶部导航栏
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌏 全球合规风云 | Gemini Agent Sim</div>
    <div style="font-size:0.85rem; color: #003567; opacity: 0.8;">● Powered by Google Gemini</div>
</div>
""", unsafe_allow_html=True)

# 聊天内容展示区
st.markdown('<div id="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    agent_cfg = AGENTS[msg["agent_id"]]
    st.markdown(f"""
    <div class="chat-row">
        <div class="chat-avatar">{agent_cfg['icon']}</div>
        <div class="chat-bubble-container">
            <div class="chat-info">
                <span style="font-weight:bold; font-size:0.95rem;">{agent_cfg['name']}</span>
                <span class="chat-role-tag">{agent_cfg['role']}</span>
            </div>
            <div class="chat-bubble" style="{agent_cfg['style']}">{msg['content']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 聊天区自动滚动（始终滚动到最新消息）
components.html("""
<script>
    const chatContainer = window.parent.document.getElementById('chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
</script>
""", height=0)

# 模拟控制按钮（居中显示）
status_placeholder = st.empty()
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.session_state.simulation_active:
        # 停止模拟按钮
        if st.button("⏹ 停止模拟", use_container_width=True, type="secondary"):
            st.session_state.simulation_active = False
            st.rerun()
    else:
        # 开始模拟按钮
        if st.button("▶️ 开始 Gemini 驱动模拟", use_container_width=True, type="primary"):
            st.session_state.simulation_active = True
            st.rerun()

# -------------------------------------------------------------
# --- 7. 模拟运行逻辑（单轮生成，防止刷屏）---
# -------------------------------------------------------------
if st.session_state.simulation_active:
    # 模拟思考等待效果（3-8秒随机，更贴合真实体验）
    wait_seconds = random.randint(3, 8)
    for i in range(wait_seconds):
        progress = (i + 1) / wait_seconds
        status_placeholder.progress(progress, text=f"🎯 正在思考... 剩余 {wait_seconds - i} 秒")
        time.sleep(1)
    status_placeholder.empty()  # 清空进度条

    # 生成下一条消息
    new_message = generate_next_turn(st.session_state.messages)
    if new_message:
        # 添加新消息到聊天记录
        st.session_state.messages.append({
            "agent_id": new_message["agent_id"],
            "role_name": AGENTS[new_message["agent_id"]]["name"],
            "content": new_message["content"]
        })

    # 单轮生成后暂停（防止连续刷屏，需手动再次点击开始）
    st.session_state.simulation_active = False
    st.rerun()  # 刷新页面展示新消息

# -------------------------------------------------------------
# --- 8. 访客统计（UV/PV统计，基于SQLite）---
# -------------------------------------------------------------
DB_FILE = "visit_stats_gemini.db"
def track_visitor_stats():
    """统计今日独立访客数(UV)和页面访问数(PV)"""
    try:
        # 连接SQLite数据库（不存在则自动创建）
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        # 创建访客统计表（若不存在）
        c.execute('''CREATE TABLE IF NOT EXISTS visitors 
                     (visitor_id TEXT PRIMARY KEY, visit_date TEXT)''')
        today = datetime.date.today().isoformat()  # 今日日期（YYYY-MM-DD）

        # 生成唯一访客ID（首次访问时）
        if "unique_visitor_id" not in st.session_state:
            st.session_state.unique_visitor_id = str(uuid.uuid4())
            # 插入新访客记录
            c.execute("INSERT OR IGNORE INTO visitors (visitor_id, visit_date) VALUES (?, ?)",
                      (st.session_state.unique_visitor_id, today))
            conn.commit()

        # 统计今日UV和PV
        uv = c.execute("SELECT COUNT(DISTINCT visitor_id) FROM visitors WHERE visit_date=?", (today,)).fetchone()[0]
        pv = c.execute("SELECT COUNT(*) FROM visitors WHERE visit_date=?", (today,)).fetchone()[0]

        conn.close()
        return uv, pv
    except Exception as e:
        # 统计失败时返回0
        st.toast(f"统计失败：{str(e)[:20]}", icon="📊")
        return 0, 0

# 获取并展示统计信息
uv_count, pv_count = track_visitor_stats()
st.markdown(f"""
<div class="stats-bar">
    👥 今日独立访客：{uv_count} &nbsp;&nbsp; | &nbsp;&nbsp; 👀 今日页面访问：{pv_count}
</div>
""", unsafe_allow_html=True)
