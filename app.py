import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from src.chatbot.base import BaseFODMAPChatbot
from src.database.query_processor import FODMAPQueryProcessor
from src.utils.constants import SYSTEM_PROMPT
from src.chatbot.ai_chatbot import AIFODMAPChatbot
class AIFODMAPChatbot(BaseFODMAPChatbot):
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, openai_api_key: str):
        super().__init__(neo4j_uri, neo4j_user, neo4j_password)
        self.client = OpenAI(api_key=openai_api_key)
        self.query_processor = FODMAPQueryProcessor(openai_api_key)

    def visualize_results(self, results: list, query_type: str):
        """Create visualizations based on query results"""
        if not results:
            st.warning("No specific data found in the knowledge graph for this query.")
            return

        if query_type == "meal_analysis":
            # Create expandable section for meal analysis
            with st.expander("🍽️ Meal Analysis", expanded=True):
                # Create two columns for safe and unsafe ingredients
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success("Safe Ingredients")
                    safe_ingredients = [r for r in results if r['status'] == 'recommended']
                    for ing in safe_ingredients:
                        st.write(f"✅ {ing['ingredient']}")
                
                with col2:
                    st.error("Ingredients to Avoid")
                    unsafe_ingredients = [r for r in results if r['status'] == 'avoid']
                    for ing in unsafe_ingredients:
                        categories = ing.get('fodmap_categories', [])
                        st.write(f"❌ {ing['ingredient']}")
                        if categories:
                            st.caption(f"Contains: {', '.join(categories)}")

        elif query_type == "ingredients":
            # Create an expandable section for ingredient information
            with st.expander("🥗 Ingredient Analysis", expanded=True):
                for result in results:
                    if result['status'] == 'avoid':
                        st.error(
                            f"❌ {result['ingredient']} should be avoided"
                            f"{' (Contains: ' + ', '.join(result['fodmap_categories']) + ')' if result['fodmap_categories'] else ''}"
                        )
                    elif result['status'] == 'recommended':
                        st.success(f"✅ {result['ingredient']} is safe to eat")
                    else:
                        st.info(f"ℹ️ {result['ingredient']} - status unknown")

        elif query_type == "food_group":
            # Create expandable section for each food group
            for result in results:
                with st.expander(f"🍽️ {result['group']}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    # Split foods by status
                    safe_foods = [f for f in result['foods'] if f['status'] == 'recommended']
                    unsafe_foods = [f for f in result['foods'] if f['status'] == 'avoid']
                    
                    with col1:
                        st.success("Safe Foods")
                        for food in safe_foods:
                            st.write(f"✅ {food['name']}")
                    
                    with col2:
                        st.error("Foods to Avoid")
                        for food in unsafe_foods:
                            st.write(f"❌ {food['name']}")
    
    
    
        
    def get_relevant_context(self, user_query: str) -> tuple[str, dict]:
        queries, metadata = self.query_processor.process_query(user_query)
        
        context_parts = []
        all_results = {}
        
        for query_info in queries:
            results = self.query_graph(query_info["query"], query_info["params"])
            
            if metadata["query_type"] == "meal":
                for analysis in metadata.get("meal_analyses", []):
                    context_parts.append(f"\nAnalysis for {analysis['dish_name']}:")
                    
                    fodmap_concerns = []
                    for result in results:
                        status = result["status"]
                        if status == "avoid":
                            fodmap_concerns.append(
                                f"- {result['ingredient']} should be avoided "
                                f"(contains {', '.join(result['fodmap_categories'])})"
                            )
                        elif status == "recommended":
                            context_parts.append(f"- {result['ingredient']} is safe to eat")
                    
                    if fodmap_concerns:
                        context_parts.append("FODMAP concerns:")
                        context_parts.extend(fodmap_concerns)
                    
                    all_results[f"meal_{analysis['dish_name']}"] = (results, "meal_analysis")
            
            else:
                for result in results:
                    if "ingredient" in result:
                        context_parts.append(
                            f"{result['ingredient']} ({result['status']}) "
                            f"{'contains ' + ', '.join(result['fodmap_categories']) if result['fodmap_categories'] else ''}"
                        )
                    elif "group" in result:
                        foods = [f"{food['name']} ({food['status']})" for food in result['foods']]
                        context_parts.append(f"{result['group']}: {', '.join(foods[:5])}")
                
                all_results[metadata["query_type"]] = (results, metadata["query_type"])
        
        return "\n".join(context_parts), all_results

    def generate_response(self, user_query: str) -> str:
        with st.spinner("🔍 Retrieving information from knowledge graph..."):
            context, all_results = self.get_relevant_context(user_query)
        
        if not context:
            context = "No specific information found in the FODMAP database."
        
        # Display context visualization
        st.write("📊 Retrieved Information:")
        for results, query_type in all_results.values():
            self.visualize_results(results, query_type)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Context from FODMAP database:\n{context}"},
            {"role": "user", "content": user_query}
        ]
        
        try:
            with st.spinner("🤖 Generating response..."):
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try again."

def main():
    st.set_page_config(
        page_title="Yapay Zeka FODMAP Asistanı",
        page_icon="🤖",
        layout="wide"
    )

    # Custom CSS
    st.markdown("""
        <style>
        .main-container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .user-message {
            background-color: #e3f2fd;
            margin-left: 20%;
        }
        .bot-message {
            background-color: #f5f5f5;
            margin-right: 20%;
        }
        .info-box {
            background-color: #fff3e0;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        .stButton > button {
            background-color: #1976d2;
            color: white;
            border-radius: 20px;
            padding: 0.5rem 2rem;
            border: none;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: #1565c0;
            transform: translateY(-2px);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🤖 AI-Powered FODMAP Diet Assistant")
    st.markdown("""
    Get personalized guidance on the Low FODMAP diet using advanced AI.
    Ask questions in natural language and get detailed, context-aware responses.
    """)

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Load environment variables
    load_dotenv()

    # Initialize chatbot
    chatbot = AIFODMAPChatbot(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Sidebar with example queries
    with st.sidebar:
        st.markdown("### Example Questions")
        st.info("""
        Try asking:
        - Can you explain what FODMAPs are?
        - What foods should I avoid if I have IBS?
        - I love Italian food - what can I still eat?
        - Can you suggest breakfast ideas?
        - Why do onions and garlic cause problems?
        """)
        
        st.markdown("### About FODMAP Diet")
        st.info("""
        The low FODMAP diet is a temporary elimination diet that helps identify 
        trigger foods for people with IBS and other digestive disorders.
        """)

    # Chat interface
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.text_input(
            "Ask about FODMAP diet:",
            placeholder="e.g., Can you explain which fruits are safe to eat?"
        )
    with col2:
        send_button = st.button("Send")

    if send_button or user_input:
        if user_input:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get chatbot response
            response = chatbot.generate_response(user_input)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(
                f'<div class="chat-message user-message">👤 You: {message["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-message bot-message">🤖 Assistant: {message["content"]}</div>',
                unsafe_allow_html=True
            )

    chatbot.close()
if __name__ == "__main__":
    main()
