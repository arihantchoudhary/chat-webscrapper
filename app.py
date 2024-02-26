import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage  # Chat interface components
from langchain_community.document_loaders import WebBaseLoader  # For loading web page content
from langchain.text_splitter import RecursiveCharacterTextSplitter  # For dividing text into manageable pieces
from langchain_community.vectorstores import Chroma  # Vector storage mechanism
from langchain_openai import OpenAIEmbeddings, ChatOpenAI  # OpenAI models and embeddings
from dotenv import load_dotenv  # For loading environment variables
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # Prompt templates for chat
from langchain.chains import create_history_aware_retriever, create_retrieval_chain  # Chains for retrieval logic
from langchain.chains.combine_documents import create_stuff_documents_chain  # Document combination logic

load_dotenv()  # Load environment variables

# Define your OpenAI API key here
api_key = ''

def extract_text_vectors_from_url(web_url): 
    # Extract and process the web page content
    content_loader = WebBaseLoader(web_url)
    loaded_document = content_loader.load()
    
    # Break down the loaded document into smaller chunks
    splitter = RecursiveCharacterTextSplitter()
    chunks_of_document = splitter.split_documents(loaded_document)
    
    # Generate a vector store from the document segments
    vector_storage = Chroma.from_documents(chunks_of_document, OpenAIEmbeddings(api_key=api_key))

    return vector_storage

def build_retrieval_chain_with_context(vector_storage):
    language_model = ChatOpenAI(api_key=api_key)  # Set up the language model
    
    # Set up the mechanism to retrieve relevant text fragments based on queries
    text_retriever = vector_storage.as_retriever()
    
    # Set up chat prompts for interaction
    interaction_prompt = ChatPromptTemplate.from_messages([
      MessagesPlaceholder(variable_name="conversation_history"),
      ("user", "{input}"),
      ("user", "Based on our discussion, what information should we look up?")
    ])
    
    # Chain together retrieval logic with chat history
    context_aware_chain = create_history_aware_retriever(language_model, text_retriever, interaction_prompt)
    
    return context_aware_chain
    
# Function to integrate conversational logic
def integrate_conversation_logic(context_chain): 
    language_model = ChatOpenAI(api_key=api_key)
    
    # Setup prompt for conversation based on provided context
    document_combination_prompt = ChatPromptTemplate.from_messages([
      ("system", "Respond to the query using the following context:\n\n{context}"),
      MessagesPlaceholder(variable_name="conversation_history"),
      ("user", "{input}"),
    ])
    
    documents_combination_chain = create_stuff_documents_chain(language_model, document_combination_prompt)
    
    return create_retrieval_chain(context_chain, documents_combination_chain)

def fetch_chat_response(input_text):
    context_chain = build_retrieval_chain_with_context(st.session_state.vector_storage)
    chat_integration_chain = integrate_conversation_logic(context_chain)
    chat_response = chat_integration_chain.invoke({
        "conversation_history": st.session_state.conversation_history,
        "input": input_text
    })
    
    return chat_response['answer']

# Setup Streamlit app configuration
st.set_page_config(page_title="LLM-Web Scrapper AI!", page_icon="🌐")
st.title("Webscrapper 🌐 AI")

# Configure sidebar for settings
with st.sidebar:
    st.header("Configuration")
    input_web_url = st.text_input("Enter the URL of the website")

if not input_web_url:
    st.info("Please provide the URL of a website to start.")
else:
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = [AIMessage(content="Hi! How can I assist you today?")]
    if "vector_storage" not in st.session_state:
        st.session_state.vector_storage = extract_text_vectors_from_url(input_web_url)    

    chat_input = st.chat_input("What would you like to know?")
    if chat_input:
        chat_answer = fetch_chat_response(chat_input)
        st.session_state.conversation_history.extend([HumanMessage(content=chat_input), AIMessage(content=chat_answer)])

    for msg in st.session_state.conversation_history:
        if isinstance(msg, AIMessage):
            with st.chat_message("Bot"):
                st.write(msg.content)
        else:
            with st.chat_message("You"):
                st.write(msg.content)
                
#streamlit run app.py