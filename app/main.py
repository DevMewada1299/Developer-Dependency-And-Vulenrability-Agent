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
    prompt_style = st.selectbox("Prompt Style", ["compact_json", "react_json", "deliberate_json", "strict_schema"], index=0)
    st.session_state.prompt_style = prompt_style
    planning_mode = st.selectbox("Planning Mode", ["single", "consensus-3", "consensus-5"], index=0)
    st.session_state.planning_mode = planning_mode
    verify = st.checkbox("Verify/Refine Answer", value=False)
    st.session_state.verify = verify
    view = st.radio("View", ["Chat", "Stats"], index=0)
    st.session_state.view = view
    if uploaded is not None:
        up_dir = Path("data/uploads")
        up_dir.mkdir(parents=True, exist_ok=True)
        p = str(up_dir / "requirements_uploaded.txt")
        with open(p, "wb") as f:
            f.write(uploaded.read())
        st.session_state.req_path = p
    if st.button("Reset Chat"):
        st.session_state.messages = []

if st.session_state.get("view") == "Chat":
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

if st.session_state.get("view") == "Chat":
    query = st.chat_input("Ask about security and dependencies")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        out = advise(query, st.session_state.provider, st.session_state.req_path, history=st.session_state.messages, prompt_style=st.session_state.get("prompt_style", "compact_json"), planning_mode=st.session_state.get("planning_mode", "single"), verify=st.session_state.get("verify", False))
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
                st.write({"provider": meta.get("provider"), "model": meta.get("model"), "llm": meta.get("llm"), "prompt_style": meta.get("prompt_style"), "planning_mode": meta.get("planning_mode"), "verify_ms": meta.get("verify_ms")})

if st.session_state.get("view") == "Stats":
    from src.storage.db import fetch_recent_sessions, fetch_tool_calls
    import pandas as pd
    rows = fetch_recent_sessions(limit=100)
    if rows:
        st.subheader("Recent Sessions")
        st.dataframe(pd.DataFrame(rows))
        sel = st.selectbox("Select session id", [r["id"] for r in rows])
        calls = fetch_tool_calls(session_id=int(sel))
        st.subheader("Tool Calls")
        st.dataframe(pd.DataFrame(calls))
