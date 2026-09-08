import streamlit as st

from .chat_engine import (
    create_interaction,
    delete_local_api_key,
    load_api_key,
    save_api_key,
)


AI_STUDIO_KEY_URL = "https://aistudio.google.com/apikey"


def _reset_chat():
    st.session_state["chat_messages"] = []
    st.session_state.pop("chat_interaction_id", None)
    st.session_state.pop("chat_model", None)


def _activate_key(api_key):
    save_api_key(api_key)
    _reset_chat()


def _remove_key():
    delete_local_api_key()
    _reset_chat()


def render_chat_page():
    st.title("💬 Chat")
    st.write(
        "Chat AI generale integrata in Porca MaDovbyk AI. "
        "Puoi fare domande, chiedere spiegazioni, confronti, idee o analisi direttamente qui."
    )

    api_key, key_source = load_api_key()

    if not api_key:
        st.info(
            "Per attivare la Chat serve una chiave Gemini API. "
            "La puoi creare in Google AI Studio; se la salvi qui resta soltanto su questo PC "
            "e non viene caricata su GitHub."
        )

        st.link_button(
            "🔑 Crea / gestisci chiave in Google AI Studio",
            AI_STUDIO_KEY_URL,
            use_container_width=False,
        )

        new_key = st.text_input(
            "Gemini API key",
            type="password",
            placeholder="Incolla qui la chiave...",
            help="Viene salvata localmente in .streamlit/gemini_api_key.txt, file escluso da Git.",
        )

        if st.button(
            "✅ Salva chiave e attiva Chat",
            type="primary",
            use_container_width=True,
            disabled=not bool(new_key.strip()),
        ):
            try:
                _activate_key(new_key)
                st.success("Chat attivata su questo PC.")
                st.rerun()
            except Exception as exc:
                st.error(f"Non riesco a salvare la chiave: {exc}")

        return

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    left, right = st.columns([4, 1.3])
    with left:
        source_label = (
            "chiave locale protetta da .gitignore"
            if key_source == "local"
            else "chiave da variabile d'ambiente"
        )
        model = st.session_state.get("chat_model")
        model_text = f" · modello {model}" if model else ""
        st.caption(f"🟢 Chat attiva · Gemini Interactions API · {source_label}{model_text}")

    with right:
        if st.button("🧹 Nuova chat", use_container_width=True):
            _reset_chat()
            st.rerun()

    with st.expander("⚙️ Impostazioni Chat", expanded=False):
        st.caption(
            "La conversazione usa lo stato server-side Gemini tramite interaction ID. "
            "La cronologia visibile resta nella sessione della Dashboard."
        )
        if key_source == "local":
            if st.button("🗑️ Rimuovi chiave salvata da questo PC"):
                _remove_key()
                st.rerun()
        else:
            st.caption(
                "La chiave arriva da GEMINI_API_KEY: per rimuoverla va eliminata dalla variabile d'ambiente."
            )

    if not st.session_state["chat_messages"]:
        st.markdown(
            "**Esempi:** `Confrontami due giocatori`, `Spiegami una regola`, "
            "`Dammi un'idea per un allenamento`, `Riassumi questo concetto`, "
            "oppure qualsiasi altra domanda generale."
        )

    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Scrivi un messaggio...")

    if not prompt:
        return

    st.session_state["chat_messages"].append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sto rispondendo..."):
            try:
                result = create_interaction(
                    api_key=api_key,
                    prompt=prompt,
                    previous_interaction_id=st.session_state.get("chat_interaction_id"),
                    preferred_model=st.session_state.get("chat_model"),
                )
                answer = result["text"]
                st.markdown(answer)

                st.session_state["chat_messages"].append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )
                if result.get("interaction_id"):
                    st.session_state["chat_interaction_id"] = result["interaction_id"]
                if result.get("model"):
                    st.session_state["chat_model"] = result["model"]

            except Exception as exc:
                st.error(str(exc))
                st.caption(
                    "Se la chiave è valida ma compare un limite/quota, verifica il progetto in Google AI Studio."
                )
