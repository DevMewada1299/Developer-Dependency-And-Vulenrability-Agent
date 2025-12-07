import os
from pathlib import Path
import sys
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import importlib
for m in ["src.agents.orchestrator", "src.llm.client"]:
    if m in sys.modules:
        del sys.modules[m]
import src.llm.client as llm_client
import src.agents.orchestrator as orchestrator
from src.agents.orchestrator import advise

st.set_page_config(page_title="Dependency Security Assistant", layout="centered")
st.title("Dependency Security Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "provider" not in st.session_state:
    st.session_state.provider = "llama"
if "req_path" not in st.session_state:
    st.session_state.req_path = None

with st.sidebar:
    st.session_state.provider = st.selectbox("LLM Provider", ["llama", "phi"], index=0)
    uploaded = st.file_uploader("Upload requirements.txt", type=["txt"]) 
    if uploaded is not None:
        up_dir = Path("data/uploads")
        up_dir.mkdir(parents=True, exist_ok=True)
        p = str(up_dir / "requirements_uploaded.txt")
        with open(p, "wb") as f:
            f.write(uploaded.read())
        st.session_state.req_path = p
    if st.button("Reset Chat"):
        st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

query = st.chat_input("Ask about security and dependencies")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    out = advise(query, st.session_state.provider, st.session_state.req_path, history=st.session_state.messages)
    ans = out.get("answer_text") or ""
    st.session_state.messages.append({"role": "assistant", "content": ans, "out": out})
    with st.chat_message("assistant"):
        st.write(ans)
        with st.expander("Tool Calls"):
            st.write(out.get("plan") or [])
            meta = out.get("meta") or {}
            calls = meta.get("tool_calls") or []
            for c in calls:
                st.write({"tool": c.get("tool"), "args": c.get("args"), "duration_ms": c.get("duration_ms"), "stats": c.get("stats"), "fixed": c.get("fixed"), "packages_count": c.get("packages_count"), "releases_count": c.get("releases_count")})
        with st.expander("LLM Stats"):
            meta = out.get("meta") or {}
            st.write({"provider": meta.get("provider"), "model": meta.get("model"), "llm": meta.get("llm")})
