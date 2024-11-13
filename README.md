# FODMAP Diet Assistant 🤖

An AI-powered chatbot system that provides personalized guidance on the Low FODMAP diet using natural language processing and a knowledge graph backend.

## Overview

The FODMAP Diet Assistant combines OpenAI's GPT-4, Neo4j graph database, and Streamlit to create an intelligent chat interface that helps users navigate the complexities of the Low FODMAP diet. It provides personalized recommendations, meal analysis, and ingredient information while maintaining context through a sophisticated knowledge graph.

## Features

- 🗣️ Natural language understanding of dietary queries
- 🍽️ Detailed meal and ingredient analysis
- 📊 Visual representation of FODMAP content
- 🔍 Intelligent context-aware responses
- 📝 Turkish language support
- 🎯 Evidence-based dietary recommendations
- 💡 Interactive chat interface
- 📈 Real-time data visualization

## Technical Architecture

### Components

1. **Frontend (Streamlit)**
   - Interactive chat interface
   - Real-time response visualization
   - Query input handling
   - Session state management

2. **Backend**
   - `BaseFODMAPChatbot`: Core chatbot functionality
   - `AIFODMAPChatbot`: AI-enhanced chatbot implementation
   - `FODMAPQueryProcessor`: Query classification and processing
   - `MealAnalyzer`: Meal composition analysis

3. **Database**
   - Neo4j graph database
   - FODMAP knowledge graph
   - Food relationship mapping

4. **AI Integration**
   - OpenAI GPT-4 for natural language understanding
   - Embeddings for response relevance evaluation
   - Context-aware response generation

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd fodmap-assistant
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
OPENAI_API_KEY=your_openai_api_key
```

5. Initialize the knowledge graph:
```bash
python src/database/gptgraphbuilder.py
```

## Usage

1. Start the application:
```bash
streamlit run src/app.py
```

2. Access the web interface at `http://localhost:8501`

3. Start chatting with the assistant about FODMAP-related questions

### Example Queries

- "Can you explain what FODMAPs are?"
- "Is soğan (onion) safe to eat?"
- "Can I eat karnıyarık?"
- "What can I have for breakfast?"
- "Are dairy products allowed?"

## Testing

The project includes a comprehensive testing framework for evaluating the chatbot's performance:

```bash
python src/test_framework.py
```

The testing framework evaluates:
- Query understanding accuracy
- Knowledge retrieval precision
- Response relevance
- Overall performance metrics

## Project Structure

```
fodmap-assistant/
├── src/
│   ├── app.py                 # Main Streamlit application
│   ├── chatbot/
│   │   ├── base.py           # Base chatbot implementation
│   │   ├── ai_chatbot.py     # AI-enhanced chatbot
│   │   └── meal_analyzer.py  # Meal analysis functionality
│   ├── database/
│   │   ├── query_processor.py # Query processing
│   │   └── gptgraphbuilder.py # Knowledge graph builder
│   └── utils/
│       └── constants.py       # System prompts and constants
├── tests/
│   ├── test_cases.json       # Test scenarios
│   └── test_framework.py     # Testing infrastructure
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Performance Metrics

Based on the test results:
- Query Understanding: 90%
- Knowledge Retrieval: 75%
- Response Relevance: 89%
- Overall Performance: 85%

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT-4 API
- Neo4j for graph database
- Streamlit for the web interface
- Contributors to the FODMAP diet research

## Support

For support, please open an issue in the repository or contact the development team.
