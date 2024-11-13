from openai import OpenAI
import json
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

class FODMAPParser:
    def __init__(self, openai_api_key: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def parse_fodmap_data(self, file_path: str) -> dict:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        system_message = """You are a precise parser that converts FODMAP diet information into structured JSON data. 
        Pay special attention to clearly identifying which foods should be avoided and which are recommended."""

        user_message = f"""Parse the following FODMAP diet information into a structured JSON object.
        For each food, explicitly specify both whether it should be avoided AND whether it is recommended.
        Some foods might be neither recommended nor avoided (neutral).

        The JSON should have the following structure:
        1. A diet_type object with name and description
        2. A standard_food_groups array with objects containing:
           - name (one of: "Fruits", "Vegetables", "Grains", "Dairy", "Proteins", "Nuts and Seeds", "Beverages", "Condiments", "Sweeteners")
           - foods array with objects containing:
             * name (string)
             * should_avoid (boolean)
             * is_recommended (boolean)
             * fodmap_level ("high", "low", or "moderate")
             * serving_info (optional string)
             * alternative_names (optional array of strings)
        3. A fodmap_categories array with objects containing:
           - name (e.g., "Fructans", "Lactose", "Polyols", etc.)
           - description (string)
           - foods array with objects containing:
             * name (string)
             * amount (optional string)

        Rules for should_avoid and is_recommended:
        - If a food is explicitly listed as safe/allowed, set is_recommended=true and should_avoid=false
        - If a food is explicitly listed as unsafe/to avoid, set should_avoid=true and is_recommended=false
        - If the status is unclear, set both to false

        Here's the content to parse:

        {content}

        Return only the JSON object, no additional text or explanations."""

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            print("Error in GPT-4 response:", response.choices[0].message.content)
            raise Exception(f"Failed to parse GPT-4 response as JSON: {e}")

    def create_knowledge_graph(self, data: dict):
        with self.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")

            # Create diet type node
            session.run("""
                CREATE (d:DietType {name: $name, description: $description})
            """, data["diet_type"])

            # Create FODMAP category nodes and relationships
            for category in data["fodmap_categories"]:
                session.run("""
                    MATCH (d:DietType {name: $diet_name})
                    CREATE (fc:FODMAPCategory {name: $cat_name, description: $cat_desc})
                    CREATE (fc)-[:PART_OF]->(d)
                """, {
                    "diet_name": data["diet_type"]["name"],
                    "cat_name": category["name"],
                    "cat_desc": category["description"]
                })

                # Create relationships between FODMAP categories and foods
                for food in category["foods"]:
                    session.run("""
                        MATCH (fc:FODMAPCategory {name: $cat_name})
                        MERGE (f:Food {name: $food_name})
                        CREATE (f)-[:CONTAINS_FODMAP {amount: $amount}]->(fc)
                    """, {
                        "cat_name": category["name"],
                        "food_name": food["name"],
                        "amount": food.get("amount", "unknown")
                    })

            # Create standard food groups and foods
            for group in data["standard_food_groups"]:
                session.run("""
                    MATCH (d:DietType {name: $diet_name})
                    CREATE (fg:FoodGroup {name: $group_name})
                    CREATE (fg)-[:PART_OF]->(d)
                """, {
                    "diet_name": data["diet_type"]["name"],
                    "group_name": group["name"]
                })

                for food in group["foods"]:
                    # Create food node with properties
                    properties = {
                        "name": food["name"],
                        "fodmap_level": food["fodmap_level"]
                    }
                    if "serving_info" in food:
                        properties["serving_info"] = food["serving_info"]
                    if "alternative_names" in food:
                        properties["alternative_names"] = food["alternative_names"]

                    # Create food node and its relationships
                    session.run("""
                        MATCH (fg:FoodGroup {name: $group_name})
                        MATCH (d:DietType {name: $diet_name})
                        MERGE (f:Food {name: $food_name})
                        SET f += $properties
                        MERGE (f)-[:BELONGS_TO]->(fg)
                        WITH f, d
                        // Create SHOULD_AVOID relationship if true
                        FOREACH(_ IN CASE WHEN $should_avoid = true THEN [1] ELSE [] END |
                            MERGE (f)-[:SHOULD_AVOID]->(d)
                        )
                        // Create IS_RECOMMENDED relationship if true
                        FOREACH(_ IN CASE WHEN $is_recommended = true THEN [1] ELSE [] END |
                            MERGE (f)-[:IS_RECOMMENDED]->(d)
                        )
                    """, {
                        "group_name": group["name"],
                        "food_name": food["name"],
                        "properties": properties,
                        "diet_name": data["diet_type"]["name"],
                        "should_avoid": food["should_avoid"],
                        "is_recommended": food["is_recommended"]
                    })

                    # Create alternative name nodes if they exist
                    if "alternative_names" in food:
                        for alt_name in food["alternative_names"]:
                            session.run("""
                                MATCH (f:Food {name: $food_name})
                                CREATE (a:AlternativeName {name: $alt_name})
                                CREATE (a)-[:REFERS_TO]->(f)
                            """, {
                                "food_name": food["name"],
                                "alt_name": alt_name
                            })

    def add_useful_indexes(self):
        with self.driver.session() as session:
            session.run("CREATE INDEX food_name IF NOT EXISTS FOR (f:Food) ON (f.name)")
            session.run("CREATE INDEX food_group_name IF NOT EXISTS FOR (fg:FoodGroup) ON (fg.name)")
            session.run("CREATE INDEX fodmap_category_name IF NOT EXISTS FOR (fc:FODMAPCategory) ON (fc.name)")
            session.run("CREATE INDEX alternative_name IF NOT EXISTS FOR (a:AlternativeName) ON (a.name)")

    def verify_relationships(self):
        """Verify and print statistics about the created relationships"""
        with self.driver.session() as session:
            stats = session.run("""
                MATCH (f:Food)
                RETURN 
                    count(f) as total_foods,
                    count((f)-[:SHOULD_AVOID]->()) as foods_to_avoid,
                    count((f)-[:IS_RECOMMENDED]->()) as recommended_foods,
                    count((f)-[:BELONGS_TO]->()) as categorized_foods
            """).single()
            
            print("\nKnowledge Graph Statistics:")
            print(f"Total foods: {stats['total_foods']}")
            print(f"Foods to avoid: {stats['foods_to_avoid']}")
            print(f"Recommended foods: {stats['recommended_foods']}")
            print(f"Categorized foods: {stats['categorized_foods']}")

    def close(self):
        self.driver.close()

def main():
    load_dotenv()

    parser = FODMAPParser(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password")
    )

    try:
        print("Parsing FODMAP data...")
        data = parser.parse_fodmap_data("turkish.txt")

        with open("fodmap_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Parsed data saved to fodmap_data.json")

        print("Creating knowledge graph...")
        parser.create_knowledge_graph(data)
        
        print("Creating indexes...")
        parser.add_useful_indexes()
        
        print("Verifying relationships...")
        parser.verify_relationships()
        
        print("Knowledge graph created successfully!")

    finally:
        parser.close()

if __name__ == "__main__":
    main()