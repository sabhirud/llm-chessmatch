# LLM Chess App

A full-stack chess application with a React frontend and FastAPI backend that uses Claude AI to generate chess moves.

## Setup Instructions

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

## API Endpoints

- `POST /get_move` - Returns a chess move from AI
  - Request body: `{"model": "claude-opus-4-20250514", "o3", "gemini-2.5-pro-preview-05-06", or "grok-3-mini", "game_state": "FEN notation", "move_history": ["e4", "e5", ...]}`
  - Response: `{"move": "Nf3"}`
- `POST /random-number` - Returns a random number between 1 and 100 (demo endpoint)

## Technologies Used

- **Frontend**: React with TypeScript
- **Backend**: FastAPI with Python
- **AI**: Anthropic Claude API, OpenAI API, Google Gemini API & X.AI Grok API
- **CORS**: Configured to allow communication between frontend and backend