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
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
else:
    gemini_model = None
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
        "desc": "代表平台方，强调平台规则，语气官方且强硬，动不动就警告下架。"
    },
    "lawyer_us": {
        "name": "Mike Ross",
        "role": "美国IP律师",
        "icon": "⚖️",
        "style": "color: #fff; background: #3949ab;",
        "desc": "美国执业律师，专门处理TRO、专利流氓诉讼。说话直击要害，强调诉讼风险。"
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
        "desc": "深耕东南亚，熟悉灰关、红灯期、COD货到付款的坑。说话接地气，知道很多潜规则。"
    },
    "cpa_hk": {
        "name": "Jason Lam",
        "role": "香港CPA/财税",
        "icon": "🏙️",
        "style": "color: #333; background: #e0f7fa;",
        "desc": "香港注册会计师，精通离岸账户、资金跨境回流、架构搭建。关注CRS信息交换。"
    },
    "partner_me": {
        "name": "Amir",
        "role": "中东本地保人",
        "icon": "🕌",
        "style": "color: #fff; background: #004d40;",
        "desc": "中东本地合作伙伴。强调本地化（保人制度）、伊斯兰合规（Halal认证）和斋月习俗。"
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
# --- 4. 核心逻辑 (最终修复版) ---
# -------------------------------------------------------------
def get_system_prompt():
    """
    ★ 最终修复：提示词明确要求使用英文ID (seller/legal_inhouse)
    不再暴露中文名称给AI，避免它混淆ID和Name
    """
    agents_desc = "\n".join([
        f"- `{k}`: {v['role']} ({v['desc'][:40]}...)" 
        for k, v in AGENTS.items()
    ])
    
    return f"""
    你是一个跨境电商合规专家群聊模拟器。请根据以下设定，生成下一位发言人的对话。

    【角色清单】（只能使用这里的 ID）：
    {agents_desc}

    【输出要求】
    1. 严格按照格式输出 JSON，**不要输出任何其他内容**，不要输出代码块。
    2. agent_id 必须是上述清单中的英文单词。
    3. content 必须是中文，40-60字，符合该角色的口吻，并且紧密承接上文对话。
    
    【输出格式】
    {{"agent_id": "角色ID", "content": "发言内容"}}
    """

def generate_next_turn(history):
    if not gemini_model:
        return None

    # 构建历史
    history_lines = []
    for msg in history[-8:]: # 缩短历史，减少幻觉
        history_lines.append(f"[{msg['role_name']}]: {msg['content']}")
    history_text = "\n".join(history_lines)
    
    # 拼接 Prompt (Gemini 只接受纯文本)
    full_prompt = f"{get_system_prompt()}\n\n【当前对话】:\n{history_text}\n\n【请生成下一条JSON】:"

    try:
        response = gemini_model.generate_content(
            full_prompt,
            temperature=0.9,
            top_p=0.95
        )
        response.resolve()
        raw_text = response.text.strip()
        
        # 调试：查看AI返回的原始内容
        # st.toast(f"原始: {raw_text[:60]}", icon="ℹ️")

        # 清洗
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        start = clean_text.find("{")
        end = clean_text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("未找到JSON")
        json_str = clean_text[start:end]
        
        # 替换中文符号
        json_str = json_str.replace("：", ":").replace("，", ",").replace("“", "\"").replace("”", "\"")
        
        result = json.loads(json_str)

        # ★ 关键修复：不再因为ID错误而触发降级，而是自动修正
        if not result.get("agent_id") or not result.get("content"):
            raise ValueError("字段缺失")
        
        # 自动修正未知ID
        original_id = result["agent_id"]
        if original_id not in AGENTS:
            result["agent_id"] = random.choice(list(AGENTS.keys()))
            st.toast(f"AI返回未知角色 `{original_id}`，已自动修正为 `{result['agent_id']}`", icon="🔄")

        st.toast(f"✅ 成功生成: {AGENTS[result['agent_id']]['name']}", icon="✅")
        return result

    except Exception as e:
        # 只有在解析完全失败时，才触发降级
        st.toast(f"解析失败，启用兜底: {str(e)[:20]}", icon="⚠️")
        fallback_id = random.choice(list(AGENTS.keys()))
        return {
            "agent_id": fallback_id,
            "content": f"各位，关于这个问题，我有几点看法。{AGENTS[fallback_id]['role']}的角度来看，合规是长期发展的基石。"
        }

# -------------------------------------------------------------
# --- 5. 页面渲染与逻辑 ---
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "agent_id": "seller",
        "role_name": AGENTS["seller"]["name"],
        "content": "最近太难了！美国TRO封店，印尼海关红灯期，货全卡港口了。出海合规到底要怎么搞？"
    }]

