import React from 'react';

const AboutPage: React.FC = () => {
  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <p>
        LLM Chess is an experimental, <a href="https://github.com/rishikavikondala/llm-chess" target="_blank" rel="noopener noreferrer" style={{ color: '#0099cc', textDecoration: 'underline' }}>open-source</a> app that lets thinking models play chess against each other. The app currently supports Claude Sonnet 4, Claude Opus 4, Gemini 2.5 Pro, Gemini 2.5 Flash, o4-mini, and Grok 3 Mini.
      </p>

      <p>
        The app has an "Auto" mode, where the game automatically sends requests to models for each turn, or "Manual" mode, where the user can decide when to kick off the next turn.
      </p>

      <p>
        Beyond standard chess moves, models can also offer draws (which the opponent can accept or decline) or resign when they determine their position is hopeless. This adds realistic chess behavior where models can recognize when continuing play is futile.
      </p>

      <p>
        This app was built entirely with <a href="https://www.anthropic.com/claude-code" target="_blank" rel="noopener noreferrer" style={{ color: '#0099cc', textDecoration: 'underline' }}>Claude Code</a>.
      </p>

      <p>
        Have questions or thoughts? <a href="https://www.rishikavikondala.com/" target="_blank" rel="noopener noreferrer" style={{ color: '#0099cc', textDecoration: 'underline' }}>Reach out!</a>
      </p>
    </div>
  );
};

export default AboutPage;