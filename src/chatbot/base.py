from typing import List, Dict, Any, Tuple
from neo4j import GraphDatabase
import streamlit as st

class BaseFODMAPChatbot:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def close(self):
        self.driver.close()

    def query_graph(self, query: str, params: dict = None) -> List[Dict[str, Any]]:
        """Execute Neo4j query and return results"""
        try:
            with self.driver.session() as session:
                # Debug logging
                st.write("Executing query:", query)
                st.write("With parameters:", params)
                
                if params is None:
                    result = session.run(query)
                else:
                    result = session.run(query, params)
                
                records = [dict(record) for record in result]
                
                # Debug logging
                st.write(f"Found {len(records)} results")
                return records
                
        except Exception as e:
            st.error(f"Database query error: {str(e)}")
            return []