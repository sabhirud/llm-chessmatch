import React from 'react';
import { Chess } from 'chess.js';
import ChessPiece from './ChessPieces';

interface ChessBoardProps {
  game: Chess;
  isGameStarted: boolean;
}

const ChessBoard: React.FC<ChessBoardProps> = ({ game, isGameStarted }) => {
  const board = game.board();

  const renderSquare = (piece: any, row: number, col: number) => {
    const isLightSquare = (row + col) % 2 === 0;
    const squareColor = isLightSquare ? '#f0d9b5' : '#b58863';
    
    return (
      <div
        key={`${row}-${col}`}
        style={{
          width: '70px',
          height: '70px',
          backgroundColor: squareColor,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid #8b4513',
          position: 'relative',
          boxSizing: 'border-box'
        }}
      >
        {piece && (
          <ChessPiece
            piece={piece.type}
            color={piece.color === 'w' ? 'white' : 'black'}
            size={50}
          />
        )}
        <span style={{
          position: 'absolute',
          bottom: '2px',
          right: '4px',
          fontSize: '10px',
          opacity: 0.6,
          color: isLightSquare ? '#8b4513' : '#f0d9b5',
          fontWeight: 'bold'
        }}>
          {String.fromCharCode(97 + col)}{8 - row}
        </span>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(8, 70px)',
        gridTemplateRows: 'repeat(8, 70px)',
        border: '3px solid #8b4513',
        backgroundColor: '#fff',
        borderRadius: '8px',
        overflow: 'hidden',
        opacity: isGameStarted ? 1 : 0.7
      }}>
        {board.map((row, rowIndex) =>
          row.map((piece, colIndex) =>
            renderSquare(piece, rowIndex, colIndex)
          )
        )}
      </div>
      
      <div style={{ 
        marginTop: '15px', 
        fontSize: '12px', 
        color: '#666',
        fontFamily: 'monospace',
        backgroundColor: '#f8f8f8',
        padding: '8px 12px',
        borderRadius: '4px',
        border: '1px solid #ddd'
      }}>
        FEN: {game.fen()}
      </div>
    </div>
  );
};

export default ChessBoard;