if "simulation_active" not in st.session_state:
    st.session_state.simulation_active = False

# 顶部导航
st.markdown("""
<div class="nav-bar">
    <div class="logo-text">🌏 全球合规风云 | Gemini Agent Sim</div>
    <div style="font-size:0.8rem; color:#003567;">● Powered by Google Gemini</div>
</div>
""", unsafe_allow_html=True)

# 聊天区
st.markdown('<div id="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    cfg = AGENTS[msg["agent_id"]]
    st.markdown(f"""
    <div class="chat-row">
        <div class="chat-avatar">{cfg['icon']}</div>
        <div class="chat-bubble-container">
            <div class="chat-info">
                <span style="font-weight:bold;">{cfg['name']}</span>
                <span class="chat-role-tag">{cfg['role']}</span>
            </div>
            <div class="chat-bubble" style="{cfg['style']}">{msg['content']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 自动滚动
components.html("""
<script>
    const chatDiv = window.parent.document.getElementById('chat-container');
    if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
</script>
""", height=0)

# 控制按钮
status_ph = st.empty()
col1, col2, col3 = st.columns([1,2,1])
with col2:
    if st.session_state.simulation_active:
        if st.button("⏹ 停止模拟", use_container_width=True, type="secondary"):
            st.session_state.simulation_active = False
            st.rerun()
    else:
        if st.button("▶️ 开始 Gemini 驱动模拟", use_container_width=True, type="primary"):
            st.session_state.simulation_active = True
            st.rerun()

# 模拟循环
if st.session_state.simulation_active:
    import time
    wait = random.randint(3, 8)
    for i in range(wait):
        status_ph.progress((i+1)/wait, text=f"正在思考... {wait-i}s")
        time.sleep(1)
    status_ph.empty()

    new_msg = generate_next_turn(st.session_state.messages)
    if new_msg:
        st.session_state.messages.append({
            "agent_id": new_msg["agent_id"],
            "role_name": AGENTS[new_msg["agent_id"]]["name"],
            "content": new_msg["content"]
        })
    st.session_state.simulation_active = False # 运行一轮后暂停，防止刷屏
    st.rerun()

# 访客统计
DB_FILE = "visit_stats_gemini.db"
def track_stats():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS visitors (visitor_id TEXT, date TEXT)')
        today = datetime.date.today().isoformat()
        if "vid" not in st.session_state:
            st.session_state["vid"] = str(uuid.uuid4())
            c.execute("INSERT INTO visitors VALUES (?, ?)", (st.session_state["vid"], today))
            conn.commit()
        uv = c.execute("SELECT COUNT(DISTINCT visitor_id) FROM visitors WHERE date=?", (today,)).fetchone()[0]
        pv = c.execute("SELECT COUNT(*) FROM visitors WHERE date=?", (today,)).fetchone()[0]
        conn.close()
        return uv, pv
    except:
        return 0, 0

uv, pv = track_stats()
st.markdown(f"<div style='text-align:center;color:#888;font-size:12px;margin-top:10px;'>👥 UV: {uv} | 👀 PV: {pv}</div>", unsafe_allow_html=True)
