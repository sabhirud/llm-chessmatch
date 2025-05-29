import React, { useState, useCallback, useRef } from 'react';
import { Chess } from 'chess.js';
import ChessBoard from './ChessBoard';
import ModelSelector from './ModelSelector';
import CapturedPiecesRow from './CapturedPieces';

const MODELS = [
  'claude-opus-4-20250514',
  'claude-sonnet-4-20250514',
  'o4-mini',
  'gemini-2.5-pro-preview-05-06',
  'gemini-2.5-flash-preview-05-20',
  'grok-3-mini'
];

interface GameState {
  game: Chess;
  isGameStarted: boolean;
  isGameOver: boolean;
  currentPlayer: 'white' | 'black';
  whiteModel: string;
  blackModel: string;
  isThinking: boolean;
  gameResult: string | null;
  gameMode: 'auto' | 'manual';
  capturedPieces: {
    white: string[];
    black: string[];
  };
  moveThinkingTokens: number[];
  moveTimes: number[];
  drawOffer: {
    offered: boolean;
    offeredBy: 'white' | 'black' | null;
  };
  awaitingDrawResponse: boolean;
  thinkingOutput: string;
  isStreaming: boolean;
}

const formatTime = (milliseconds: number): string => {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  } else {
    return `${(milliseconds / 1000).toFixed(1)}s`;
  }
};

