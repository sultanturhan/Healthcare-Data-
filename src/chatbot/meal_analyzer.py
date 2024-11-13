from typing import Dict, List
import json
from openai import OpenAI
from ..utils.constants import MEAL_ANALYSIS_PROMPT

class MealAnalyzer:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)

    def analyze_meal(self, meal_name: str) -> Dict:
        """Break down a meal into its base ingredients"""
        messages = [
            {"role": "system", "content": MEAL_ANALYSIS_PROMPT},
            {"role": "user", "content": f'List all main ingredients in this dish: "{meal_name}"'}
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
                "error": str(e),
                "dish_name": meal_name,
                "ingredients": []
            }

    def generate_ingredient_queries(self, ingredients: List[Dict]) -> Dict:
        """Generate Cypher query for checking ingredients"""
        ingredient_names = [ing["name"] for ing in ingredients]
        
        return {
            "query": """
            MATCH (f:Food)
            WHERE toLower(f.name) IN $ingredients
            OPTIONAL MATCH (f)-[:BELONGS_TO]->(fg:FoodGroup)
            OPTIONAL MATCH (f)-[:CONTAINS_FODMAP]->(fc:FODMAPCategory)
            OPTIONAL MATCH (f)-[:SHOULD_AVOID]->()
            OPTIONAL MATCH (f)-[:IS_RECOMMENDED]->()
            RETURN f.name as ingredient,
                   fg.name as food_group,
                   collect(DISTINCT fc.name) as fodmap_categories,
                   CASE WHEN (f)-[:SHOULD_AVOID]->() THEN 'avoid'
                        WHEN (f)-[:IS_RECOMMENDED]->() THEN 'recommended'
                        ELSE 'unknown' END as status
            """,
            "params": {
                "ingredients": [ing.lower() for ing in ingredient_names]
            }
        }
