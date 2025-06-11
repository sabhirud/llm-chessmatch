import React, { useEffect, useState } from 'react';
import { Chess } from 'chess.js';
import ChessPiece from './ChessPieces';

interface LastMove {
  from: string;
  to: string;
  color: 'w' | 'b';
  piece: string;
  captured?: string;
}

interface ChessBoardProps {
  game: Chess;
  isGameStarted: boolean;
  lastMove: LastMove | null;
}
const SQUARE_SIZE = 70;

const ChessBoard: React.FC<ChessBoardProps> = ({ game, isGameStarted, lastMove }) => {
  const board = game.board();
  const [animateMove, setAnimateMove] = useState(false);
  const [currentMove, setCurrentMove] = useState<LastMove | null>(null);

  useEffect(() => {
    if (lastMove) {
      setCurrentMove(lastMove);
      setAnimateMove(false);
      requestAnimationFrame(() => setAnimateMove(true));
    }
  }, [lastMove]);

  const squareToCoords = (sq: string) => {
    const file = sq.charCodeAt(0) - 97;
    const rank = 8 - parseInt(sq[1], 10);
    return { row: rank, col: file };
  };

  const renderSquare = (piece: any, row: number, col: number) => {
    const isLightSquare = (row + col) % 2 === 0;
    const squareColor = isLightSquare ? '#f0d9b5' : '#b58863';
    const square = `${String.fromCharCode(97 + col)}${8 - row}`;
    const isMovingPiece = currentMove && currentMove.to === square;

    let pieceStyle: React.CSSProperties = {};
    if (isMovingPiece && currentMove) {
      const from = squareToCoords(currentMove.from);
      const offsetX = (from.col - col) * SQUARE_SIZE;
      const offsetY = (from.row - row) * SQUARE_SIZE;
      pieceStyle.transform = animateMove ? 'translate(0, 0)' : `translate(${offsetX}px, ${offsetY}px)`;
      pieceStyle.transition = 'transform 0.3s ease';
    }

    return (
      <div
        key={`${row}-${col}`}
        style={{
          width: `${SQUARE_SIZE}px`,
          height: `${SQUARE_SIZE}px`,
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
          <div style={pieceStyle}>
            <ChessPiece
              piece={piece.type}
              color={piece.color === 'w' ? 'white' : 'black'}
              size={50}
            />
          </div>
        )}
        {isMovingPiece && currentMove?.captured && !animateMove && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              animation: 'fadeOut 0.3s forwards',
              pointerEvents: 'none'
            }}
          >
            <ChessPiece
              piece={currentMove.captured}
              color={currentMove.color === 'w' ? 'black' : 'white'}
              size={50}
            />
          </div>
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
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(8, ${SQUARE_SIZE}px)`,
      gridTemplateRows: `repeat(8, ${SQUARE_SIZE}px)`,
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
  );
};

export default ChessBoard;
