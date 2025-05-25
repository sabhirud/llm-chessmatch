declare module 'react-chess-pieces' {
  import { ComponentType } from 'react';

  interface ChessPieceProps {
    piece: string;
    color: 'white' | 'black';
    size?: number;
  }

  export const ChessPiece: ComponentType<ChessPieceProps>;
}