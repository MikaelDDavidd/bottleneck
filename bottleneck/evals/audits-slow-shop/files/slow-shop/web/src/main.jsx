import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Orders from './pages/Orders';
import Catalog from './pages/Catalog';
import Reports from './pages/Reports';

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Orders />} />
      <Route path="/catalog" element={<Catalog />} />
      <Route path="/reports" element={<Reports />} />
    </Routes>
  </BrowserRouter>
);
