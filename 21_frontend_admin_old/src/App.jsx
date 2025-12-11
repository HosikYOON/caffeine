import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Consumption from './pages/Consumption';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/consumption" element={<Consumption />} />
          <Route path="/anomalies" element={
            <div style={{ padding: '24px' }}>
              <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '16px' }}>이상거래 탐지</h2>
              <div style={{
                backgroundColor: 'white',
                padding: '48px',
                borderRadius: '12px',
                textAlign: 'center',
                boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
              }}>
                <p style={{ fontSize: '48px', marginBottom: '16px' }}>🚧</p>
                <p style={{ fontSize: '18px', color: '#6b7280' }}>
                  이상거래 탐지 기능은 준비 중입니다
                </p>
                <p style={{ fontSize: '14px', color: '#9ca3af', marginTop: '8px' }}>
                  현재 RDS에 이상거래 데이터가 없습니다
                </p>
              </div>
            </div>
          } />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
