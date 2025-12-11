"use client";

import { useState, useEffect } from 'react';
import { PieChart, TrendingUp, RefreshCw } from 'lucide-react';
import { PieChart as RechartsPie, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { ConsumptionItem } from '@/components/ui/ConsumptionItem';
import { getCategoryBreakdown } from '@/api/services';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d'];

export default function ConsumptionPage() {
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
            // 최근 1개월 카테고리별 소비 데이터
            const categories = await getCategoryBreakdown(1);

            // ConsumptionItem용 데이터 변환
            const itemsData = categories.map(cat => ({
                name: cat.category,
                amount: '₩' + cat.total_amount.toLocaleString(),
                percent: cat.percentage + '%'
            }));
            setConsumptionData(itemsData);

            // PieChart용 데이터 변환
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
            // 에러 시 Mock 데이터
            setConsumptionData([
                { name: '식비', amount: '₩450,000', percent: '35%' },
                { name: '쇼핑', amount: '₩320,000', percent: '25%' },
                { name: '교통', amount: '₩150,000', percent: '12%' },
            ]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="mb-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-800">소비 분석</h2>
                        <p className="text-gray-500 mt-1">전체적인 소비 트렌드를 분석합니다</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className={`text-sm px-3 py-1 rounded-full ${dataSource.includes('DB') ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                            }`}>
                            {dataSource}
                        </span>
                        <button
                            onClick={fetchConsumption}
                            disabled={loading}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                            새로고침
                        </button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold text-gray-800">월간 소비 분포</h3>
                        <PieChart className="w-5 h-5 text-gray-400" />
                    </div>
                    {loading ? (
                        <div className="h-64 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                        </div>
                    ) : pieData.length > 0 ? (
                        <div className="h-64">
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
                        <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
                            <p className="text-gray-400">데이터가 없습니다</p>
                        </div>
                    )}
                </div>

                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold text-gray-800">주요 지출 카테고리</h3>
                        <TrendingUp className="w-5 h-5 text-gray-400" />
                    </div>
                    {loading ? (
                        <div className="h-64 flex items-center justify-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {consumptionData.map((item, i) => (
                                <ConsumptionItem
                                    key={i}
                                    name={item.name}
                                    amount={item.amount}
                                    percent={item.percent}
                                />
                            ))}
                            {consumptionData.length === 0 && (
                                <div className="text-center text-gray-400 py-8">
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
