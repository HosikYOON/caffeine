import React, { useState, useMemo, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Download, Search, Calendar, Loader2 } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

const CATEGORY_COLORS = {
    '식비': '#FF6B6B',
    '교통': '#4ECDC4',
    '쇼핑': '#FFE66D',
    '의료': '#95E1D3',
    '통신': '#A8E6CF',
    '주거': '#C7CEEA',
    '문화': '#FFDAC1',
    '기타': '#D4A5A5'
};

const AdminIntegratedAnalysis = () => {
    const [selectedMonth, setSelectedMonth] = useState(''); // 빈 값 = 전체 데이터
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState(null);
    const [selectedDate, setSelectedDate] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTransactions = async () => {
            setLoading(true);
            setError(null);

            try {
                const params = new URLSearchParams({
                    page: '1',
                    page_size: '100'
                });

                // 월이 선택된 경우에만 날짜 필터 추가
                if (selectedMonth) {
                    const [year, month] = selectedMonth.split('-');
                    const startDate = `${selectedMonth}-01`;
                    const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate();
                    const endDate = `${selectedMonth}-${lastDay}`;
                    params.set('start_date', startDate);
                    params.set('end_date', endDate);
                }

                const response = await fetch(`${API_BASE_URL}/api/transactions?${params}`, {
                    headers: { 'Content-Type': 'application/json' },
                });

                if (!response.ok) {
                    const errorBody = await response.text();
                    console.error('API Error Response:', errorBody);
                    throw new Error(`API Error: ${response.status}`);
                }

                const data = await response.json();

                const formattedTransactions = data.transactions.map(tx => {
                    const [datePart, timePart] = tx.transaction_date.split(' ');
                    return {
                        id: tx.id,
                        userId: `user_${String(tx.id).padStart(3, '0')}***`,
                        merchant: tx.merchant,
                        category: tx.category,
                        amount: tx.amount,
                        date: datePart,
                        time: timePart?.substring(0, 5) || '00:00',
                        ipAddress: 'N/A'
                    };
                });

                setTransactions(formattedTransactions);
            } catch (err) {
                console.error('Failed to fetch transactions:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchTransactions();
    }, [selectedMonth]);

    const filteredTransactions = useMemo(() => {
        let filtered = transactions;
        if (searchQuery) filtered = filtered.filter(tx => tx.merchant.toLowerCase().includes(searchQuery.toLowerCase()));
        if (selectedCategory) filtered = filtered.filter(tx => tx.category === selectedCategory);
        if (selectedDate) filtered = filtered.filter(tx => tx.date === selectedDate);
        return filtered;
    }, [transactions, searchQuery, selectedCategory, selectedDate]);

    const categoryData = useMemo(() => {
        const categoryMap = {};
        filteredTransactions.forEach(tx => {
            if (!categoryMap[tx.category]) categoryMap[tx.category] = 0;
            categoryMap[tx.category] += tx.amount;
        });
        return Object.keys(categoryMap).map(category => ({
            name: category,
            value: categoryMap[category],
            color: CATEGORY_COLORS[category] || CATEGORY_COLORS['기타']
        }));
    }, [filteredTransactions]);

    const dailyData = useMemo(() => {
        const dailyMap = {};
        filteredTransactions.forEach(tx => {
            if (!dailyMap[tx.date]) dailyMap[tx.date] = 0;
            dailyMap[tx.date] += tx.amount;
        });
        return Object.keys(dailyMap).sort().map(date => ({
            date: date.split('-')[2] + '일',
            fullDate: date,
            amount: dailyMap[date]
        }));
    }, [filteredTransactions]);

    const handlePieClick = (data) => setSelectedCategory(prev => prev === data.name ? null : data.name);
    const handleBarClick = (data) => setSelectedDate(prev => prev === data.fullDate ? null : data.fullDate);

    const handleExport = () => {
        const csvContent = [
            ['No', 'Transaction ID', 'User ID', 'Date', 'Time', 'Merchant', 'Category', 'Amount', 'IP Address'],
            ...filteredTransactions.map((tx, index) => [index + 1, tx.id, tx.userId, tx.date, tx.time, tx.merchant, tx.category, tx.amount, tx.ipAddress])
        ].map(row => row.join(',')).join('\n');
        const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `transactions_${selectedMonth}.csv`;
        link.click();
    };

    const getFilterText = () => {
        const filters = [];
        if (selectedCategory) filters.push(selectedCategory);
        if (selectedDate) filters.push(selectedDate);
        if (searchQuery) filters.push(`"${searchQuery}"`);
        return filters.length > 0 ? `필터링: ${filters.join(' / ')}` : '전체 거래 내역';
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
                    <p className="text-gray-600">데이터를 불러오는 중...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center bg-white p-8 rounded-lg shadow-md max-w-md">
                    <div className="text-red-500 text-5xl mb-4">⚠️</div>
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">데이터 로딩 실패</h3>
                    <p className="text-gray-600 mb-4">{error}</p>
                    <button onClick={() => window.location.reload()} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md">다시 시도</button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-[1600px] mx-auto">

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
                    <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                            <Calendar className="w-5 h-5 text-gray-500" />
                            <input type="month" value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)} className="border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div className="flex-1 max-w-md relative">
                            <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                            <input type="text" placeholder="가맹점명 검색..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full border border-gray-300 rounded-md pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <button onClick={handleExport} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md">
                            <Download className="w-4 h-4" />엑셀 다운로드
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-6 mb-6">
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h3 className="text-lg font-semibold text-gray-800 mb-4">카테고리별 거래 비중</h3>
                        <p className="text-sm text-gray-500 mb-4">💡 차트 조각을 클릭하여 해당 카테고리 거래 내역을 조회하세요</p>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie data={categoryData} cx="50%" cy="50%" labelLine={false} label={(entry) => `${entry.name} (${((entry.value / filteredTransactions.reduce((sum, tx) => sum + tx.amount, 0)) * 100).toFixed(1)}%)`} outerRadius={100} fill="#8884d8" dataKey="value" onClick={handlePieClick} style={{ cursor: 'pointer' }}>
                                    {categoryData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} opacity={selectedCategory && selectedCategory !== entry.name ? 0.3 : 1} />)}
                                </Pie>
                                <Tooltip formatter={(value) => `₩${value.toLocaleString()}`} />
                            </PieChart>
                        </ResponsiveContainer>
                        {selectedCategory && (<div className="mt-4 text-center"><span className="inline-block bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium">선택: {selectedCategory} ✕</span></div>)}
                    </div>

                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <h3 className="text-lg font-semibold text-gray-800 mb-4">일별 거래액 추이</h3>
                        <p className="text-sm text-gray-500 mb-4">💡 막대를 클릭하여 해당 날짜의 거래 내역을 조회하세요</p>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={dailyData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip formatter={(value) => `₩${value.toLocaleString()}`} />
                                <Bar dataKey="amount" fill="#3B82F6" onClick={handleBarClick} style={{ cursor: 'pointer' }} />
                            </BarChart>
                        </ResponsiveContainer>
                        {selectedDate && (<div className="mt-4 text-center"><span className="inline-block bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium">선택: {selectedDate} ✕</span></div>)}
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="border-b border-gray-200 px-6 py-4 bg-gray-50">
                        <h3 className="text-lg font-semibold text-gray-800">{getFilterText()}</h3>
                        <p className="text-sm text-gray-500 mt-1">총 {filteredTransactions.length}건 / 합계: ₩{filteredTransactions.reduce((sum, tx) => sum + tx.amount, 0).toLocaleString()}</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">No</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Transaction ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date/Time</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Merchant</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {filteredTransactions.map((tx, index) => (
                                    <tr key={tx.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 text-sm text-gray-900">{index + 1}</td>
                                        <td className="px-6 py-4 text-sm font-mono text-gray-700">{tx.id}</td>
                                        <td className="px-6 py-4 text-sm font-mono text-gray-500">{tx.userId}</td>
                                        <td className="px-6 py-4 text-sm text-gray-900">{tx.date} {tx.time}</td>
                                        <td className="px-6 py-4 text-sm text-gray-900">{tx.merchant}</td>
                                        <td className="px-6 py-4">
                                            <span className="inline-block px-3 py-1 text-xs font-semibold rounded-full" style={{ backgroundColor: (CATEGORY_COLORS[tx.category] || CATEGORY_COLORS['기타']) + '20', color: CATEGORY_COLORS[tx.category] || CATEGORY_COLORS['기타'] }}>{tx.category}</span>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-right font-medium text-gray-900">₩{tx.amount.toLocaleString()}</td>
                                        <td className="px-6 py-4 text-sm font-mono text-gray-500">{tx.ipAddress}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {filteredTransactions.length === 0 && (<div className="text-center py-12"><p className="text-gray-500">조건에 맞는 거래 내역이 없습니다.</p></div>)}
                </div>
            </div>
        </div>
    );
};

export default AdminIntegratedAnalysis;
