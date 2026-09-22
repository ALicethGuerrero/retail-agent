"""Interfaz de usuario con Streamlit para el asistente de Retail Electrónica."""

import streamlit as st

from app.agent import RetailAgent

st.set_page_config(page_title="Nexo | Retail Electrónica", page_icon="N", layout="wide")
st.title("Nexo")
st.caption("Asistente de Retail Electrónica")

if "agent" not in st.session_state:
    st.session_state.agent = RetailAgent()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.header("Memoria de la sesión")
    state = st.session_state.agent.state
    st.write(f"Cliente: {state.cliente_nombre or 'No identificado'}")
    st.write(f"Identificación: {state.cliente_identificacion or 'N/A'}")
    budget = (
        f"${state.presupuesto_mencionado:,.0f} COP"
        if state.presupuesto_mencionado
        else "N/A"
    )
    st.write(f"Presupuesto: {budget}")
    st.write(f"Último pedido: {state.ultimo_pedido_consultado or 'N/A'}")
    st.subheader("Productos vistos")
    if state.productos_consultados:
        for product in state.productos_consultados:
            st.write(f"- {product}")
    else:
        st.write("Ninguno")

    if st.button("Reiniciar conversación"):
        st.session_state.agent = RetailAgent()
        st.session_state.chat_history = []
        st.rerun()

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_prompt := st.chat_input("Escribe tu solicitud"):
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.write(user_prompt)
    with st.chat_message("assistant"):
        try:
            response_text = st.write_stream(
                st.session_state.agent.chat_stream(user_prompt)
            )
        except Exception as error:
            response_text = str(error)
            st.write(response_text)
    st.session_state.chat_history.append(
        {"role": "assistant", "content": response_text}
    )
    st.rerun()