const ChessGame: React.FC = () => {
  const [gameState, setGameState] = useState<GameState>({
    game: new Chess(),
    isGameStarted: false,
    isGameOver: false,
    currentPlayer: 'white',
    whiteModel: '',
    blackModel: '',
    isThinking: false,
    gameResult: null,
    gameMode: 'manual',
    capturedPieces: {
      white: [],
      black: []
    },
    moveThinkingTokens: [],
    moveTimes: [],
    drawOffer: {
      offered: false,
      offeredBy: null
    },
    awaitingDrawResponse: false,
    thinkingOutput: '',
    isStreaming: false
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const thinkingOutputRef = useRef<string>('');
  const thinkingOutputBoxRef = useRef<HTMLDivElement>(null);

  const makeMove = useCallback(async (model: string, player: 'white' | 'black') => {
    // Prevent duplicate calls
    if (gameState.isGameOver || gameState.isThinking) {
      return;
    }

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    // Set thinking state and capture current state for API call
    const currentFen = gameState.game.fen();
    const currentHistory = gameState.game.history();
    const startTime = Date.now();
    const isAnthropicModel = model.includes('claude');
    
    console.log('Starting move for', player, 'with history:', currentHistory);
    
    // Set initial thinking state and clear previous thinking output
    setGameState(prev => ({ 
      ...prev, 
      isThinking: true,
      thinkingOutput: '',
      isStreaming: isAnthropicModel
    }));
    
    // Reset thinking output ref
    thinkingOutputRef.current = '';
    
    // Set up periodic updates for thinking output
    let updateInterval: NodeJS.Timeout | null = null;
    if (isAnthropicModel) {
      updateInterval = setInterval(() => {
        setGameState(prev => ({
          ...prev,
          thinkingOutput: thinkingOutputRef.current
        }));
      }, 50); // Update UI every 50ms
    }

    // Make API call
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_API_BASE_URL || 'http://localhost:8000';
      
      // Use streaming endpoint
      const response = await fetch(`${backendUrl}/get_move_stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: model,
          game_state: currentFen,
          move_history: currentHistory
        }),
        signal: abortControllerRef.current?.signal
      });

      if (response.ok && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines[lines.length - 1];
            
            for (let i = 0; i < lines.length - 1; i++) {
              const line = lines[i].trim();
              if (line.startsWith('data: ')) {
                const dataStr = line.substring(6);
                if (dataStr === '[DONE]') continue;
                
                try {
                  const event = JSON.parse(dataStr);
                  
                  if (event.type === 'thinking_delta') {
                    thinkingOutputRef.current += event.content;
                  } else if (event.type === 'thinking_end') {
                    // Thinking is done - ensure final update
                    setGameState(prev => ({
                      ...prev,
                      thinkingOutput: thinkingOutputRef.current
                    }));
                  } else if (event.type === 'result') {
                    // Clear the update interval
                    if (updateInterval) {
                      clearInterval(updateInterval);
                    }
                    
                    const endTime = Date.now();
                    const moveTime = endTime - startTime;
                    const data = event.data;
                        
                    setGameState(prevState => {
                      // Double-check we're still in the right state
                      if (prevState.isGameOver || !prevState.isThinking) {
                        return prevState;
                      }

                      // Handle special actions
                      if (data.action === 'resign') {
                        const winner = player === 'white' ? 'Black' : 'White';
                        return {
                          ...prevState,
                          isGameOver: true,
                          gameResult: `${player === 'white' ? 'White' : 'Black'} resigned. ${winner} wins!`,
                          isThinking: false,
                          isStreaming: false,
                          moveThinkingTokens: [...prevState.moveThinkingTokens, data.thinking_tokens || 0],
                          moveTimes: [...prevState.moveTimes, moveTime]
                        };
                      }

                      if (data.action === 'draw_offer') {
                        return {
                          ...prevState,
                          drawOffer: {
                            offered: true,
                            offeredBy: player
                          },
                          awaitingDrawResponse: true,
                          isThinking: false,
                          isStreaming: false,
                          moveThinkingTokens: [...prevState.moveThinkingTokens, data.thinking_tokens || 0],
                          moveTimes: [...prevState.moveTimes, moveTime]
                        };
                      }

                      // Handle regular moves
                      if (data.move) {
                        // Create new game and replay history to preserve move history
                        const newGame = new Chess();
                        const history = prevState.game.history();
                        
                        // Replay all moves to preserve history
                        for (const move of history) {
                          newGame.move(move);
                        }
                        
                        console.log('Before move - History:', prevState.game.history());
                        console.log('Making move:', data.move);
                        
                        try {
                          const move = newGame.move(data.move);
                          
                          if (move) {
                            console.log('After move - History:', newGame.history());
                            
                            const isGameOver = newGame.isGameOver();
                            let gameResult = null;
                            
                            if (isGameOver) {
                              if (newGame.isCheckmate()) {
                                gameResult = `${player === 'white' ? 'White' : 'Black'} wins by checkmate!`;
                              } else if (newGame.isDraw()) {
                                gameResult = 'Game ends in a draw!';
                              }
                            }

                            // Update captured pieces if a piece was captured
                            let updatedCapturedPieces = { ...prevState.capturedPieces };
                            if (move.captured) {
                              const capturedBy = player === 'white' ? 'white' : 'black';
                              updatedCapturedPieces[capturedBy] = [...updatedCapturedPieces[capturedBy], move.captured];
                            }

                            // Update thinking tokens and move times
                            const updatedThinkingTokens = [...prevState.moveThinkingTokens, data.thinking_tokens || 0];
                            const updatedMoveTimes = [...prevState.moveTimes, moveTime];

                            return {
                              ...prevState,
                              game: newGame,
                              currentPlayer: prevState.currentPlayer === 'white' ? 'black' : 'white',
                              isGameOver,
                              gameResult,
                              isThinking: false,
                              isStreaming: false,
                              capturedPieces: updatedCapturedPieces,
                              moveThinkingTokens: updatedThinkingTokens,
                              moveTimes: updatedMoveTimes
                            };
                          } else {
                            console.error('Invalid move returned:', data.move);
                            return { ...prevState, isThinking: false, isStreaming: false };
                          }
                        } catch (moveError) {
                          console.error('Error making move:', data.move, moveError);
                          return { ...prevState, isThinking: false, isStreaming: false };
                        }
                      }

                      return { ...prevState, isThinking: false, isStreaming: false };
                    });
                  }
                } catch (e) {
                  console.error('Error parsing SSE event:', e);
                }
              }
            }
          }
        } catch (e) {
          console.error('Error reading stream:', e);
        }
      }
    } catch (error) {
      // Clear the update interval
      if (updateInterval) {
        clearInterval(updateInterval);
      }
      
      // Don't update state if the request was aborted
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Move request was cancelled');
        return;
      }
      console.error('Error making move:', error);
      setGameState(prevState => ({ ...prevState, isThinking: false, isStreaming: false }));
    }
  }, [gameState.isGameOver, gameState.isThinking, gameState.game]);

  const handleDrawResponse = useCallback(async (model: string, player: 'white' | 'black') => {
    setGameState(prev => {
      // Prevent duplicate calls
      if (prev.isGameOver || prev.isThinking || !prev.awaitingDrawResponse) {
        return prev;
      }

      // Cancel any existing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new AbortController for this request
      abortControllerRef.current = new AbortController();

      // Set thinking state and capture current state for API call
      const currentFen = prev.game.fen();
      const currentHistory = prev.game.history();
      const startTime = Date.now();
      
      console.log('Getting draw response for', player, 'with history:', currentHistory);

      // Make API call
      (async () => {
        try {
          const backendUrl = process.env.REACT_APP_BACKEND_API_BASE_URL || 'http://localhost:8000';
          const response = await fetch(`${backendUrl}/draw_response`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              model: model,
              game_state: currentFen,
              move_history: currentHistory
            }),
            signal: abortControllerRef.current?.signal
          });

          if (response.ok) {
            const data = await response.json();
            const endTime = Date.now();
            const moveTime = endTime - startTime;
            
            setGameState(prevState => {
              // Double-check we're still in the right state
              if (prevState.isGameOver || !prevState.isThinking || !prevState.awaitingDrawResponse) {
                return prevState;
              }

              // Update thinking tokens and move times
              const updatedThinkingTokens = [...prevState.moveThinkingTokens, data.thinking_tokens || 0];
              const updatedMoveTimes = [...prevState.moveTimes, moveTime];

              if (data.action === 'draw_accept') {
                return {
                  ...prevState,
                  isGameOver: true,
                  gameResult: 'Game ends in a draw by agreement!',
                  isThinking: false,
                  drawOffer: {
                    offered: false,
                    offeredBy: null
                  },
                  awaitingDrawResponse: false,
                  moveThinkingTokens: updatedThinkingTokens,
                  moveTimes: updatedMoveTimes
                };
              } else {
                // Draw declined, continue game
                return {
                  ...prevState,
                  isThinking: false,
                  drawOffer: {
                    offered: false,
                    offeredBy: null
                  },
                  awaitingDrawResponse: false,
                  moveThinkingTokens: updatedThinkingTokens,
                  moveTimes: updatedMoveTimes
                };
              }
            });
          }
        } catch (error) {
          // Don't update state if the request was aborted
          if (error instanceof Error && error.name === 'AbortError') {
            console.log('Draw response request was cancelled');
            return;
          }
          console.error('Error getting draw response:', error);
          setGameState(prevState => ({ 
            ...prevState, 
            isThinking: false,
            drawOffer: {
              offered: false,
              offeredBy: null
            },
            awaitingDrawResponse: false
          }));
        }
      })();

      return { ...prev, isThinking: true };
    });
  }, []);

  const startGame = useCallback(() => {
    if (!gameState.whiteModel || !gameState.blackModel) {
      alert('Please select models for both white and black.');
      return;
    }

    setGameState(prev => ({
      ...prev,
      isGameStarted: true,
      game: new Chess(),
      moveThinkingTokens: [],
      moveTimes: [],
      drawOffer: {
        offered: false,
        offeredBy: null
      },
      awaitingDrawResponse: false,
      thinkingOutput: '',
      isStreaming: false
    }));
  }, [gameState.whiteModel, gameState.blackModel]);

  // Auto-scroll thinking output
  React.useEffect(() => {
    if (thinkingOutputBoxRef.current && gameState.isStreaming) {
      thinkingOutputBoxRef.current.scrollTop = thinkingOutputBoxRef.current.scrollHeight;
    }
  }, [gameState.thinkingOutput, gameState.isStreaming]);

  // Auto-play when it's the next player's turn (only in auto mode)
  React.useEffect(() => {
    if (gameState.gameMode === 'auto' && gameState.isGameStarted && !gameState.isGameOver && !gameState.isThinking) {
      const currentModel = gameState.currentPlayer === 'white' ? gameState.whiteModel : gameState.blackModel;
      if (currentModel) {
        // If awaiting draw response, handle that instead of making a move
        if (gameState.awaitingDrawResponse) {
          const timer = setTimeout(() => {
            handleDrawResponse(currentModel, gameState.currentPlayer);
          }, 1000);
          return () => clearTimeout(timer);
        } else {
          const timer = setTimeout(() => {
            makeMove(currentModel, gameState.currentPlayer);
          }, 1000);
          return () => clearTimeout(timer);
        }
      }
    }
  }, [gameState.gameMode, gameState.currentPlayer, gameState.isGameStarted, gameState.isGameOver, gameState.isThinking, gameState.awaitingDrawResponse, gameState.whiteModel, gameState.blackModel, makeMove, handleDrawResponse]);

  const resetGame = () => {
    // Cancel any in-flight requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setGameState({
      game: new Chess(),
      isGameStarted: false,
      isGameOver: false,
      currentPlayer: 'white',
      whiteModel: gameState.whiteModel,
      blackModel: gameState.blackModel,
      isThinking: false,
      gameResult: null,
      gameMode: 'manual',
      capturedPieces: {
        white: [],
        black: []
      },
      moveThinkingTokens: [],
      moveTimes: [],
      drawOffer: {
        offered: false,
        offeredBy: null
      },
      awaitingDrawResponse: false,
      thinkingOutput: '',
      isStreaming: false
    });
  };

  const pickRandomModels = () => {
    // Create a copy of the models array and shuffle it
    const shuffledModels = [...MODELS].sort(() => Math.random() - 0.5);
    
    // Pick the first two models (guaranteed to be different)
    const [whiteModel, blackModel] = shuffledModels;
    
    setGameState(prev => ({
      ...prev,
      whiteModel,
      blackModel
    }));
  };

  const nextMove = () => {
    if (gameState.gameMode === 'manual' && gameState.isGameStarted && !gameState.isGameOver && !gameState.isThinking) {
      const currentModel = gameState.currentPlayer === 'white' ? gameState.whiteModel : gameState.blackModel;
      if (currentModel) {
        // If awaiting draw response, handle that instead of making a move
        if (gameState.awaitingDrawResponse) {
          handleDrawResponse(currentModel, gameState.currentPlayer);
        } else {
          makeMove(currentModel, gameState.currentPlayer);
        }
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
      {!gameState.isGameStarted && (
        <p style={{ fontSize: '18px', color: '#666', textAlign: 'center', margin: '0 0 10px 0' }}>
          Select models and click "Start Game" to begin
        </p>
      )}
      <div style={{ display: 'flex', gap: '40px', alignItems: 'center' }}>
        <ModelSelector
          label="White"
          models={MODELS}
          selectedModel={gameState.whiteModel}
          onModelChange={(model) => setGameState(prev => ({ ...prev, whiteModel: model }))}
          disabled={gameState.isGameStarted}
        />
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
          {!gameState.isGameStarted && (
            <button
              onClick={pickRandomModels}
              style={{
                padding: '8px 16px',
                fontSize: '14px',
                backgroundColor: '#333',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer',
                marginBottom: '5px'
              }}
            >
              Pick Random Models
            </button>
          )}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <label style={{ fontSize: '14px', color: '#666' }}>Mode:</label>
            <select
              value={gameState.gameMode}
              onChange={(e) => setGameState(prev => ({ ...prev, gameMode: e.target.value as 'auto' | 'manual' }))}
              disabled={gameState.isGameStarted}
              style={{
                padding: '5px 10px',
                fontSize: '14px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                backgroundColor: gameState.isGameStarted ? '#f5f5f5' : 'white'
              }}
            >
              <option value="auto">Auto</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          
          {!gameState.isGameStarted ? (
            <button
              onClick={startGame}
              style={{
                padding: '10px 20px',
                fontSize: '16px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
            >
              Start Game
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '10px' }}>
              {gameState.gameMode === 'manual' && (
                <button
                  onClick={nextMove}
                  disabled={gameState.isGameOver || gameState.isThinking}
                  style={{
                    padding: '10px 15px',
                    fontSize: '14px',
                    backgroundColor: gameState.isGameOver || gameState.isThinking ? '#ccc' : '#333',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: gameState.isGameOver || gameState.isThinking ? 'not-allowed' : 'pointer'
                  }}
                >
                  {gameState.awaitingDrawResponse ? 'Respond to Draw' : 'Next Move'}
                </button>
              )}
              <button
                onClick={resetGame}
                style={{
                  padding: '10px 20px',
                  fontSize: '16px',
                  backgroundColor: '#f44336',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: 'pointer'
                }}
              >
                Reset Game
              </button>
            </div>
          )}
        </div>

        <ModelSelector
          label="Black"
          models={MODELS}
          selectedModel={gameState.blackModel}
          onModelChange={(model) => setGameState(prev => ({ ...prev, blackModel: model }))}
          disabled={gameState.isGameStarted}
        />
      </div>

      <div style={{ textAlign: 'center' }}>
        {gameState.isGameStarted && !gameState.isGameOver && (
          <div 
            ref={thinkingOutputBoxRef}
            style={{
              marginTop: '10px',
              marginBottom: '10px',
              width: '800px',
              maxWidth: '90%',
              margin: '10px auto',
              backgroundColor: '#f5f5f5',
              border: '1px solid #ddd',
              borderRadius: '8px',
              padding: '15px',
              textAlign: 'left',
              height: '150px',
              overflowY: 'auto',
              transition: 'opacity 0.3s ease',
              opacity: gameState.thinkingOutput ? 1 : 0.7,
              scrollbarWidth: 'thin',
              scrollbarColor: '#888 #f5f5f5'
            }}
          >
            <h4 style={{ margin: '0 0 10px 0', color: '#333', fontSize: '16px' }}>🤔 Thinking Process:</h4>
            <pre style={{ 
              whiteSpace: 'pre-wrap', 
              wordWrap: 'break-word',
              fontFamily: 'Consolas, Monaco, monospace',
              fontSize: '13px',
              lineHeight: '1.5',
              margin: 0,
              color: gameState.thinkingOutput ? '#555' : '#999'
            }}>
              {gameState.thinkingOutput || 'Waiting for model to think...'}
            </pre>
          </div>
        )}
        {gameState.drawOffer.offered && !gameState.isThinking && (
          <div style={{ 
            fontSize: '18px', 
            color: '#FF9800',
            fontWeight: 'bold',
            backgroundColor: '#FFF3E0',
            padding: '10px',
            borderRadius: '8px',
            border: '2px solid #FF9800',
            margin: '10px 0'
          }}>
            🤝 {gameState.drawOffer.offeredBy === 'white' ? 'White' : 'Black'} has offered a draw!
            <br />
            <span style={{ fontSize: '14px', fontWeight: 'normal' }}>
              Waiting for {gameState.drawOffer.offeredBy === 'white' ? 'Black' : 'White'} to respond...
            </span>
          </div>
        )}
        {gameState.gameResult && (
          <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#333' }}>
            {gameState.gameResult}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', gap: '30px', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '5px' }}>
          <CapturedPiecesRow 
            pieces={gameState.capturedPieces.black} 
            capturedBy="black"
          />
          
          <ChessBoard 
            game={gameState.game}
            isGameStarted={gameState.isGameStarted}
          />
          
          <CapturedPiecesRow 
            pieces={gameState.capturedPieces.white} 
            capturedBy="white"
          />
        </div>

        <div style={{ 
          minWidth: '300px',
          maxWidth: '400px',
          border: '2px solid #666',
          borderRadius: '8px',
          backgroundColor: '#f8f8f8'
        }}>
          <div>
            <div style={{
              backgroundColor: '#333',
              color: 'white',
              padding: '12px',
              textAlign: 'center',
              fontWeight: 'bold',
              fontSize: '16px'
            }}>
              Move History
            </div>
            <div style={{
              backgroundColor: '#f0f0f0',
              padding: '8px 12px',
              fontSize: '11px',
              color: '#666',
              textAlign: 'center',
              borderBottom: '1px solid #ddd'
            }}>
              Numbers in parentheses show thinking tokens used, followed by response time
            </div>
          </div>
          
          <div style={{ 
            maxHeight: '500px', 
            overflowY: 'auto',
            padding: '10px'
          }}>
            {gameState.game.history().length === 0 ? (
              <p style={{ textAlign: 'center', color: '#666', margin: '20px 0' }}>
                No moves yet
              </p>
            ) : (
              <table style={{ 
                width: '100%', 
                borderCollapse: 'collapse',
                fontSize: '14px'
              }}>
                <thead>
                  <tr>
                    <th style={{ 
                      border: '1px solid #ddd', 
                      padding: '8px', 
                      backgroundColor: '#e8e8e8',
                      textAlign: 'center',
                      width: '20%'
                    }}>
                      #
                    </th>
                    <th style={{ 
                      border: '1px solid #ddd', 
                      padding: '8px', 
                      backgroundColor: '#e8e8e8',
                      textAlign: 'center',
                      width: '40%'
                    }}>
                      White
                    </th>
                    <th style={{ 
                      border: '1px solid #ddd', 
                      padding: '8px', 
                      backgroundColor: '#e8e8e8',
                      textAlign: 'center',
                      width: '40%'
                    }}>
                      Black
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: Math.ceil(gameState.game.history().length / 2) }, (_, i) => {
                    const moveNumber = i + 1;
                    const whiteMove = gameState.game.history()[i * 2];
                    const blackMove = gameState.game.history()[i * 2 + 1];
                    const whiteThinkingTokens = gameState.moveThinkingTokens[i * 2];
                    const blackThinkingTokens = gameState.moveThinkingTokens[i * 2 + 1];
                    const whiteMoveTime = gameState.moveTimes[i * 2];
                    const blackMoveTime = gameState.moveTimes[i * 2 + 1];
                    
                    return (
                      <tr key={moveNumber}>
                        <td style={{ 
                          border: '1px solid #ddd', 
                          padding: '6px', 
                          textAlign: 'center',
                          fontWeight: 'bold'
                        }}>
                          {moveNumber}
                        </td>
                        <td style={{ 
                          border: '1px solid #ddd', 
                          padding: '6px', 
                          textAlign: 'center',
                          fontFamily: 'monospace'
                        }}>
                          {whiteMove ? (
                            <div>
                              <div>{whiteMove}</div>
                              {(whiteThinkingTokens !== undefined || whiteMoveTime !== undefined) && (
                                <div style={{ fontSize: '10px', color: '#666' }}>
                                  {whiteThinkingTokens !== undefined && `(${whiteThinkingTokens})`}
                                  {whiteThinkingTokens !== undefined && whiteMoveTime !== undefined && ' '}
                                  {whiteMoveTime !== undefined && `${formatTime(whiteMoveTime)}`}
                                </div>
                              )}
                            </div>
                          ) : ''}
                        </td>
                        <td style={{ 
                          border: '1px solid #ddd', 
                          padding: '6px', 
                          textAlign: 'center',
                          fontFamily: 'monospace'
                        }}>
                          {blackMove ? (
                            <div>
                              <div>{blackMove}</div>
                              {(blackThinkingTokens !== undefined || blackMoveTime !== undefined) && (
                                <div style={{ fontSize: '10px', color: '#666' }}>
                                  {blackThinkingTokens !== undefined && `(${blackThinkingTokens})`}
                                  {blackThinkingTokens !== undefined && blackMoveTime !== undefined && ' '}
                                  {blackMoveTime !== undefined && `${formatTime(blackMoveTime)}`}
                                </div>
                              )}
                            </div>
                          ) : '...'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          
          <div style={{
            padding: '10px',
            borderTop: '1px solid #ddd',
            backgroundColor: '#f0f0f0',
            fontSize: '12px',
            textAlign: 'center'
          }}>
            Total moves: {gameState.game.history().length}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChessGame;