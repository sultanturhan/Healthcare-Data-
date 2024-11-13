from typing import Dict, List, Tuple
import json
from openai import OpenAI
from ..chatbot.meal_analyzer import MealAnalyzer
from ..utils.constants import QUERY_CLASSIFICATION_PROMPT

class FODMAPQueryProcessor:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.meal_analyzer = MealAnalyzer(openai_api_key)

    def classify_query(self, user_query: str) -> Dict:
        messages = [
            {"role": "system", "content": QUERY_CLASSIFICATION_PROMPT},
            {"role": "user", "content": f'Classify this query: "{user_query}"'}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {
                "query_type": "ingredient",  # Default to ingredient search
                "identified_items": [user_query.lower()],
                "error": str(e)
            }

    def process_query(self, user_query: str) -> Tuple[List[Dict], Dict]:
        classification = self.classify_query(user_query)
        queries = []
        
        if classification["query_type"] == "meal":
            meal_analyses = []
            for meal in classification["identified_items"]:
                meal_analysis = self.meal_analyzer.analyze_meal(meal)
                meal_analyses.append(meal_analysis)
                
                if meal_analysis["ingredients"]:
                    queries.append({
                        "query": """
                        MATCH (f:Food)
                        WHERE toLower(f.name) IN $ingredients
                        OPTIONAL MATCH (f)-[:BELONGS_TO]->(fg:FoodGroup)
                        OPTIONAL MATCH (f)-[:CONTAINS_FODMAP]->(fc:FODMAPCategory)
                        RETURN f.name as ingredient,
                               fg.name as food_group,
                               collect(DISTINCT fc.name) as fodmap_categories,
                               CASE WHEN exists((f)-[:SHOULD_AVOID]->()) THEN 'avoid'
                                    WHEN exists((f)-[:IS_RECOMMENDED]->()) THEN 'recommended'
                                    ELSE 'unknown' END as status
                        """,
                        "params": {
                            "ingredients": [ing["name"].lower() for ing in meal_analysis["ingredients"]]
                        }
                    })
            
            classification["meal_analyses"] = meal_analyses
            
        elif classification["query_type"] == "ingredient":
            queries.append({
                "query": """
                MATCH (f:Food)
                WHERE toLower(f.name) CONTAINS $ingredient
                OPTIONAL MATCH (f)-[:BELONGS_TO]->(fg:FoodGroup)
                OPTIONAL MATCH (f)-[:CONTAINS_FODMAP]->(fc:FODMAPCategory)
                RETURN f.name as ingredient,
                       fg.name as food_group,
                       collect(DISTINCT fc.name) as fodmap_categories,
                       CASE WHEN exists((f)-[:SHOULD_AVOID]->()) THEN 'avoid'
                            WHEN exists((f)-[:IS_RECOMMENDED]->()) THEN 'recommended'
                            ELSE 'unknown' END as status
                """,
                "params": {
                    "ingredient": classification["identified_items"][0].lower()
                }
            })
            
        return queries, classification