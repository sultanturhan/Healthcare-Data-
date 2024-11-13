from openai import OpenAI
import streamlit as st
from ..database.query_processor import FODMAPQueryProcessor
from .base import BaseFODMAPChatbot
from ..utils.constants import SYSTEM_PROMPT

class AIFODMAPChatbot(BaseFODMAPChatbot):
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, openai_api_key: str):
        super().__init__(neo4j_uri, neo4j_user, neo4j_password)
        self.client = OpenAI(api_key=openai_api_key)
        self.query_processor = FODMAPQueryProcessor(openai_api_key)

    def visualize_results(self, results: list, query_type: str):
        """Create visualizations based on query results"""
        if not results:
            print("No specific data found in the knowledge graph for this query.")
            return

        if query_type == "meal_analysis":
            print("\nMeal Analysis:")
            safe_ingredients = [r for r in results if r['status'] == 'recommended']
            unsafe_ingredients = [r for r in results if r['status'] == 'avoid']
            
            print("\nSafe Ingredients:")
            for ing in safe_ingredients:
                print(f"✅ {ing['ingredient']}")
            
            print("\nIngredients to Avoid:")
            for ing in unsafe_ingredients:
                categories = ing.get('fodmap_categories', [])
                print(f"❌ {ing['ingredient']}")
                if categories:
                    print(f"   Contains: {', '.join(categories)}")

        elif query_type == "ingredients":
            print("\nIngredient Analysis:")
            for result in results:
                if result['status'] == 'avoid':
                    print(f"❌ {result['ingredient']} should be avoided")
                    if result['fodmap_categories']:
                        print(f"   Contains: {', '.join(result['fodmap_categories'])}")
                elif result['status'] == 'recommended':
                    print(f"✅ {result['ingredient']} is safe to eat")
                else:
                    print(f"ℹ️ {result['ingredient']} - status unknown")

        elif query_type == "food_group":
            print("\nFood Group Analysis:")
            for result in results:
                safe_foods = [f for f in result.get('foods', []) if f['status'] == 'recommended']
                unsafe_foods = [f for f in result.get('foods', []) if f['status'] == 'avoid']
                
                print(f"\n{result.get('group', 'Unknown Group')}:")
                print("\nSafe Foods:")
                for food in safe_foods:
                    print(f"✅ {food['name']}")
                
                print("\nFoods to Avoid:")
                for food in unsafe_foods:
                    print(f"❌ {food['name']}")
    
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
        print("🔍 Retrieving information from knowledge graph...")
        context, all_results = self.get_relevant_context(user_query)
        
        if not context:
            context = "No specific information found in the FODMAP database."
        
        print("📊 Retrieved Information:")
        for results, query_type in all_results.values():
            self.visualize_results(results, query_type)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Context from FODMAP database:\n{context}"},
            {"role": "user", "content": user_query}
        ]
        
        try:
            print("🤖 Generating response...")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try again."
