import os
import shutil
import subprocess
import sys

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from data_loader import WORKSPACE_DB, load_to_sqlite, profile_database
from gemini_client import DEFAULT_MODEL, get_api_key
from sql_engine import answer_question, suggest_questions

load_dotenv()

st.set_page_config(
    page_title="DataChat Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM UI
# ============================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Main background */
.stApp {
    background:
        radial-gradient(circle at 10% 10%, rgba(99,102,241,.12), transparent 30%),
        radial-gradient(circle at 90% 20%, rgba(168,85,247,.10), transparent 30%),
        linear-gradient(135deg, #090d18 0%, #111827 50%, #0b1020 100%);
    color: #f8fafc;
}

/* Animated background blobs */
.stApp::before {
    content: "";
    position: fixed;
    width: 280px;
    height: 280px;
    border-radius: 50%;
    background: rgba(99,102,241,.08);
    top: 10%;
    left: 5%;
    filter: blur(60px);
    animation: floatOne 8s ease-in-out infinite;
    pointer-events: none;
}

.stApp::after {
    content: "";
    position: fixed;
    width: 240px;
    height: 240px;
    border-radius: 50%;
    background: rgba(236,72,153,.07);
    bottom: 10%;
    right: 5%;
    filter: blur(60px);
    animation: floatTwo 10s ease-in-out infinite;
    pointer-events: none;
}

@keyframes floatOne {
    0%,100% { transform: translate(0,0); }
    50% { transform: translate(40px,30px); }
}

@keyframes floatTwo {
    0%,100% { transform: translate(0,0); }
    50% { transform: translate(-35px,-25px); }
}

/* Header */
.hero {
    padding: 25px 30px;
    border-radius: 24px;
    background: linear-gradient(
        135deg,
        rgba(30,41,59,.92),
        rgba(30,27,75,.86)
    );
    border: 1px solid rgba(255,255,255,.10);
    box-shadow: 0 20px 60px rgba(0,0,0,.25);
    margin-bottom: 25px;
    animation: fadeIn .7s ease;
}

.hero h1 {
    font-size: 42px;
    font-weight: 800;
    margin: 0;
}

.hero p {
    color: #cbd5e1;
    font-size: 16px;
    margin-top: 8px;
}

.robot {
    font-size: 70px;
    display: inline-block;
    animation: robotFloat 3s ease-in-out infinite;
}

@keyframes robotFloat {
    0%,100% { transform: translateY(0) rotate(-2deg); }
    50% { transform: translateY(-10px) rotate(2deg); }
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Cards */
.info-card {
    padding: 18px;
    border-radius: 18px;
    background: rgba(30,41,59,.65);
    border: 1px solid rgba(255,255,255,.08);
    margin-bottom: 15px;
    transition: .25s ease;
}

.info-card:hover {
    transform: translateY(-3px);
    border-color: rgba(129,140,248,.45);
    box-shadow: 0 12px 35px rgba(0,0,0,.18);
}

.status-online {
    color: #86efac;
    font-weight: 700;
}

.status-offline {
    color: #fca5a5;
    font-weight: 700;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a, #111827);
    border-right: 1px solid rgba(255,255,255,.08);
}

section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #f8fafc;
}

/* Buttons */
.stButton > button {
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,.12);
    background: rgba(51,65,85,.75);
    color: white;
    font-weight: 600;
    transition: all .2s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    border-color: rgba(129,140,248,.7);
    box-shadow: 0 8px 25px rgba(0,0,0,.2);
}

/* Chat */
[data-testid="stChatMessage"] {
    border-radius: 18px;
    padding: 10px;
    margin-bottom: 12px;
    animation: fadeIn .35s ease;
}

/* Code */
.stCodeBlock {
    border-radius: 15px;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 15px;
    overflow: hidden;
}

/* Expander */
[data-testid="stExpander"] {
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,.08);
}

/* Suggestion buttons */
.suggestion-title {
    font-size: 18px;
    font-weight: 700;
    margin: 20px 0 10px;
}

.footer {
    text-align: center;
    color: #64748b;
    font-size: 12px;
    margin-top: 50px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNCTIONS
# ============================================================

def show_chart(df: pd.DataFrame):
    if df.shape[0] < 2 or df.shape[1] < 2:
        return

    x = df.columns[0]

    nums = [
        c for c in df.columns[1:]
        if pd.api.types.is_numeric_dtype(df[c])
    ]

    if not nums:
        return

    data = df.set_index(x)[nums]

    is_time = any(
        k in str(x).lower()
        for k in ("date", "month", "year", "week", "day", "quarter")
    )

    st.markdown("### 📈 Visualization")

    if is_time:
        st.line_chart(data)
    else:
        st.bar_chart(data)


def render_result(msg: dict, key: str):

    if msg.get("summary"):
        st.markdown(
            f"""
            <div class="info-card">
                <b>🤖 DataChat says</b><br><br>
                {msg["summary"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("🔍 View SQL generated by Gemini"):
        st.code(msg["sql"], language="sql")

    st.markdown("### 📊 Results")

    st.dataframe(
        msg["df"],
        use_container_width=True,
        hide_index=True,
    )

    show_chart(msg["df"])

    st.download_button(
        "⬇️ Download Results as CSV",
        msg["df"].to_csv(index=False),
        file_name="datachat_result.csv",
        mime="text/csv",
        key=key,
    )


def clear_chat():
    st.session_state["messages"] = []
    st.session_state["suggestions"] = []
    st.session_state["pending"] = None


def remove_dataset():
    clear_chat()

    if os.path.exists(WORKSPACE_DB):
        try:
            os.remove(WORKSPACE_DB)
        except PermissionError:
            pass

    st.session_state["profile"] = ""


def new_session():
    remove_dataset()

    # Remove cached session values
    for key in ["messages", "suggestions", "pending", "profile"]:
        st.session_state.pop(key, None)

    st.rerun()


# ============================================================
# SESSION STATE
# ============================================================

st.session_state.setdefault("messages", [])
st.session_state.setdefault("suggestions", [])
st.session_state.setdefault("pending", None)
st.session_state.setdefault("profile", "")


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="text-align:center; padding:10px;">
            <div style="font-size:55px;">🤖</div>
            <h2 style="margin:0;">DataChat</h2>
            <small style="color:#94a3b8;">Your AI Data Copilot</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Gemini
    st.subheader("🧠 Gemini AI")

    env_key = get_api_key()

    entered_key = st.text_input(
        "Gemini API key",
        value=env_key,
        type="password",
        help="Your key is used only for this local Streamlit session.",
    )

    if entered_key.strip():
        os.environ["GEMINI_API_KEY"] = entered_key.strip()

        st.markdown(
            '<div class="status-online">🟢 Gemini Connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-offline">🔴 Gemini Not Connected</div>',
            unsafe_allow_html=True,
        )

    st.caption(f"Model: {DEFAULT_MODEL}")

    st.divider()

    # Data
    st.subheader("📂 Data Workspace")

    uploads = st.file_uploader(
        "Upload your dataset",
        type=["csv", "xlsx", "xls", "db", "sqlite"],
        accept_multiple_files=True,
    )

    if st.button(
        "📥 Load Dataset",
        disabled=not uploads,
        use_container_width=True,
    ):
        try:
            sqlite_files = [
                u for u in uploads
                if u.name.lower().endswith((".db", ".sqlite"))
            ]

            if sqlite_files:
                with open(WORKSPACE_DB, "wb") as out:
                    out.write(sqlite_files[0].getbuffer())
            else:
                load_to_sqlite(
                    [(u.name, u) for u in uploads]
                )

            st.session_state["messages"] = []
            st.session_state["suggestions"] = []
            st.session_state["profile"] = profile_database()

            st.success("✅ Dataset loaded!")

        except Exception as e:
            st.error(f"Could not load files: {e}")

    if st.button(
        "🎮 Use Demo Data",
        use_container_width=True,
    ):
        try:
            subprocess.run(
                [sys.executable, "setup_db.py"],
                check=True,
            )

            shutil.copy("sample.db", WORKSPACE_DB)

            st.session_state["messages"] = []
            st.session_state["suggestions"] = []
            st.session_state["profile"] = profile_database()

            st.success("🎮 Demo data loaded!")

        except Exception as e:
            st.error(f"Could not load demo data: {e}")

    st.divider()

    # Session controls
    st.subheader("🧹 Session Controls")

    if st.button(
        "🧹 Clear Chat",
        use_container_width=True,
    ):
        clear_chat()
        st.success("Chat cleared!")

    if st.button(
        "🗑️ Remove Dataset",
        use_container_width=True,
    ):
        remove_dataset()
        st.success("Dataset removed!")

    if st.button(
        "🆕 New Session",
        use_container_width=True,
    ):
        new_session()

    st.divider()

    st.caption(
        "🔒 Your dataset stays local in SQLite. "
        "Only the required schema, question and limited result information "
        "are sent to Gemini."
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div style="display:flex; align-items:center; gap:20px;">
            <div class="robot">🤖</div>
            <div>
                <h1>DataChat Copilot</h1>
                <p>
                    Talk to your data. Generate SQL. Discover insights.
                    Visualize results.
                </p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA STATUS
# ============================================================

if os.path.exists(WORKSPACE_DB):

    profile = (
        st.session_state.get("profile")
        or profile_database()
    )

    st.markdown(
        """
        <div class="info-card">
            <b>🟢 Dataset Ready</b><br>
            Your data is loaded and ready to analyze.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
        <div class="info-card">
            <div style="font-size:40px;">📂</div>
            <h3>No dataset loaded</h3>
            <p>
                Upload a CSV/Excel/SQLite file from the sidebar,
                or try the demo dataset.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not get_api_key():
        st.warning(
            "🔑 Add your Gemini API key from the sidebar."
        )

    st.stop()


# ============================================================
# GEMINI STATUS
# ============================================================

if not get_api_key():
    st.warning(
        "🔑 Add your Gemini API key in the sidebar "
        "before asking questions."
    )


# ============================================================
# DATA OVERVIEW
# ============================================================

with st.expander(
    "📊 Explore Dataset",
    expanded=not st.session_state["messages"],
):

    st.code(profile)

    st.markdown(
        '<div class="suggestion-title">💡 Need ideas?</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "✨ Generate Smart Questions",
        disabled=not get_api_key(),
    ):

        with st.spinner("🤖 DataChat is exploring your dataset..."):

            try:
                st.session_state["suggestions"] = (
                    suggest_questions()
                )

            except Exception as e:
                st.error(
                    f"Could not generate suggestions: {e}"
                )

    for i, q in enumerate(
        st.session_state["suggestions"]
    ):

        if st.button(
            f"💬 {q}",
            key=f"sug{i}",
            use_container_width=True,
        ):
            st.session_state["pending"] = q


# ============================================================
# CHAT HISTORY
# ============================================================

for i, m in enumerate(
    st.session_state["messages"]
):

    with st.chat_message(
        m["role"],
        avatar="🧑‍💻" if m["role"] == "user" else "🤖",
    ):

        if m["role"] == "user":

            st.write(m["content"])

        elif "error" in m:

            st.warning(m["error"])

        else:

            render_result(
                m,
                key=f"dl{i}",
            )


# ============================================================
# CHAT INPUT
# ============================================================

prompt = st.chat_input(
    "💬 Ask something about your data...",
    disabled=not get_api_key(),
)

if st.session_state.get("pending"):

    prompt = st.session_state.pop("pending")


# ============================================================
# PROCESS QUESTION
# ============================================================

if prompt:

    history = []

    messages = st.session_state["messages"]

    for i in range(len(messages) - 1):

        if (
            messages[i]["role"] == "user"
            and messages[i + 1].get("role") == "assistant"
            and "sql" in messages[i + 1]
        ):

            history.append(
                {
                    "question": messages[i]["content"],
                    "sql": messages[i + 1]["sql"],
                }
            )

    # User message
    st.session_state["messages"].append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message(
        "user",
        avatar="🧑‍💻",
    ):
        st.write(prompt)

    # AI response
    with st.chat_message(
        "assistant",
        avatar="🤖",
    ):

        with st.spinner(
            "🤖 DataChat is thinking..."
        ):

            try:

                res = answer_question(
                    prompt,
                    history,
                )

                msg = {
                    "role": "assistant",
                    **res,
                }

                render_result(
                    msg,
                    key=f"dl{len(st.session_state['messages'])}",
                )

            except ValueError as e:

                msg = {
                    "role": "assistant",
                    "error": str(e),
                }

                st.warning(str(e))

            except Exception as e:

                msg = {
                    "role": "assistant",
                    "error": f"Something went wrong: {e}",
                }

                st.error(msg["error"])

    st.session_state["messages"].append(msg)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        🤖 DataChat Copilot • Gemini-powered data analysis •
        Local SQLite workspace
    </div>
    """,
    unsafe_allow_html=True,
)