import os
import requests
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="MirAI Policy Advisor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"
INGEST_ENDPOINT = f"{BACKEND_URL}/ingest"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
REQUEST_TIMEOUT = 60  # seconds

# Injected Modern Cyber/Glassmorphism CSS
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
    /* Global Typography & Palette */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        letter-spacing: -0.02em;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1050px;
    }

    /* Gradient Hero Header */
    .hero-container {
        background: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.08) 50%, transparent 100%),
                    linear-gradient(180deg, rgba(17, 24, 39, 0.8) 0%, rgba(15, 23, 42, 0.6) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px 28px;
        margin-bottom: 24px;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #A78BFA 0%, #C084FC 40%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }

    .hero-subtitle {
        color: #94A3B8;
        font-size: 0.98rem;
        margin-top: 6px;
        margin-bottom: 14px;
    }

    .badge-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .tag-badge {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 9999px;
        background: rgba(139, 92, 246, 0.12);
        color: #C4B5FD;
        border: 1px solid rgba(139, 92, 246, 0.25);
    }

    .tag-badge-green {
        background: rgba(16, 185, 129, 0.12);
        color: #6EE7B7;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }

    /* Sidebar Glassmorphic Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D1117 0%, #0F172A 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    .sidebar-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
    }

    .status-live {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: #34D399;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-live::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
    }

    .status-offline {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: #F87171;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-offline::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #EF4444;
        box-shadow: 0 0 10px #EF4444;
    }

    /* Buttons Styling */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.88rem;
        transition: all 0.2s ease-in-out;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.04);
        color: #E2E8F0;
    }

    .stButton > button:hover {
        border-color: #8B5CF6;
        color: #F8FAFC;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7C3AED 0%, #6366F1 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1.5px);
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.5);
    }

    /* Chat Messages */
    [data-testid="stChatMessage"] {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 14px 18px;
        margin-bottom: 12px;
        backdrop-filter: blur(8px);
    }

    /* Chat Input Bar */
    [data-testid="stChatInput"] {
        border-radius: 16px;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        background: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)


def check_backend_health():
    """Verify backend API and ChromaDB status."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=3)
        if response.status_code == 200:
            return True, response.json()
        return False, {"error": f"Status code {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}


# Initialize session state for chat messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **Welcome to the Autonomous MirAI Policy Advisor!**\n\n"
                "I provide strictly grounded guidance derived from the official "
                "**Mirai School of Technology Student Policy Handbook (2026)**.\n\n"
                "Ask me about:\n"
                "- 📊 **Attendance Evaluation & Debarment Tiers**\n"
                "- 🏥 **Medical & Duty Leave Protocols**\n"
                "- 🎓 **Admit Card & No-Dues Process**\n"
                "- 🚀 **Student Club Formation & Budget Approvals**\n"
                "- ⚖️ **Code of Conduct & Examination Rules**"
            )
        }
    ]

# Sidebar: Controls & Live Health
with st.sidebar:
    st.markdown("### ⚡ Advisor Dashboard")
    
    # System Status Card
    is_online, health_data = check_backend_health()
    if is_online:
        st.markdown("""
        <div class="sidebar-card">
            <div class="status-live">Backend Online & Healthy</div>
            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">FastAPI :8000 • LCEL Chain Ready</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sidebar-card">
            <div class="status-offline">Backend Disconnected</div>
            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">Start FastAPI via: <code>uvicorn backend:app --port 8000</code></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Policy Ingestion Card
    st.markdown("#### 📁 Policy Handbook Ingestion")
    st.caption("Upload and update the official policy PDF into ChromaDB:")
    uploaded_file = st.file_uploader("Select Handbook PDF", type=["pdf"], key="policy_pdf_uploader")

    if uploaded_file is not None:
        if st.button("⚡ Index Handbook Document", use_container_width=True, type="primary"):
            with st.spinner("Chunking & embedding handbook into ChromaDB..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    resp = requests.post(INGEST_ENDPOINT, files=files, timeout=120)
                    if resp.status_code == 200:
                        res_data = resp.json()
                        st.success(f"✅ Ingestion Succeeded!\n{res_data.get('message')}")
                        st.info(f"Generated **{res_data.get('chunks_ingested', 0)}** semantic chunks.")
                    else:
                        st.error(f"❌ Failed ({resp.status_code}): {resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Could not connect to FastAPI server on port 8000.")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out while embedding chunks.")
                except Exception as ex:
                    st.error(f"⚠️ Unexpected error: {str(ex)}")

    st.markdown("---")

    # Quick Prompts
    st.markdown("#### 🎯 Quick Test Queries")
    st.caption("Benchmark queries from the certification audit:")

    sample_queries = [
        "I have 72% attendance. How many attendance marks will I get?",
        "I study at the Ratnam campus. I got sick and need medical leave. Who do I email and how many days do I have to submit my documents?",
        "We want to start a new Cybersecurity society under the Tech Club. Do we ask Management directly?",
        "How much is the fine for smoking a cigarette on campus?"
    ]

    for q in sample_queries:
        if st.button(q, key=f"btn_{hash(q)}", use_container_width=True):
            st.session_state.pending_query = q

    st.markdown("---")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Conversation reset. How can I assist you with Mirai student policies?"
            }
        ]
        st.rerun()

