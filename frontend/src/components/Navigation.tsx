import React from 'react';
import { Link } from 'react-router-dom';

const Navigation: React.FC = () => {
  return (
    <nav style={{ 
      padding: '1rem', 
      backgroundColor: '#333', 
      display: 'flex', 
      justifyContent: 'center',
      gap: '2rem'
    }}>
      <Link 
        to="/" 
        style={{ 
          color: 'white', 
          textDecoration: 'none', 
          fontSize: '1.2rem',
          fontWeight: 'bold'
        }}
      >
        Home
      </Link>
      <Link 
        to="/about" 
        style={{ 
          color: 'white', 
          textDecoration: 'none', 
          fontSize: '1.2rem',
          fontWeight: 'bold'
        }}
      >
        What is this?
      </Link>
    </nav>
  );
};

export default Navigation;