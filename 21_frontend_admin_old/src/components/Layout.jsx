import { Link, useLocation } from 'react-router-dom';
import { Home, PieChart, AlertTriangle } from 'lucide-react';

export default function Layout({ children }) {
    const location = useLocation();

    const navigation = [
        { name: '대시보드', path: '/', icon: Home },
        { name: '소비 분석', path: '/consumption', icon: PieChart },
        { name: '이상거래', path: '/anomalies', icon: AlertTriangle },
    ];

    return (
        <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f9fafb' }}>
            {/* Sidebar */}
            <div style={{
                width: '240px',
                backgroundColor: '#1f2937',
                color: 'white',
                padding: '24px 0',
                position: 'fixed',
                height: '100vh',
                overflowY: 'auto'
            }}>
                <div style={{ padding: '0 24px', marginBottom: '32px' }}>
                    <h1 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>Caffeine Admin</h1>
                    <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>관리자 페이지</p>
                </div>

                <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '0 16px' }}>
                    {navigation.map((item) => {
                        const isActive = location.pathname === item.path;
                        const Icon = item.icon;

                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '12px',
                                    padding: '12px 16px',
                                    borderRadius: '8px',
                                    textDecoration: 'none',
                                    color: isActive ? '#ffffff' : '#9ca3af',
                                    backgroundColor: isActive ? '#3b82f6' : 'transparent',
                                    transition: 'all 0.2s',
                                    fontWeight: isActive ? 600 : 400
                                }}
                                onMouseEnter={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.backgroundColor = '#374151';
                                        e.currentTarget.style.color = '#ffffff';
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.backgroundColor = 'transparent';
                                        e.currentTarget.style.color = '#9ca3af';
                                    }
                                }}
                            >
                                <Icon size={20} />
                                <span>{item.name}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div style={{
                    position: 'absolute',
                    bottom: '24px',
                    left: '24px',
                    right: '24px',
                    padding: '16px',
                    backgroundColor: '#374151',
                    borderRadius: '8px'
                }}>
                    <p style={{ fontSize: '12px', color: '#9ca3af', margin: '0 0 4px 0' }}>Version</p>
                    <p style={{ fontSize: '14px', fontWeight: 600, margin: 0 }}>v1.0.0</p>
                </div>
            </div>

            {/* Main Content */}
            <div style={{ marginLeft: '240px', flex: 1, padding: '24px' }}>
                {children}
            </div>
        </div>
    );
}
