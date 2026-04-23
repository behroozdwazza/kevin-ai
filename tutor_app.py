import streamlit as st
from openai import OpenAI
import datetime

# --- Simple Access Control ---
def check_password():
    """Returns True if the user had the correct password."""
    if "password_correct" not in st.session_state:
        # First run, show the input
        st.text_input("Enter the Class Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.text_input("Enter the Class Access Code:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect code. Please check your syllabus.")
        return False
    else:
        # Password correct
        return True

def password_entered():
    """Checks whether a password entered by the user is correct."""
    # Replace 'Behrooz2026' with whatever code you want
    if st.session_state["password"].lower() == "itscm180" :
        st.session_state["password_correct"] = True
        del st.session_state["password"]  # don't store password
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()  # Stop execution here if not authenticated

# --- THE REST OF YOUR KEVIN CODE GOES BELOW THIS LINE ---

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Your Assistant ID
ASSISTANT_ID = "asst_AfNPz2hBNGU2PRP2zpJwDlfj"

st.set_page_config(page_title="Kevin: Socratic Python Tutor")
st.title("Kevin: Socratic Python Tutor")

# --- Sidebar for Uploads ---
st.sidebar.header("Upload Code Screenshot")
uploaded_image = st.sidebar.file_uploader(
    "Share your code or error message:", 
    type=["png", "jpg", "jpeg"]
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        # If an image was part of this turn, we could display it here
        if "image_url" in msg:
            st.image(msg["image_url"])

# Get today's date
today_date = datetime.date.today().strftime("%B %d, %Y")

# Chat input
if user_input := st.chat_input("How can I help you?"):
    # 1. Store the local message (text only for the UI history)
    current_message = {"role": "user", "text": user_input}
    
    # 2. Prepare the content for the API (can be a list for Vision)
    api_content = [{"type": "text", "text": user_input}]
    
    # 3. Handle image upload if a file is present
    if uploaded_image is not None:
        # Upload the file to OpenAI with the 'vision' purpose
        vision_file = client.files.create(
            file=uploaded_image,
            purpose="vision"
        )
        
        # Add the image reference to the API message
        api_content.append({
            "type": "image_file", 
            "image_file": {"file_id": vision_file.id}
        })
        
        # Add the image preview to our UI history
        current_message["image_url"] = uploaded_image

    st.session_state.messages.append(current_message)
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_image:
            st.image(uploaded_image)

    # 4. Send the multi-modal message to the Thread
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=api_content
    )

    # 5. Run the Assistant
    run_instructions = "Today is " + today_date + ". Use the Term Calendar for scope. If an image is provided, analyze the code or error within it Socratically."
    
    with st.spinner("Kevin is reviewing your code..."):
        run = client.beta.threads.runs.create_and_poll(
            thread_id=st.session_state.thread_id,
            assistant_id=ASSISTANT_ID,
            additional_instructions=run_instructions
        )

    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
        assistant_text = messages.data[0].content[0].text.value
        
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
        st.session_state.messages.append({"role": "assistant", "text": assistant_text})
    else:
        st.error("Kevin encountered an error: " + run.status)