import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import ChessGame from './components/ChessGame';
import AboutPage from './components/AboutPage';
import Navigation from './components/Navigation';

function App() {
  return (
    <Router>
      <div className="App">
        <Navigation />
        <Routes>
          <Route path="/" element={
            <header className="App-header">
              <ChessGame />
            </header>
          } />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
