import os
import requests
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="MirAI Student Policy Advisor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"
INGEST_ENDPOINT = f"{BACKEND_URL}/ingest"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
REQUEST_TIMEOUT = 45  # seconds

# Custom CSS for polished UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .status-badge-online {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-offline {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .sample-pill {
        border-radius: 8px;
        background-color: #F3F4F6;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def check_backend_health():
    """Check connectivity to backend service."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, {"error": f"Status code {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}


# Initialize session state for chat messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am your **Autonomous MirAI Student Policy Advisor**. I can assist you with queries regarding Mirai School of Technology academic policies, attendance thresholds, medical leave protocols, admit cards, and student clubs. How can I help you today?"
        }
    ]

# Sidebar: Admin & Status Panel
with st.sidebar:
    st.title("⚙️ Admin & Controls")
    
    # Backend Status Indicator
    is_online, health_data = check_backend_health()
    if is_online:
        st.markdown('<span class="status-badge-online">● Backend Online</span>', unsafe_allow_html=True)
        if health_data.get("vector_store_initialized"):
            st.caption("✅ Knowledge base indexed")
        else:
            st.caption("⚠️ Knowledge base not yet initialized")
    else:
        st.markdown('<span class="status-badge-offline">● Backend Offline</span>', unsafe_allow_html=True)
        st.caption("Start backend with `python backend.py` on port 8000")

    st.divider()

    # Document Ingestion Section
    st.subheader("📄 Policy Document Ingestion")
    st.write("Upload or update the official Mirai Policy Handbook PDF:")
    uploaded_file = st.file_uploader("Select Handbook PDF", type=["pdf"], key="policy_pdf_uploader")

    if uploaded_file is not None:
        if st.button("📤 Upload & Ingest Handbook", use_container_width=True, type="primary"):
            with st.spinner("Uploading and indexing handbook into ChromaDB..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    resp = requests.post(INGEST_ENDPOINT, files=files, timeout=120)
                    
                    if resp.status_code == 200:
                        res_data = resp.json()
                        st.success(f"✅ Ingestion Successful!\n{res_data.get('message')}")
                        st.info(f"Indexed **{res_data.get('chunks_ingested', 0)}** semantic chunks.")
                    else:
                        st.error(f"❌ Ingestion Failed ({resp.status_code}): {resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🚨 Cannot connect to backend server. Please verify FastAPI is running at `http://localhost:8000`.")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Ingestion timed out. The file may be very large or the embedding model is rate-limited.")
                except Exception as ex:
                    st.error(f"⚠️ An unexpected error occurred: {str(ex)}")

    st.divider()

    # Pre-built Sample Questions
    st.subheader("💡 Frequently Asked Queries")
    sample_queries = [
        "I have 72% attendance. How many attendance marks will I get?",
        "I study at the Ratnam campus. I got sick and need medical leave. Who do I email and how many days do I have to submit my documents?",
        "We want to start a new Cybersecurity society under the Tech Club. Do we ask Management directly?",
        "How much is the fine for smoking a cigarette on campus?"
    ]

    for q in sample_queries:
        if st.button(f"📌 {q}", key=f"sample_{hash(q)}", use_container_width=True):
            st.session_state.pending_query = q

    st.divider()
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat history cleared. How can I assist you with Mirai school policies?"
            }
        ]
        st.rerun()

# Main Chat View
st.markdown('<div class="main-header">🎓 Autonomous MirAI Student Policy Advisor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Official AI-powered policy guidance grounded strictly in the Mirai School of Technology Student Handbook (2026).</div>', unsafe_allow_html=True)

# Display existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Check if a sample query was selected via sidebar
prompt_to_submit = None
if "pending_query" in st.session_state and st.session_state.pending_query:
    prompt_to_submit = st.session_state.pending_query
    st.session_state.pending_query = None

# Get new user query from chat input
user_input = st.chat_input("Ask a question about Mirai student policies, attendance, leaves, or clubs...")
if user_input:
    prompt_to_submit = user_input

if prompt_to_submit:
    # Append user question to state and display
    st.session_state.messages.append({"role": "user", "content": prompt_to_submit})
    with st.chat_message("user"):
        st.markdown(prompt_to_submit)

    # Process assistant response with error resilience
    with st.chat_message("assistant"):
        with st.spinner("Consulting official policy handbook..."):
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
                    err_msg = f"Backend returned error code {response.status_code}: {response.text}"
                    st.error(f"❌ {err_msg}")
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ {err_msg}"})

            except requests.exceptions.ConnectionError:
                friendly_error = (
                    "🔌 **Connection Error:** Could not reach the policy advisor backend. "
                    "Please ensure the FastAPI backend is running at `http://localhost:8000`."
                )
                st.error(friendly_error)
                st.session_state.messages.append({"role": "assistant", "content": friendly_error})

            except requests.exceptions.Timeout:
                timeout_error = (
                    "⏱️ **Request Timed Out:** The advisor backend took too long to generate a response. "
                    "Please try your question again in a moment."
                )
                st.error(timeout_error)
                st.session_state.messages.append({"role": "assistant", "content": timeout_error})

            except Exception as e:
                general_error = f"⚠️ **Error encountered:** {str(e)}"
                st.error(general_error)
                st.session_state.messages.append({"role": "assistant", "content": general_error})
