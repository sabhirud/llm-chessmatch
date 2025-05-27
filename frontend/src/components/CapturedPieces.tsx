import React from 'react';
import ChessPiece from './ChessPieces';

interface CapturedPiecesRowProps {
  pieces: string[];
  capturedBy: 'white' | 'black';
}

const CapturedPiecesRow: React.FC<CapturedPiecesRowProps> = ({ pieces, capturedBy }) => {
  const pieceCounts: { [key: string]: number } = {};
  pieces.forEach(piece => {
    pieceCounts[piece] = (pieceCounts[piece] || 0) + 1;
  });

  const pieceOrder = ['q', 'r', 'b', 'n', 'p'];
  const sortedPieces = pieceOrder.filter(piece => pieceCounts[piece] > 0);

  if (sortedPieces.length === 0) {
    return null;
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-start',
      minHeight: '30px',
      padding: '4px 0',
      width: '560px',
      gap: '8px'
    }}>
      {sortedPieces.map(piece => (
        <div key={piece} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '2px'
        }}>
          <ChessPiece 
            piece={piece} 
            color={capturedBy === 'white' ? 'black' : 'white'} 
            size={28} 
          />
          {pieceCounts[piece] > 1 && (
            <span style={{
              fontSize: '12px',
              fontWeight: 'bold',
              color: '#666',
              marginLeft: '2px'
            }}>
              ×{pieceCounts[piece]}
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

export default CapturedPiecesRow;