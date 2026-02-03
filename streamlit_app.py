import streamlit as st
import google.generativeai as genai
import requests
import json
import datetime
import os
import time
import re
import random
import sqlite3
import uuid
from threading import Timer

# -------------------------------------------------------------
# --- 0. 页面配置 ---
# -------------------------------------------------------------
st.set_page_config(
    page_title="跨境企业Agent社区", 
    page_icon="🌐", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# --- 1. CSS 注入 (保留原有风格 + 新增Agent角色样式) ---
# -------------------------------------------------------------
st.markdown("""
<style>
    /* === 1. 全局重置与字体 === */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');

    * {
        box-sizing: border-box;
    }
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #f4f7f9 !important;
        font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        color: #333333 !important;
    }

    /* === 2. 彻底去除顶部留白 === */
    [data-testid="stHeader"], [data-testid="stToolbar"] {
        display: none !important;
    }
    .main .block-container {
        padding-top: 0 !important;
        padding-bottom: 6rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    
    /* === 3. 顶部导航栏模拟 === */
    .nav-bar {
        background-color: #ffffff;
        border-bottom: 1px solid #e0e0e0;
        padding: 15px 40px;
        position: sticky;
        top: 0;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }
    .logo-text {
        font-size: 1.2rem;
        font-weight: 700;
        color: #003567;
        letter-spacing: 0.5px;
    }
    .nav-tag {
        background-color: #eef4fc;
        color: #0056b3;
        font-size: 0.75rem;
        padding: 4px 8px;
        border-radius: 4px;
        margin-left: 12px;
        font-weight: 500;
    }
    .status-tag {
        background-color: #d4edda;
        color: #155724;
        font-size: 0.75rem;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 500;
    }

    /* === 4. 主容器限制 === */
    .main-content-wrapper {
        max-width: 1000px;
        margin: 0 auto;
        padding: 20px 20px;
    }

    /* === 5. 标题区域 === */
    .hero-section {
        margin-bottom: 20px;
        text-align: left;
    }
    .page-title {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1a1a1a !important;
        margin-bottom: 8px !important;
    }
    .subtitle {
        font-size: 1rem !important;
        color: #666666 !important;
        font-weight: 400 !important;
    }

    /* === 6. Agent聊天气泡 (核心修改：多角色样式) === */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 8px 0 !important;
    }
    [data-testid="stChatMessage"] > div:first-child {
        display: none !important;
    }
    
    .chat-row {
        display: flex;
        margin-bottom: 16px;
        width: 100%;
        align-items: flex-start;
    }
    .chat-avatar {
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
        margin-right: 12px;
        border: 1px solid #e0e0e0;
    }
    .chat-role {
        font-size: 0.7rem;
        color: #888;
        margin-top: 2px;
        text-align: center;
    }
    .chat-bubble {
        padding: 14px 18px;
        border-radius: 10px;
        font-size: 0.95rem;
        line-height: 1.6;
        max-width: 85%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        position: relative;
    }
    .chat-nickname {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 4px;
        color: #222;
    }

    /* === 7. 不同角色专属样式 (核心) === */
    /* 跨境电商企业主 */
    .role-seller .chat-avatar { background-color: #ffecd8; color: #e67e22; }
    .role-seller .chat-bubble { background-color: #fff8f0; border: 1px solid #ffe0b2; }
    /* 制造业企业主 */
    .role-manufacturer .chat-avatar { background-color: #e8f5e9; color: #2ecc71; }
    .role-manufacturer .chat-bubble { background-color: #f1f8e9; border: 1px solid #c8e6c9; }
    /* 公司法务 */
    .role-company-legal .chat-avatar { background-color: #e3f2fd; color: #3498db; }
    .role-company-legal .chat-bubble { background-color: #f0f8ff; border: 1px solid #b3e5fc; }
    /* 各国律师 */
    .role-lawyer .chat-avatar { background-color: #f3e5f5; color: #9b59b6; }
    .role-lawyer .chat-bubble { background-color: #faf2f8; border: 1px solid #e1bee7; }
    /* 税务/合规机构 */
    .role-regulator .chat-avatar { background-color: #ffebee; color: #e74c3c; }
    .role-regulator .chat-bubble { background-color: #fff5f5; border: 1px solid #ffcdd2; }
    /* 电商平台 */
    .role-platform .chat-avatar { background-color: #f5f5f5; color: #7f8c8d; }
    .role-platform .chat-bubble { background-color: #ffffff; border: 1px solid #e0e0e0; }

    /* === 8. 模型分析卡片 === */
    .model-section-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #555;
        margin: 30px 0 15px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-left: 4px solid #003567;
        padding-left: 10px;
    }
    .model-card {
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .model-card-header {
        padding: 12px 20px;
        font-size: 0.9rem;
        font-weight: 600;
        background-color: #f8f9fa;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        align-items: center;
    }
    .gemini-header, .glm-header { color: #0056b3; }

    /* === 9. 输入框与按钮 === */
    [data-testid="stChatInput"] {
        background-color: white !important;
        padding: 15px 0 !important;
        border-top: 1px solid #e0e0e0 !important;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.03) !important;
        z-index: 1000;
    }
    [data-testid="stChatInput"] > div {
        max-width: 1000px !important;
        margin: 0 auto !important;
    }
    div.stButton > button {
        border-radius: 6px !important;
        border: 1px solid #dcdfe6 !important;
        background-color: white !important;
        color: #333 !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    div.stButton > button:hover {
        border-color: #0056b3 !important;
        color: #0056b3 !important;
        background-color: #ecf5ff !important;
    }
    [data-testid="stButton"] button[kind="secondary"] {
        margin-top: 20px;
        width: 100%;
        border-style: dashed !important;
    }

    /* === 10. 统计模块与光标动画 === */
    .metric-container {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-top: 15px;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    .metric-box { text-align: center; }
    .metric-label { color: #6c757d; font-size: 0.85rem; margin-bottom: 2px; }
    .metric-value { color: #212529; font-size: 1.2rem; font-weight: bold; }
    .metric-sub { font-size: 0.7rem; color: #adb5bd; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
    .blinking-cursor { animation: blink 1s infinite; color: #0056b3; font-weight: bold; margin-left: 2px;}
    .agent-tips {
        font-size: 0.85rem;
        color: #666;
        text-align: center;
        margin: 10px 0;
        padding: 8px;
        background-color: #eef4fc;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# --- 2. 核心定义：Agent角色/系统指令/工具函数 ---
# -------------------------------------------------------------
# === 2.1 Agent角色配置（核心：6类角色，带专属标识/风格/话术方向）===
AGENT_ROLES = [
    {
        "role_type": "seller",
        "name": "亚马逊李总",
        "avatar": "🏪",
        "desc": "跨境电商企业主",
        "personality": "务实、关注成本与平台规则、提问直白、关注实际操作问题"
    },
    {
        "role_type": "manufacturer",
        "name": "机械制造王总",
        "avatar": "🏭",
        "desc": "制造业跨境企业主",
        "personality": "关注关税、物流、生产合规、对国际税务政策敏感"
    },
    {
        "role_type": "company-legal",
        "name": "张法务",
        "avatar": "⚖️",
        "desc": "企业资深法务",
        "personality": "严谨、专业、引用法规、关注合同风险和合规流程"
    },
    {
        "role_type": "lawyer",
        "name": "德国迈克律师",
        "avatar": "🇩🇪",
        "desc": "德国涉外律师",
        "personality": "精通当地法规、注重细节、解答精准、提供当地实操建议"
    },
    {
        "role_type": "regulator",
        "name": "欧盟合规专员",
        "avatar": "🇪🇺",
        "desc": "欧盟税务合规机构",
        "personality": "官方、严谨、强调法规要求、提醒合规风险、无主观建议"
    },
    {
        "role_type": "platform",
        "name": "Shopee平台小二",
        "avatar": "🛒",
        "desc": "东南亚电商平台",
        "personality": "亲和、熟悉平台规则、提供平台侧解决方案、提醒平台政策"
    }
]

# === 2.2 系统指令：控制Agent发言风格和上下文关联 ===
AGENT_SYSTEM_INSTRUCTION = """
你是跨境贸易领域的专业从业者，需严格按照指定角色的性格和身份发言：
1. 发言必须基于历史对话上下文，不能脱离当前讨论的话题，字数控制在50-150字
2. 贴合角色身份：企业主关注实际问题和成本，律师/法务关注法规和合规，机构关注监管要求，平台关注规则和操作
3. 语气符合角色性格：企业主直白务实，律师严谨专业，机构官方正式，平台亲和耐心
4. 可以提出问题、解答疑问、补充信息或提醒风险，禁止无关内容，禁止重复历史发言
5. 发言语言：根据对话整体语境，使用中文交流，专业术语准确
"""

# === 2.3 工具函数 ===
def clean_extra_newlines(text):
    """清理冗余换行/空格"""
    cleaned = re.sub(r'\n{3,}', '\n\n', text)
    cleaned = re.sub(r'　+', '', cleaned)
    return cleaned.strip('\n')

def markdown_to_html(text):
    """Markdown转HTML，适配聊天展示"""
    lines = [line.strip() for line in text.split("\n") if not line.startswith("###")]
    html_lines = []
    in_list = False
    for line in lines:
        if line.startswith("**") and line.endswith("**"):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<div style='color: #003567; font-weight: 700; margin: 8px 0;'>{line.strip('*')}</div>")
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list: html_lines.append("<ul style='margin: 0 0 12px 20px; padding: 0;'>"); in_list = True
            html_lines.append(f"<li style='margin-bottom: 4px;'>{line[2:].strip()}</li>")
        elif line:
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<p style='margin-bottom: 8px;'>{line}</p>")
    if in_list: html_lines.append("</ul>")
    return "\n".join(html_lines)

def get_chat_context():
    """提取历史对话上下文，用于Agent关联发言"""
    if len(st.session_state.messages) <= 1:
        return "跨境企业主、律师、合规机构和电商平台正在讨论跨境贸易的合规、税务、平台规则等问题，开始展开交流。"
    # 取最近10条对话作为上下文，避免过长
    recent_msgs = st.session_state.messages[-10:]
    context = ""
    for msg in recent_msgs:
        if msg["role"] == "agent":
            context += f"{msg['name']}({msg['desc']}): {msg['content']}\n"
        elif msg["role"] == "user":
            context += f"用户: {msg['content']}\n"
    return context.strip()

# -------------------------------------------------------------
# --- 3. AI模型调用函数（保留原有双模型，适配Agent发言）---
# -------------------------------------------------------------
USER_ICON = "👤"
GEMINI_ICON = "♊️"
GLM_ICON = "🧠"

# Gemini模型调用
def stream_gemini_response(prompt, model, max_retries=3):
    for attempt in range(max_retries):
        try:
            stream = model.generate_content(prompt, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    time.sleep(0.02)
            return
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    yield f"⚠️ 模型调用失败：配额不足，请稍后重试。"
                    break
            else:
                yield f"⚠️ 模型调用失败：{error_str[:50]}..."
                break

# GLM模型调用
def stream_glm_response(prompt, api_key, model_name="glm-4"):
    if not api_key:
        yield "⚠️ 未配置GLM API Key。"
        return
    try:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,  # 提高温度，让Agent发言更自然
            "stream": True
        }
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=30)
        for line in response.iter_lines():
            if line and line.startswith(b'data: '):
                line = line[6:].decode('utf-8')
                if line == '[DONE]': break
                try:
                    if content := json.loads(line)['choices'][0]['delta'].get('content'):
                        yield content
                except: continue
    except Exception as e:
        yield f"⚠️ GLM调用失败：{str(e)[:50]}..."

# 语义对比分析（保留原有功能）
def generate_semantic_compare(gemini_resp, glm_resp, user_question, gemini_api_key, max_retries=3):
    compare_prompt = f"""
    作为跨境贸易合规专家，请对比以下两个模型针对"{user_question}"的回答，严格按格式输出语义异同分析：
    [Gemini]: {gemini_resp[:1500]}
    [GLM]: {glm_resp[:1500]}
    输出格式：
    **核心共识**
    - [共识点1]
    - [共识点2]
    **观点差异**
    - Gemini侧重：[描述]
    - GLM侧重：[描述]
    **综合建议**
    [100字左右实操建议]
    """
    for attempt in range(max_retries):
        try:
            genai.configure(api_key=gemini_api_key)
            summary_model = genai.GenerativeModel('gemini-2.5-flash')
            stream = summary_model.generate_content(compare_prompt, stream=True)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    time.sleep(0.03)
            return
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    yield f"**警告：** 配额限制，等待 {2**attempt} 秒后重试..."
                    time.sleep(2**attempt)
                    continue
                else:
                    yield f"**核心共识**\n- 均强调跨境合规重要性\n\n**观点差异**\n- 分析服务暂时不可用\n\n**综合建议**\n多次调用失败，请检查API Key或稍后重试。"
                    return
            else:
                yield f"**核心共识**\n- 均强调跨境合规重要性\n\n**观点差异**\n- 分析服务暂时不可用\n\n**综合建议**\n模型调用错误：{type(e).__name__}。"
                return

# -------------------------------------------------------------
# --- 4. Agent自动发言核心逻辑 ---
# -------------------------------------------------------------
def generate_agent_message():
    """生成单个Agent的发言内容"""
    # 随机选择一个Agent角色
    agent = random.choice(AGENT_ROLES)
    # 构造Agent专属prompt
    context = get_chat_context()
    agent_prompt = f"""
    {AGENT_SYSTEM_INSTRUCTION}
    当前角色：{agent['name']}，身份：{agent['desc']}，性格：{agent['personality']}
    历史对话上下文：
    {context}
    请以{agent['name']}的身份发言，符合上述所有要求。
    """
    # 调用Gemini生成发言（优先使用，效果更稳定）
    full_content = ""
    try:
        genai.configure(api_key=gemini_api_key)
        agent_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            temperature=0.8  # 提高随机性，让发言更丰富
        )
        stream = agent_model.generate_content(agent_prompt, stream=True)
        for chunk in stream:
            if chunk.text:
                full_content += chunk.text
        # 清理内容，控制长度
        full_content = clean_extra_newlines(full_content)
        if len(full_content) < 20:
            full_content = f"{agent['name']}：关于跨境{random.choice(['税务', '合规', '平台规则', '物流'])}问题，我补充一点：{full_content}"
    except:
        # 备用：Gemini失败时使用固定话术
        full_content = f"{agent['name']}：结合当前的跨境交流，我认为{random.choice(['合规是基础', '成本控制很重要', '当地法规必须重视', '平台规则要吃透'])}，建议大家{random.choice(['提前做好规划', '及时咨询专业人士', '关注政策更新'])}。"
    # 返回Agent发言信息
    return {
        "role": "agent",
        "role_type": agent['role_type'],
        "name": agent['name'],
        "avatar": agent['avatar'],
        "desc": agent['desc'],
        "content": full_content
    }

def schedule_agent_speech():
    """调度Agent自动发言：30-60秒随机间隔"""
    if st.session_state.get("agent_running", True):
        # 生成并添加Agent发言
        agent_msg = generate_agent_message()
        st.session_state.messages.append(agent_msg)
        # 重新运行页面，刷新展示
        st.rerun()
        # 随机生成下一次发言时间（30-60秒）
        next_interval = random.randint(30, 60)
        # 调度下一次发言
        Timer(next_interval, schedule_agent_speech).start()

# -------------------------------------------------------------
# --- 5. 初始化与状态配置 ---
# -------------------------------------------------------------
# API密钥配置
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
glm_api_key = st.secrets.get("GLM_API_KEY", "")
st.session_state["api_configured"] = bool(gemini_api_key)

# 初始化Gemini模型
@st.cache_resource
def initialize_gemini_model():
    if not gemini_api_key: return None
    return genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction="你是跨境贸易合规专家，为中国出海企业提供专业、严谨的财税、合规、法律建议。"
    )
gemini_model = initialize_gemini_model()

# 初始化对话状态
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "🌐 欢迎来到跨境企业Agent社区！这里有跨境企业主、律师、合规机构、电商平台实时交流，30-60秒自动发言，也可手动提问参与讨论～"
        }
    ]
# 初始化Agent运行状态
if "agent_running" not in st.session_state:
    st.session_state["agent_running"] = True
# 首次启动Agent调度
if not st.session_state.get("agent_scheduled", False):
    st.session_state["agent_scheduled"] = True
    # 延迟5秒启动，避免页面加载时卡顿
    Timer(5, schedule_agent_speech).start()

# -------------------------------------------------------------
# --- 6. 数据库与访问统计（保留原有功能）---
# -------------------------------------------------------------
DB_FILE = "visit_stats.db"
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, pv_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (visitor_id TEXT PRIMARY KEY, first_visit_date TEXT)''')
    c.execute("PRAGMA table_info(visitors)")
    columns = [info[1] for info in c.fetchall()]
    if "last_visit_date" not in columns:
        try:
            c.execute("ALTER TABLE visitors ADD COLUMN last_visit_date TEXT")
            c.execute("UPDATE visitors SET last_visit_date = first_visit_date WHERE last_visit_date IS NULL")
        except: pass
    conn.commit()
    conn.close()

def get_visitor_id():
    if "visitor_id" not in st.session_state:
        st.session_state["visitor_id"] = str(uuid.uuid4())
    return st.session_state["visitor_id"]

def track_and_get_stats():
    init_db()
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    today_str = datetime.datetime.utcnow().date().isoformat()
    visitor_id = get_visitor_id()
    if "has_counted" not in st.session_state:
        try:
            c.execute("INSERT OR IGNORE INTO daily_traffic (date, pv_count) VALUES (?, 0)", (today_str,))
            c.execute("UPDATE daily_traffic SET pv_count = pv_count + 1 WHERE date=?", (today_str,))
            c.execute("SELECT visitor_id FROM visitors WHERE visitor_id=?", (visitor_id,))
            if c.fetchone():
                c.execute("UPDATE visitors SET last_visit_date=? WHERE visitor_id=?", (today_str, visitor_id))
            else:
                c.execute("INSERT INTO visitors (visitor_id, first_visit_date, last_visit_date) VALUES (?, ?, ?)", 
                          (visitor_id, today_str, today_str))
            conn.commit()
            st.session_state["has_counted"] = True
        except Exception as e:
            st.error(f"数据库写入错误: {e}")
    c.execute("SELECT COUNT(*) FROM visitors WHERE last_visit_date=?", (today_str,))
    today_uv = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM visitors")
    total_uv = c.fetchone()[0]
    c.execute("SELECT pv_count FROM daily_traffic WHERE date=?", (today_str,))
    res_pv = c.fetchone()
    today_pv = res_pv[0] if res_pv else 0
    conn.close()
    return today_uv, total_uv, today_pv

# 执行统计
try:
    today_uv, total_uv, today_pv = track_and_get_stats()
except Exception as e:
    today_uv, total_uv, today_pv = 0, 0, 0

# -------------------------------------------------------------
# --- 7. 页面渲染（核心：Agent聊天气泡展示）---
# -------------------------------------------------------------
# 自定义顶部导航栏
st.markdown(f"""
<div class="nav-bar">
    <div>
        <span class="logo-text">🌐 跨境企业Agent社区</span>
        <span class="nav-tag">AI 模拟对话系统</span>
    </div>
    <span class="status-tag">{'🟢 Agent在线交流中' if st.session_state.get('agent_running') else '🔴 Agent已暂停'}</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# 标题区域
st.markdown("""
<div class="hero-section">
    <h1 class="page-title">跨境贸易合规交流社区</h1>
    <div class="subtitle">汇聚跨境企业主、涉外律师、税务合规机构、电商平台，实时交流跨境贸易实操问题</div>
</div>
""", unsafe_allow_html=True)

# Agent操作提示
st.markdown("""
<div class="agent-tips">
    📌 社区规则：1. 30-60秒自动有Agent发言；2. 发言基于历史上下文，贴合角色身份；3. 可手动提问，Agent会针对性回应
</div>
""", unsafe_allow_html=True)

# 历史消息渲染（核心：区分Agent/用户/助手角色）
st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg["role"] == "agent":
        # Agent角色消息渲染（带专属样式）
        st.markdown(f"""
        <div class="chat-row role-{msg['role_type']}">
            <div>
                <div class="chat-avatar">{msg['avatar']}</div>
                <div class="chat-role">{msg['desc']}</div>
            </div>
            <div class="chat-bubble">
                <div class="chat-nickname">{msg['name']}</div>
                {markdown_to_html(msg['content'])}
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif msg["role"] == "user":
        # 用户消息渲染
        st.markdown(f"""
        <div class="chat-row">
            <div>
                <div class="chat-avatar">{USER_ICON}</div>
                <div class="chat-role">用户</div>
            </div>
            <div class="chat-bubble" style="background-color: #0056b3; color: white;">
                {msg['content']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 助手消息渲染
        st.markdown(f"""
        <div class="chat-row">
            <div>
                <div class="chat-avatar">🤖</div>
                <div class="chat-role">智能助手</div>
            </div>
            <div class="chat-bubble" style="background-color: #f8f9fa; border: 1px solid #e0e0e0;">
                {markdown_to_html(msg['content'])}
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 用户输入处理 ---
chat_input_text = st.chat_input("请输入你的跨境贸易问题，参与社区讨论...")
if chat_input_text and st.session_state.get("api_configured", False):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": chat_input_text})
    # 立即触发一次Agent回应（提升交互性）
    st.session_state.messages.append(generate_agent_message())
    st.rerun()

# --- Agent控制按钮 ---
col1, col2 = st.columns(2)
with col1:
    if st.button("📌 立即触发Agent发言", use_container_width=True):
        st.session_state.messages.append(generate_agent_message())
        st.rerun()
with col2:
    if st.session_state.get("agent_running", True):
        if st.button("⏸️ 暂停Agent自动发言", use_container_width=True):
            st.session_state["agent_running"] = False
            st.rerun()
    else:
        if st.button("▶️ 恢复Agent自动发言", use_container_width=True):
            st.session_state["agent_running"] = True
            schedule_agent_speech()
            st.rerun()

# --- 重置对话按钮 ---
if st.button('🔄 重置社区对话', key="reset_btn", help="清空所有对话历史"):
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "🌐 欢迎来到跨境企业Agent社区！这里有跨境企业主、律师、合规机构、电商平台实时交流，30-60秒自动发言，也可手动提问参与讨论～"
        }
    ]
    st.rerun()

# --- 访问统计展示 ---
st.markdown(f"""
<div class="metric-container">
    <div class="metric-box">
        <div class="metric-sub">今日访客: {today_uv} 人</div>
    </div>
    <div class="metric-box" style="border-left: 1px solid #dee2e6; border-right: 1px solid #dee2e6; padding: 0 20px;">
        <div class="metric-sub">历史总访客: {total_uv} 人</div>
    </div>
    <div class="metric-box">
        <div class="metric-sub">今日访问量: {today_pv} 次</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
