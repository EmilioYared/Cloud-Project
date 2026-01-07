import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import DocumentsList from './pages/DocumentsList';
import Chat from './pages/Chat';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<DocumentsList />} />
          <Route path="/chat/:docId" element={<Chat />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
