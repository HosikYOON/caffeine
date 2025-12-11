import { useState, useEffect } from 'react';
import { PieChart, TrendingUp, RefreshCw } from 'lucide-react';
import { PieChart as RechartsPie, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { getCategoryBreakdown } from '../api/services';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d'];

export default function Consumption() {
    const [consumptionData, setConsumptionData] = useState([]);
    const [pieData, setPieData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [dataSource, setDataSource] = useState('');

    useEffect(() => {
        fetchConsumption();
    }, []);

    const fetchConsumption = async () => {
        try {
            setLoading(true);
            const categories = await getCategoryBreakdown(1);

            const itemsData = categories.map(cat => ({
                name: cat.category,
                amount: '₩' + cat.total_amount.toLocaleString(),
                percent: cat.percentage + '%'
            }));
            setConsumptionData(itemsData);

            const chartData = categories.map(cat => ({
                name: cat.category,
                value: cat.total_amount
            }));
            setPieData(chartData);

            setDataSource('DB (실시간)');
            console.log('✅ 소비 분석 데이터 로드 완료:', categories.length + '개 카테고리');
        } catch (error) {
            console.error('❌ 소비 데이터 로드 실패:', error);
            setDataSource('[ERROR]');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1f2937', margin: '0 0 8px 0' }}>소비 분석</h2>
                        <p style={{ color: '#6b7280', margin: 0 }}>전체적인 소비 트렌드를 분석합니다</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{
                            fontSize: '14px',
                            padding: '6px 12px',
                            borderRadius: '9999px',
                            backgroundColor: dataSource.includes('DB') ? '#dcfce7' : '#fef3c7',
                            color: dataSource.includes('DB') ? '#15803d' : '#a16207'
                        }}>
                            {dataSource}
                        </span>
                        <button
                            onClick={fetchConsumption}
                            disabled={loading}
                            style={{
                                padding: '8px 16px',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: loading ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                opacity: loading ? 0.5 : 1
                            }}
                        >
                            <RefreshCw size={16} style={loading ? { animation: 'spin 1s linear infinite' } : {}} />
                            새로고침
                        </button>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
                <div style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                    border: '1px solid #f3f4f6'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>월간 소비 분포</h3>
                        <PieChart size={20} style={{ color: '#9ca3af' }} />
                    </div>
                    {loading ? (
                        <div style={{ height: '256px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div style={{
                                width: '48px',
                                height: '48px',
                                border: '4px solid #f3f4f6',
                                borderTop: '4px solid #3b82f6',
                                borderRadius: '50%',
                                animation: 'spin 1s linear infinite'
                            }}></div>
                        </div>
                    ) : pieData.length > 0 ? (
                        <div style={{ height: '256px' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <RechartsPie>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        labelLine={false}
                                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                        outerRadius={80}
                                        fill="#8884d8"
                                        dataKey="value"
                                    >
                                        {pieData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip formatter={(value) => '₩' + value.toLocaleString()} />
                                    <Legend />
                                </RechartsPie>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div style={{ height: '256px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
                            <p style={{ color: '#9ca3af' }}>데이터가 없습니다</p>
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
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>주요 지출 카테고리</h3>
                        <TrendingUp size={20} style={{ color: '#9ca3af' }} />
                    </div>
                    {loading ? (
                        <div style={{ height: '256px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <div style={{
                                width: '48px',
                                height: '48px',
                                border: '4px solid #f3f4f6',
                                borderTop: '4px solid #3b82f6',
                                borderRadius: '50%',
                                animation: 'spin 1s linear infinite'
                            }}></div>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            {consumptionData.map((item, i) => (
                                <div key={i} style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '12px',
                                    backgroundColor: '#f9fafb',
                                    borderRadius: '8px'
                                }}>
                                    <span style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937' }}>{item.name}</span>
                                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                                        <span style={{ fontSize: '14px', color: '#6b7280' }}>{item.amount}</span>
                                        <span style={{ fontSize: '14px', fontWeight: 600, color: '#3b82f6' }}>{item.percent}</span>
                                    </div>
                                </div>
                            ))}
                            {consumptionData.length === 0 && (
                                <div style={{ textAlign: 'center', color: '#9ca3af', padding: '32px 0' }}>
                                    소비 데이터가 없습니다
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
