# LLM Chess App

LLM Chess is an experimental app that lets thinking models play chess against each other. Currently supports:

* Claude 4 Opus
* Claude 4 Sonnet
* Gemini 2.5 Pro
* Gemini 2.5 Flash
* o4-mini
* Grok 3 Mini

## Running locally

### Backend (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, and/or XAI_API_KEY
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the FastAPI server:
   ```bash
   python main.py
   ```

The backend will be available at `http://localhost:8000`

### Frontend (React)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

The frontend will be available at `http://localhost:3000`
