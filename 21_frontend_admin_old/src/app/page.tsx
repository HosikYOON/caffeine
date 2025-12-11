"use client";

import { useState, useEffect } from 'react';
import { Users, ShoppingCart, DollarSign, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { DashboardStatCard } from '@/components/ui/DashboardStatCard';
import { CategoryTable } from '@/components/ui/CategoryTable';
import { getFullAnalysis, getMonthlyTrend, getTransactionStats } from '@/api/services';

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

      // 전체 분석 데이터 가져오기
      const analysis = await getFullAnalysis();
      setDataSource(analysis.data_source || 'DB');

      // 통계 카드 데이터 설정
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

      // 월별 추이 데이터 (라인 차트)
      const monthlyTrend = analysis.monthly_trend || [];
      const lineChartData = monthlyTrend.map(item => ({
        name: item.month.split('-')[1] + '월',
        value: Math.round(item.total_amount / 10000), // 만원 단위
      }));
      setLineData(lineChartData);

      // 카테고리별 소비 (바 차트)
      const categories = analysis.category_breakdown || [];
      const barChartData = categories.map(item => ({
        name: item.category,
        value: Math.round(item.total_amount / 10000), // 만원 단위
      }));
      setBarData(barChartData);

      // 카테고리별 테이블 데이터
      const totalAmount = categories.reduce((sum, cat) => sum + cat.total_amount, 0);
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

      // 오류 시 Mock 데이터 표시
      setStats([
        { title: '전체 사용자', value: '데이터 로드 실패', trend: 'API 연결 확인 필요', icon: Users, color: 'text-blue-600', trendColor: 'text-red-500' },
      ]);
      setDataSource('[ERROR]');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">대시보드</h2>
            <p className="text-gray-500 mt-1">전체 서비스 현황을 한눈에 확인하세요</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-sm px-3 py-1 rounded-full ${dataSource.includes('DB') ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
              }`}>
              {dataSource.includes('DB') ? '🟢 실시간 DB' : '🟡 ' + dataSource}
            </span>
            <button
              onClick={fetchDashboardData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              새로고침
            </button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <DashboardStatCard
            key={index}
            title={stat.title}
            value={stat.value}
            trend={stat.trend}
            icon={stat.icon}
            color={stat.color}
            trendColor={stat.trendColor}
          />
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Line Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-800 mb-6">월별 거래 추이</h3>
          {lineData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400">
              데이터가 없습니다
            </div>
          )}
          <p className="text-xs text-gray-400 mt-2 text-center">단위: 만원</p>
        </div>

        {/* Bar Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-800 mb-6">카테고리별 소비</h3>
          {barData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#1e293b" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-400">
              데이터가 없습니다
            </div>
          )}
          <p className="text-xs text-gray-400 mt-2 text-center">단위: 만원</p>
        </div>
      </div>

      {/* Table */}
      {tableData.length > 0 && <CategoryTable data={tableData} />}
    </div>
  );
}
