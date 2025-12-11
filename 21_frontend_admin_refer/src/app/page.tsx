"use client";

import { useState, useEffect } from 'react';

import { Users, ShoppingCart, DollarSign, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { DashboardStatCard } from '@/components/ui/DashboardStatCard';
import { CategoryTable } from '@/components/ui/CategoryTable';

// [왕초보 백엔드 연동 가이드]
// 1. 맨 위에 이 줄을 추가하세요: import { useState, useEffect } from 'react';
// 2. 아래의 'stats' 변수(여기부터 ]; 까지)를 모두 지우세요.
// 3. 지운 자리에 아래 코드를 복사해서 붙여넣으세요.
/*
const [stats, setStats] = useState([]);

useEffect(() => {
    // 백엔드에서 대시보드 통계 가져오기
    const fetchStats = async () => {
        try {
            const response = await fetch('/api/v1/dashboard/stats');
            const data = await response.json();
            setStats(data);
        } catch (error) {
            console.error('통계 데이터를 가져오는데 실패했습니다:', error);
        }
    };
    fetchStats();
}, []);
*/


// [왕초보 백엔드 연동 가이드]
// 1. 아래의 'lineData' 변수(여기부터 ]; 까지)를 모두 지우세요.
// 2. 지운 자리에 아래 코드를 복사해서 붙여넣으세요.
/*
const [lineData, setLineData] = useState([]);

useEffect(() => {
    // 백엔드에서 차트 데이터 가져오기
    const fetchChartData = async () => {
        try {
            const response = await fetch('/api/v1/dashboard/charts');
            const data = await response.json();
            setLineData(data.dailyTransactions); // 라인 차트 데이터 설정
            // setBarData(data.categoryConsumption); // 바 차트 데이터도 여기서 설정하면 좋아요
        } catch (error) {
            console.error('차트 데이터를 가져오는데 실패했습니다:', error);
        }
    };
    fetchChartData();
}, []);
*/




// 아이콘 매핑 객체
const iconMap: { [key: string]: any } = {
  Users: Users,
  ShoppingCart: ShoppingCart,
  DollarSign: DollarSign,
  TrendingUp: TrendingUp
};

export default function Dashboard() {
  const [stats, setStats] = useState([]);
  const [lineData, setLineData] = useState([]);
  const [barData, setBarData] = useState([]);
  const tableData: any[] = []; // TODO: 백엔드 API 연동 필요

  useEffect(() => {
    // 백엔드에서 대시보드 통계 가져오기
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/v1/dashboard/stats');
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error('통계 데이터를 가져오는데 실패했습니다:', error);
      }
    };
    fetchStats();
  }, []);

  useEffect(() => {
    // 백엔드에서 차트 데이터 가져오기
    const fetchChartData = async () => {
      try {
        const response = await fetch('/api/v1/dashboard/charts');
        const data = await response.json();
        setLineData(data.dailyTransactions); // 라인 차트 데이터 설정
        setBarData(data.categoryConsumption); // 바 차트 데이터 설정
      } catch (error) {
        console.error('차트 데이터를 가져오는데 실패했습니다:', error);
      }
    };
    fetchChartData();
  }, []);
  return (
    <div className="space-y-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-800">대시보드</h2>
        <p className="text-gray-500 mt-1">전체 서비스 현황을 한눈에 확인하세요</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat: any, index) => {
          const IconComponent = iconMap[stat.icon] || Users; // 기본값 Users
          return (
            <DashboardStatCard
              key={index}
              title={stat.title}
              value={stat.value}
              trend={stat.trend}
              icon={IconComponent}
              color={stat.color}
              trendColor={stat.trendColor}
            />
          );
        })}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Line Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-800 mb-6">일별 거래 추이</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar Chart */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold text-gray-800 mb-6">카테고리별 소비</h3>
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
        </div>
      </div>

      {/* Table */}
      <CategoryTable data={tableData} />
    </div>
  );
}
