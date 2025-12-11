import { useState, useEffect } from 'react';
import { Users, ShoppingCart, DollarSign, TrendingUp, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { getFullAnalysis } from '../api/services';

export default function Dashboard() {
    const [stats, setStats] = useState([]);
    const [lineData, setLineData] = useState([]);
    const [barData, setBarData] = useState([]);
    const [tableData, setTableData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dataSource, setDataSource] = useState('');

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const analysis = await getFullAnalysis();
            setDataSource(analysis.data_source || 'DB');

            const summary = analysis.summary;
            setStats([
                {
                    title: '총 거래 건수',
                    value: summary.transaction_count.toLocaleString() + '건',
                    trend: `${summary.month_over_month_change > 0 ? '+' : ''}${summary.month_over_month_change.toFixed(1)}% 전월 대비`,
                    icon: ShoppingCart,
                    color: 'text-blue-600',
                    trendColor: summary.month_over_month_change > 0 ? 'text-green-500' : 'text-red-500'
                },
                {
                    title: '총 거래액',
                    value: '₩' + (summary.total_spending / 10000).toFixed(1) + '만',
                    trend: `${summary.month_over_month_change > 0 ? '+' : ''}${summary.month_over_month_change.toFixed(1)}% 전월 대비`,
                    icon: DollarSign,
                    color: 'text-blue-600',
                    trendColor: summary.month_over_month_change > 0 ? 'text-green-500' : 'text-red-500'
                },
                {
                    title: '평균 거래액',
                    value: '₩' + Math.round(summary.average_transaction).toLocaleString(),
                    trend: '평균 거래액',
                    icon: TrendingUp,
                    color: 'text-blue-600',
                    trendColor: 'text-gray-500'
                },
                {
                    title: '최다 카테고리',
                    value: summary.top_category,
                    trend: '가장 많이 소비한 카테고리',
                    icon: Users,
                    color: 'text-blue-600',
                    trendColor: 'text-gray-500'
                }
            ]);

            const monthlyTrend = analysis.monthly_trend || [];
            const lineChartData = monthlyTrend.map(item => ({
                name: item.month.split('-')[1] + '월',
                value: Math.round(item.total_amount / 10000),
            }));
            setLineData(lineChartData);

            const categories = analysis.category_breakdown || [];
            const barChartData = categories.map(item => ({
                name: item.category,
                value: Math.round(item.total_amount / 10000),
            }));
            setBarData(barChartData);

            const tableRows = categories.map(item => ({
                category: item.category,
                amount: '₩' + (item.total_amount >= 100000000
                    ? (item.total_amount / 100000000).toFixed(1) + '억'
                    : (item.total_amount / 10000).toFixed(1) + '만'),
                count: item.transaction_count.toLocaleString() + '건',
                ratio: item.percentage.toFixed(1) + '%'
            }));
            setTableData(tableRows);

            console.log('✅ 관리자 대시보드 데이터 로드 완료 - 출처:', analysis.data_source);
        } catch (error) {
            console.error('❌ 대시보드 데이터 로드 실패:', error);
            setDataSource('[ERROR]');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{
                        width: '48px',
                        height: '48px',
                        border: '4px solid #f3f4f6',
                        borderTop: '4px solid #3b82f6',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite',
                        margin: '0 auto'
                    }}></div>
                    <p style={{ marginTop: '16px', color: '#6b7280' }}>데이터 로딩 중...</p>
                </div>
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: '32px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1f2937', margin: '0 0 8px 0' }}>대시보드</h2>
                        <p style={{ color: '#6b7280', margin: 0 }}>전체 서비스 현황을 한눈에 확인하세요</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{
                            fontSize: '14px',
                            padding: '6px 12px',
                            borderRadius: '9999px',
                            backgroundColor: dataSource.includes('DB') ? '#dcfce7' : '#fef3c7',
                            color: dataSource.includes('DB') ? '#15803d' : '#a16207'
                        }}>
                            {dataSource.includes('DB') ? '🟢 실시간 DB' : '🟡 ' + dataSource}
                        </span>
                        <button
                            onClick={fetchDashboardData}
                            style={{
                                padding: '8px 16px',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}
                        >
                            <RefreshCw size={16} />
                            새로고침
                        </button>
                    </div>
                </div>
            </div>

            {/* Stats Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: '24px',
                marginBottom: '24px'
            }}>
                {stats.map((stat, index) => {
                    const Icon = stat.icon;
                    return (
                        <div key={index} style={{
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '24px',
                            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                            border: '1px solid #f3f4f6'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                                <div>
                                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 8px 0' }}>{stat.title}</p>
                                    <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#1f2937', margin: '0 0 8px 0' }}>{stat.value}</p>
                                    <p style={{ fontSize: '12px', color: stat.trendColor, margin: 0 }}>{stat.trend}</p>
                                </div>
                                <Icon size={24} style={{ color: '#3b82f6' }} />
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Charts Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px', marginBottom: '24px' }}>
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                    border: '1px solid #f3f4f6'
                }}>
                    <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', marginBottom: '24px' }}>월별 거래 추이</h3>
                    {lineData.length > 0 ? (
                        <>
                            <ResponsiveContainer width="100%" height={220}>
                                <LineChart data={lineData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <Tooltip />
                                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
                                </LineChart>
                            </ResponsiveContainer>
                            <p style={{ fontSize: '12px', color: '#9ca3af', textAlign: 'center', marginTop: '8px' }}>단위: 만원</p>
                        </>
                    ) : (
                        <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                            데이터가 없습니다
                        </div>
                    )}
                </div>

                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                    border: '1px solid #f3f4f6'
                }}>
                    <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', marginBottom: '24px' }}>카테고리별 소비</h3>
                    {barData.length > 0 ? (
                        <>
                            <ResponsiveContainer width="100%" height={220}>
                                <BarChart data={barData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <Tooltip />
                                    <Bar dataKey="value" fill="#1e293b" radius={[4, 4, 0, 0]} barSize={40} />
                                </BarChart>
                            </ResponsiveContainer>
                            <p style={{ fontSize: '12px', color: '#9ca3af', textAlign: 'center', marginTop: '8px' }}>단위: 만원</p>
                        </>
                    ) : (
                        <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                            데이터가 없습니다
                        </div>
                    )}
                </div>
            </div>

            {/* Table */}
            {tableData.length > 0 && (
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                    border: '1px solid #f3f4f6',
                    overflow: 'hidden'
                }}>
                    <div style={{ padding: '24px', borderBottom: '1px solid #f3f4f6' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>카테고리별 상세</h3>
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead style={{ backgroundColor: '#f9fafb' }}>
                            <tr>
                                <th style={{ padding: '12px 24px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>카테고리</th>
                                <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>금액</th>
                                <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>건수</th>
                                <th style={{ padding: '12px 24px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#6b7280' }}>비율</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tableData.map((row, index) => (
                                <tr key={index} style={{ borderTop: '1px solid #f3f4f6' }}>
                                    <td style={{ padding: '12px 24px', fontSize: '14px', color: '#1f2937' }}>{row.category}</td>
                                    <td style={{ padding: '12px 24px', textAlign: 'right', fontSize: '14px', fontWeight: 600, color: '#1f2937' }}>{row.amount}</td>
                                    <td style={{ padding: '12px 24px', textAlign: 'right', fontSize: '14px', color: '#6b7280' }}>{row.count}</td>
                                    <td style={{ padding: '12px 24px', textAlign: 'right', fontSize: '14px', color: '#6b7280' }}>{row.ratio}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
