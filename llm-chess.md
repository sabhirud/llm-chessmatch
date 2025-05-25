Implement a POST endpoint get_move.

Request body:
- model (string name of an LLM)
- game_state (string FEN notation of the state of a chess board)
- move_history (list of previous moves made by white and black)

Response body:
- move (string move of what move to make next)