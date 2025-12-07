import os
from pathlib import Path
import sys
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import importlib
import src.agents.orchestrator as orchestrator
importlib.reload(orchestrator)
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
    st.session_state.messages.append({"role": "assistant", "content": ans})
    with st.chat_message("assistant"):
        st.write(ans)