# Main Interactive View
st.markdown("""
<div class="hero-container">
    <div class="hero-title">Autonomous MirAI Student Policy Advisor</div>
    <div class="hero-subtitle">
        Institutional policy guidance powered by Multi-Query RAG and Gemini. Grounded strictly in the 2026 Student Handbook.
    </div>
    <div class="badge-strip">
        <span class="tag-badge tag-badge-green">● Zero Hallucination Mode</span>
        <span class="tag-badge">ChromaDB Vector Store</span>
        <span class="tag-badge">MultiQuery Retreiver</span>
        <span class="tag-badge">Mirai Handbook 2026</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle quick sidebar selection or live chat input
prompt_to_submit = None
if "pending_query" in st.session_state and st.session_state.pending_query:
    prompt_to_submit = st.session_state.pending_query
    st.session_state.pending_query = None

user_input = st.chat_input("Ask any policy question (e.g., attendance marks, leave notice, club proposals)...")
if user_input:
    prompt_to_submit = user_input

if prompt_to_submit:
    # Display user query
    st.session_state.messages.append({"role": "user", "content": prompt_to_submit})
    with st.chat_message("user"):
        st.markdown(prompt_to_submit)

    # Process assistant response with error resilience
    with st.chat_message("assistant"):
        with st.spinner("Analyzing policy clauses with MultiQueryRetriever..."):
            try:
                response = requests.post(
                    CHAT_ENDPOINT,
                    json={"question": prompt_to_submit},
                    timeout=REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    answer_text = response.json().get("answer", "No answer provided.")
                    st.markdown(answer_text)
                    st.session_state.messages.append({"role": "assistant", "content": answer_text})
                elif response.status_code == 400:
                    err_msg = response.json().get("detail", response.text)
                    st.warning(f"⚠️ **Notice:** {err_msg}")
                    st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {err_msg}"})
                else:
                    err_msg = f"Backend returned error ({response.status_code}): {response.text}"
                    st.error(f"❌ {err_msg}")
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ {err_msg}"})

            except requests.exceptions.ConnectionError:
                friendly_error = (
                    "🔌 **Backend Unreachable:** Could not connect to the FastAPI advisor server. "
                    "Please ensure `python backend.py` or `uvicorn backend:app --port 8000` is active."
                )
                st.error(friendly_error)
                st.session_state.messages.append({"role": "assistant", "content": friendly_error})

            except requests.exceptions.Timeout:
                timeout_error = (
                    "⏱️ **Request Timed Out:** The advisor backend took too long to formulate a response. "
                    "Please retry your question."
                )
                st.error(timeout_error)
                st.session_state.messages.append({"role": "assistant", "content": timeout_error})

            except Exception as e:
                general_error = f"⚠️ **Error encountered:** {str(e)}"
                st.error(general_error)
                st.session_state.messages.append({"role": "assistant", "content": general_error})
