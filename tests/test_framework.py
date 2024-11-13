import json
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI
import pandas as pd
from src.database.query_processor import FODMAPQueryProcessor
from src.chatbot.base import BaseFODMAPChatbot
from src.chatbot.meal_analyzer import MealAnalyzer

class FODMAPTestFramework:
    def __init__(self, 
                 neo4j_uri: str,
                 neo4j_user: str,
                 neo4j_password: str,
                 openai_api_key: str,
                 test_data_path: str):
        """Initialize the test framework with necessary components"""
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.query_processor = FODMAPQueryProcessor(openai_api_key)
        self.chatbot = BaseFODMAPChatbot(neo4j_uri, neo4j_user, neo4j_password)
        self.test_data = self._load_test_data(test_data_path)
        
    def _load_test_data(self, path: str) -> List[Dict[str, Any]]:
        """Load test cases from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data["test_cases"]  # Return the list of test cases
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for a text"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return np.array(response.data[0].embedding)
    
    def _compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def evaluate_query_understanding(self, test_case: Dict) -> float:
        """Evaluate query classification accuracy"""
        expected_type = test_case["expected_classification"]
        classification = self.query_processor.classify_query(test_case["query"])
        return 1.0 if classification["query_type"] == expected_type else 0.0
    
    def evaluate_knowledge_retrieval(self, test_case: Dict) -> float:
        """Evaluate knowledge retrieval precision"""
        queries, _ = self.query_processor.process_query(test_case["query"])
        
        retrieved_nodes = set()
        for query_info in queries:
            results = self.chatbot.query_graph(query_info["query"], query_info["params"])
            for result in results:
                if "ingredient" in result:
                    retrieved_nodes.add(result["ingredient"].lower())
                elif "food_group" in result:
                    retrieved_nodes.add(result["food_group"].lower())
        
        expected_nodes = set(node.lower() for node in test_case["expected_nodes"])
        
        if not retrieved_nodes:
            return 0.0
            
        return len(retrieved_nodes.intersection(expected_nodes)) / len(retrieved_nodes)
    
    def evaluate_response_relevance(self, response: str, test_case: Dict) -> float:
        """Evaluate response relevance using embedding similarity"""
        response_embedding = self._get_embedding(response)
        query_embedding = self._get_embedding(test_case["query"])
        expected_embedding = self._get_embedding(test_case["expected_response"])
        
        query_similarity = self._compute_cosine_similarity(response_embedding, query_embedding)
        expected_similarity = self._compute_cosine_similarity(response_embedding, expected_embedding)
        
        return (query_similarity + expected_similarity) / 2
    
    def run_tests(self) -> pd.DataFrame:
        """Run all tests and compile results"""
        results = []
        
        for test_case in self.test_data:
            try:
                # Process query
                queries, metadata = self.query_processor.process_query(test_case["query"])
                
                # Calculate metrics
                query_understanding = self.evaluate_query_understanding(test_case)
                knowledge_retrieval = self.evaluate_knowledge_retrieval(test_case)
                
                # Get response for relevance evaluation
                response = test_case.get("actual_response", "")
                response_relevance = self.evaluate_response_relevance(response, test_case)
                
                results.append({
                    "query": test_case["query"],
                    "query_understanding": query_understanding,
                    "knowledge_retrieval": knowledge_retrieval,
                    "response_relevance": response_relevance,
                    "expected_type": test_case["expected_classification"],
                    "actual_type": metadata["query_type"]
                })
                
            except Exception as e:
                print(f"Error processing test case: {test_case.get('query', 'Unknown')}")
                print(f"Error details: {str(e)}")
                
        return pd.DataFrame(results)
    
    def generate_report(self, results_df: pd.DataFrame) -> Dict[str, float]:
        """Generate aggregate metrics report"""
        return {
            "average_query_understanding": results_df["query_understanding"].mean(),
            "average_knowledge_retrieval": results_df["knowledge_retrieval"].mean(),
            "average_response_relevance": results_df["response_relevance"].mean(),
            "overall_performance": results_df[["query_understanding", 
                                            "knowledge_retrieval", 
                                            "response_relevance"]].mean().mean()
        }

def main():
    """Main function to run tests"""
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Initialize test framework
    framework = FODMAPTestFramework(
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USER"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        test_data_path="tests/test_cases.json"
    )
    
    # Run tests
    results_df = framework.run_tests()
    
    # Generate and print report
    report = framework.generate_report(results_df)
    
    # Save detailed results
    results_df.to_csv("test_results.csv", index=False)
    
    # Print summary
    print("\nTest Results Summary:")
    print("-" * 50)
    for metric, value in report.items():
        print(f"{metric}: {value:.3f}")

if __name__ == "__main__":
    main()
