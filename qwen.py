"""Offline Qwen3 coding assistant — Streamlit front-end for a local vLLM server.

Start the model server first (see serve_vllm.sh), then run this app:

    streamlit run app.py

Environment overrides:
    VLLM_BASE_URL   default http://localhost:8000/v1
    VLLM_API_KEY    default sk-local
    VLLM_MODEL      default qwen3-8b
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime

import streamlit as st

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    st.error("Missing dependencies. Run:  pip install streamlit openai")
    st.stop()


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DEFAULT_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
DEFAULT_API_KEY = os.getenv("VLLM_API_KEY", "sk-local")
DEFAULT_MODEL = os.getenv("VLLM_MODEL", "qwen3-8b")

SYSTEM_PROMPTS: dict[str, str] = {
    "Coding assistant": (
        "You are a senior software engineer acting as an offline coding assistant. "
        "Rules: answer with correct, runnable code; prefer whole files over fragments "
        "when asked to implement something; always tag fenced code blocks with the "
        "language; call out edge cases, failure modes and complexity in one short "
        "section; if the request is ambiguous, state your assumption in a single line "
        "and then answer; never invent library APIs you are unsure about — say so "
        "instead. Skip pleasantries and filler."
    ),
    "Code reviewer": (
        "You are a meticulous code reviewer. For the code you are given, report "
        "findings grouped as Bugs, Security, Performance, Style. Cite file and line "
        "where possible, explain why each finding matters, and propose a concrete fix "
        "as a replacement snippet or diff. Rank findings by severity. Do not rewrite "
        "code that is already correct."
    ),
    "Debugging partner": (
        "You are a debugging partner. Given an error, stack trace or failing test, "
        "first restate the symptom in one line, then list the most likely root causes "
        "in order of probability, then give the exact commands or code to confirm or "
        "eliminate each one. Ask for the smallest missing piece of information only if "
        "you genuinely cannot proceed."
    ),
    "Explain like a tutor": (
        "You are a patient programming tutor. Explain the concept from first "
        "principles, build up with a tiny runnable example, then show a realistic "
        "one. Name the common misconceptions. End with exactly two short exercises."
    ),
    "Commit / docs writer": (
        "You write concise engineering prose. Given a diff or a description, produce "
        "Conventional Commits messages, PR descriptions, or docstrings as requested. "
        "Be specific, use the imperative mood, and never pad with adjectives."
    ),
}

st.set_page_config(page_title="Offline Code Assistant", page_icon="🧑‍💻", layout="wide")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def split_think(text: str) -> tuple[str, str]:
    """Split an inline  thinking...</think> block out of a completion.

    Returned as (reasoning, answer). Handles the case where the vLLM server has
    no --reasoning-parser configured and leaves the tags in `content`.
    """
    if "</think>" not in text:
        return "", text
    head, _, tail = text.partition("</think>")
    reasoning = head.split(" thinking", 1)[-1] if " thinking" in head else head
    return reasoning.strip(), tail.strip()


@st.cache_resource(show_spinner=False)
def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(
        base_url=base_url,
        api_key=api_key or "EMPTY",
        timeout=900.0,
        max_retries=0,
    )


def render_history() -> None:
    for msg in st.session_state["messages"]:
        if msg["role"] == "system":
            continue
        avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg.get("reasoning"):
                with st.expander("🧠 Reasoning", expanded=False):
                    st.markdown(msg["reasoning"])
            st.markdown(msg["content"])


for key, default in (("messages", []), ("last_stats", None), ("pinned", "")):
    st.session_state.setdefault(key, default)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.header("⚙️ Server")
    base_url = st.text_input("Base URL", DEFAULT_BASE_URL)
    api_key = st.text_input("API key", DEFAULT_API_KEY, type="password")
    client = get_client(base_url, api_key)

    if st.button("Test connection", use_container_width=True):
        try:
            st.session_state["model_ids"] = [m.id for m in client.models.list().data]
            st.success(f"Online — {len(st.session_state['model_ids'])} model(s)")
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            st.session_state["model_ids"] = []
            st.error(f"Unreachable: {exc}")

    model_ids = st.session_state.get("model_ids") or []
    if model_ids:
        model = st.selectbox("Model", model_ids)
    else:
        model = st.text_input("Model", DEFAULT_MODEL)

    st.divider()
    st.header("🎛️ Generation")
    thinking = st.toggle(
        "Thinking mode",
        value=True,
        help="Qwen3 reasons inside  thinking … </think> before answering. "
             "Slower, markedly better on hard problems.",
    )
    if thinking:
        temperature = st.slider("Temperature", 0.0, 1.5, 0.6, 0.05)
        top_p = st.slider("Top-p", 0.1, 1.0, 0.95, 0.01)
    else:
        temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.05)
        top_p = st.slider("Top-p", 0.1, 1.0, 0.80, 0.01)

    max_tokens = st.slider(
        "Max new tokens", 256, 32768, 8192 if thinking else 4096, 256,
        help="Thinking mode needs headroom — too low and the answer comes back empty.",
    )
    keep_reasoning = st.checkbox(
        "Keep reasoning in history", value=False,
        help="Retaining chain-of-thought burns context fast. Off is recommended.",
    )
    st.caption("Qwen3 tips: never use temperature 0 in thinking mode (it loops). "
               "Leave presence penalty at 0 — it degrades reasoning.")

    st.divider()
    st.header("🧩 Prompt")
    preset = st.selectbox("System prompt preset", list(SYSTEM_PROMPTS))
    system_prompt = st.text_area("System prompt", SYSTEM_PROMPTS[preset], height=220)
    pinned = st.text_area(
        "Pinned context (optional)", st.session_state["pinned"], height=140,
        help="Code or notes prepended to every request — handy for a file you keep "
             "referring to.",
    )
    st.session_state["pinned"] = pinned

    st.divider()
    st.header("🗂️ Session")
    st.caption(f"{len(st.session_state['messages'])} message(s) in context")
    col_clear, col_export = st.columns(2)
    if col_clear.button("Clear", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["last_stats"] = None
        st.rerun()
    if st.session_state["messages"]:
        col_export.download_button(
            "Export",
            json.dumps(st.session_state["messages"], indent=2, ensure_ascii=False),
            file_name=f"chat-{datetime.now():%Y%m%d-%H%M%S}.json",
            mime="application/json",
            use_container_width=True,
        )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

st.title("🧑‍💻 Offline Code Assistant")
st.caption(f"Model `{model}` · vLLM at `{base_url}` · nothing leaves this machine")

render_history()
if st.session_state["last_stats"]:
    st.caption(st.session_state["last_stats"])

prompt = st.chat_input("Ask for code, a review, an explanation…")

if prompt:
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    system = system_prompt.strip()
    if pinned.strip():
        system += "\n\n# Pinned context\n" + pinned.strip()
    request_messages = [{"role": "system", "content": system}] + [
        {k: v for k, v in m.items() if k in ("role", "content")}
        for m in st.session_state["messages"]
    ]

    with st.chat_message("assistant", avatar="🤖"):
        think_slot = None
        if thinking:
            with st.expander("🧠 Reasoning", expanded=False):
                think_slot = st.empty()

        answer_slot = st.empty()
        answer_slot.markdown("_warming up…_")

        reasoning_text, answer_text = "", ""
        usage = None
        started = time.perf_counter()
        first_token_at = None
        finished_thinking = False
        error = None

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=request_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
                extra_body={"chat_template_kwargs": {"enable_thinking": bool(thinking)}},
            )
            for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = choices[0].delta

                reasoning_delta = getattr(delta, "reasoning_content", None)
                if reasoning_delta:
                    first_token_at = first_token_at or time.perf_counter()
                    reasoning_text += reasoning_delta
                    if think_slot is not None:
                        think_slot.markdown(reasoning_text + " ▌")

                if delta.content:
                    first_token_at = first_token_at or time.perf_counter()
                    if think_slot is not None and reasoning_text and not finished_thinking:
                        think_slot.markdown(reasoning_text)
                        finished_thinking = True
                    answer_text += delta.content
                    answer_slot.markdown(answer_text + " ▌")

        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            error = exc

        elapsed = time.perf_counter() - started

        # Normalise: the server may or may not have separated the reasoning.
        inline_reasoning, clean_answer = split_think(answer_text)
        if inline_reasoning:
            reasoning_text = (reasoning_text + "\n\n" + inline_reasoning).strip()
        if not clean_answer:
            clean_answer = answer_text

        if think_slot is not None:
            think_slot.markdown(reasoning_text or "_no reasoning emitted_")
        elif reasoning_text:
            # No --reasoning-parser on the server, but the model thought anyway.
            with st.expander("🧠 Reasoning", expanded=False):
                st.markdown(reasoning_text)

        if error is not None:
            answer_slot.error(
                f"Request failed: {error}\n\n"
                f"Is the vLLM server running? Try `curl {base_url}/models`."
            )
            st.session_state["messages"].pop()  # drop the orphaned user turn
        else:
            if not clean_answer:
                clean_answer = (
                    "_(the model spent the whole token budget thinking — raise "
                    "**Max new tokens** or turn Thinking mode off)_"
                )
            answer_slot.markdown(clean_answer)

            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            tps = completion_tokens / elapsed if elapsed > 0 else 0.0
            ttft = (first_token_at - started) if first_token_at else 0.0
            stats = (
                f"⏱ {elapsed:.1f}s · {completion_tokens} tokens out · "
                f"{tps:.1f} tok/s · TTFT {ttft:.2f}s · {prompt_tokens} tokens in"
            )
            st.session_state["last_stats"] = stats
            st.caption(stats)

            message: dict[str, str] = {"role": "assistant", "content": clean_answer}
            if keep_reasoning and reasoning_text:
                message["reasoning"] = reasoning_text
            st.session_state["messages"].append(message)
