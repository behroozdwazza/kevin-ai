import streamlit as st
from openai import OpenAI
import datetime

# Get today's date
today_date = datetime.date.today().strftime("%B %d, %Y")

# --- Simple Access Control ---
def check_password():
    """Returns True if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.text_input("Enter the Class Access Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter the Class Access Code:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect code. Please check your syllabus.")
        return False
    else:
        return True

def password_entered():
    """Checks whether a password entered by the user is correct."""
    if st.session_state["password"].lower() == "itscm180":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()

# --- INITIALIZATION ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
ASSISTANT_ID = "asst_AfNPz2hBNGU2PRP2zpJwDlfj"

# 1. Initialize uploader_key and other session states
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

st.set_page_config(page_title="Kevin AI: The ITSCM180 Smart Tutor")
st.image("uww-logo.png", width=800)

# --- SIDEBAR ---
st.sidebar.header("Upload Code Screenshot")

# 2. Add the dynamic key here
uploaded_image = st.sidebar.file_uploader(
    "Share your code or error message:", 
    type=["png", "jpg", "jpeg"],
    key="uploader_" + str(st.session_state.uploader_key)
)

# Sidebar for Extra Credit
st.sidebar.markdown("---")
st.sidebar.subheader("Download and Submit your Chat Log for Extra Credit")

student_name = st.sidebar.text_input("Enter your Full Name:", placeholder="e.g., Jane Doe")

if st.session_state.messages:
    if student_name:
        chat_log = "STUDENT NAME: " + student_name + "\n"
        chat_log += "DATE: " + today_date + "\n"
        chat_log += "COURSE: ITSCM 180 / Intro to Programming for Business Applications\n"
        chat_log += "INSTRUCTOR: Behrooz\n"
        chat_log += "VERIFICATION ID: " + st.session_state.thread_id + "\n"
        chat_log += "-------------------------------------------\n\n"
        
        for msg in st.session_state.messages:
            entry = msg["role"].upper() + ": " + msg["text"] + "\n\n"
            chat_log += entry
            
        st.sidebar.download_button(
            label="Download Chat Log",
            data=chat_log,
            file_name=student_name.replace(" ", "_") + "_tutor_log.txt",
            mime="text/plain",
            help="Click here to save your log for Canvas submission."
        )
    else:
        st.sidebar.warning("Please enter your name above to enable the download button.")
else:
    st.sidebar.info("Start a conversation with Kevin to enable the log download.")
    
# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if "image_url" in msg:
            st.image(msg["image_url"])

# --- CHAT INPUT & LOGIC ---
if user_input := st.chat_input("How can I help you?"):
    current_message = {"role": "user", "text": user_input}
    api_content = [{"type": "text", "text": user_input}]
    
    if uploaded_image is not None:
        vision_file = client.files.create(
            file=uploaded_image,
            purpose="vision"
        )
        api_content.append({
            "type": "image_file", 
            "image_file": {"file_id": vision_file.id}
        })
        current_message["image_url"] = uploaded_image

    st.session_state.messages.append(current_message)
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_image:
            st.image(uploaded_image)

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=api_content
    )

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
        
        # 3. RESET THE UPLOADER IF AN IMAGE WAS USED
        if uploaded_image is not None:
            st.session_state.uploader_key += 1
            st.rerun()
    else:
        st.error("Kevin encountered an error: " + run.status)
