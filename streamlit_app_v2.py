import streamlit as st
from streamlit_oauth import OAuth2Component
import replicate
import os

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
DESCOPE_DOMAIN = os.environ.get("DESCOPE_DOMAIN")

AUTHORIZE_URL = os.environ.get(f"https://{DESCOPE_DOMAIN}/oauth2/v1/authorize")
TOKEN_URL = os.environ.get(f"https://{DESCOPE_DOMAIN}/oauth2/v1/token")
REVOKE_TOKEN_URL = os.environ.get(f"https://{DESCOPE_DOMAIN}/v1/oauth2/revoke")

# App title
st.set_page_config(page_title="🦙💬 Ask a Llama Chatbot")

oauth2 = OAuth2Component(
    client_id=CLIENT_ID,
    authorize_endpoint=AUTHORIZE_URL,
    token_endpoint=TOKEN_URL,
    refresh_token_endpoint=TOKEN_URL,
    revoke_token_endpoint=REVOKE_TOKEN_URL,
)

if "token" not in st.session_state:
    # If not, show authorize button
    result = oauth2.authorize_button(
        "Continue with Descope",
        icon="https://avatars.githubusercontent.com/u/97479186?s=200&v=4",
        redirect_uri="http://localhost:8501",
        scope="openid email profile descope.claims descope.custom_claims",
        key="descope",
        use_container_width=True,
        pkce="S256",
    )
    if result and "token" in result:
        # If authorization successful, save token in session state
        st.session_state.token = result.get("token")
        st.rerun()
else:
    token = st.session_state["token"]
    st.json(token)

    with st.sidebar:
        st.title("🦙💬 Llama 2 Chatbot")
        if "REPLICATE_API_TOKEN" in st.secrets:
            st.success("API key already provided!", icon="✅")
            replicate_api = st.secrets["REPLICATE_API_TOKEN"]
        else:
            replicate_api = st.text_input("Enter Replicate API token:", type="password")
            if not (replicate_api.startswith("r8_") and len(replicate_api) == 40):
                st.warning("Please enter your credentials!", icon="⚠️")
            else:
                st.success("Proceed to entering your prompt message!", icon="👉")

        # Refactored from https://github.com/a16z-infra/llama2-chatbot
        st.subheader("Models and parameters")
        selected_model = st.sidebar.selectbox(
            "Choose a Llama2 model",
            ["Llama2-7B", "Llama2-13B", "Llama2-70B"],
            key="selected_model",
        )
        if selected_model == "Llama2-7B":
            llm = "a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea"
        elif selected_model == "Llama2-13B":
            llm = "a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5"
        else:
            llm = "replicate/llama70b-v2-chat:e951f18578850b652510200860fc4ea62b3b16fac280f83ff32282f87bbd2e48"

        temperature = st.sidebar.slider(
            "temperature", min_value=0.01, max_value=5.0, value=0.1, step=0.01
        )
        top_p = st.sidebar.slider(
            "top_p", min_value=0.01, max_value=1.0, value=0.9, step=0.01
        )
        max_length = st.sidebar.slider(
            "max_length", min_value=64, max_value=4096, value=512, step=8
        )

        st.markdown(
            "📖 Learn how to build this app in this [blog](https://blog.streamlit.io/how-to-build-a-llama-2-chatbot/)!"
        )
    os.environ["REPLICATE_API_TOKEN"] = replicate_api

    # Store LLM generated responses
    if "messages" not in st.session_state.keys():
        st.session_state.messages = [
            {"role": "assistant", "content": "How may I assist you today?"}
        ]

    # Display or clear chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    def clear_chat_history():
        st.session_state.messages = [
            {"role": "assistant", "content": "How may I assist you today?"}
        ]

    st.sidebar.button("Clear Chat History", on_click=clear_chat_history)


# Function for generating LLaMA2 response
def generate_llama2_response(prompt_input):
    string_dialogue = "You are a helpful assistant. You do not respond as 'User' or pretend to be 'User'. You only respond once as 'Assistant'."
    for dict_message in st.session_state.messages:
        if dict_message["role"] == "user":
            string_dialogue += "User: " + dict_message["content"] + "\n\n"
        else:
            string_dialogue += "Assistant: " + dict_message["content"] + "\n\n"
    output = replicate.run(
        llm,
        input={
            "prompt": f"{string_dialogue} {prompt_input} Assistant: ",
            "temperature": temperature,
            "top_p": top_p,
            "max_length": max_length,
            "repetition_penalty": 1,
        },
    )
    return output


# User-provided prompt
if prompt := st.chat_input(disabled=not replicate_api):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generate_llama2_response(prompt)
            placeholder = st.empty()
            full_response = ""
            for item in response:
                full_response += item
                placeholder.markdown(full_response)
            placeholder.markdown(full_response)
    message = {"role": "assistant", "content": full_response}
    st.session_state.messages.append(message)
