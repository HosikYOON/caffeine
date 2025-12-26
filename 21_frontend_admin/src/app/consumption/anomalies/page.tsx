"use client";

import React, { useState, useEffect, MouseEvent } from 'react';
import {
    AlertTriangle, CheckCircle, XCircle, Clock, ChevronRight,
    RotateCcw, Eye, ExternalLink, User, X,
    ShieldCheck, ShieldAlert, Info
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { AnomalyData } from '@/types';
import { AnomalySummaryCard } from '@/components/ui/AnomalySummaryCard';
import { getAnomalies, approveAnomaly, rejectAnomaly, resetAnomaly } from '@/api/client';

export default function AnomaliesPage() {
    const router = useRouter();
    // =========================================================================================
    // [백엔드 연동 가이드 - 완료]
    // Backend API (/api/anomalies)와 연결되어 실제 데이터를 가져옵니다.
    // =========================================================================================
    const [anomalies, setAnomalies] = useState<AnomalyData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyData | null>(null);

    useEffect(() => {
        fetchAnomalies();
    }, []);

    /**
     * Backend API에서 이상 거래 데이터를 가져오는 함수
     */
    const fetchAnomalies = async () => {
        try {
            setIsLoading(true);
            const data = await getAnomalies('all'); // Backend API 직접 호출 (All statuses)
            if (data === null) {
                // 401 Unauthorized - silence and keep empty state (or show login message)
                setAnomalies([]);
                console.log('ℹ️ Unauthorized access - showing empty state');
                return;
            }
            setAnomalies(data);
            console.log('✅ Anomaly 데이터 로드 완료:', data.length, '건');
        } catch (error: any) {
            console.error('❌ Anomaly 데이터 로드 실패:', error);
            setAnomalies([]);
        } finally {
            setIsLoading(false);
        }
    };

    // =========================================================================================
    // [데이터 요약 계산]
    // 백엔드에서 받아온 데이터를 기반으로 화면에 표시할 요약 정보를 계산합니다.
    // =========================================================================================
    const pendingCount = anomalies.filter((a: AnomalyData) => a.status === 'pending').length;
    const approvedCount = anomalies.filter((a: AnomalyData) => a.status === 'approved').length;
    const rejectedCount = anomalies.filter((a: AnomalyData) => a.status === 'rejected').length;

    // 위험 금액 합계 계산 (모든 이상 거래의 금액 합계)
    const totalRiskAmount = anomalies.reduce((sum: number, item: AnomalyData) => sum + item.amount, 0);

    const getRiskBadge = (level: string) => {
        switch (level) {
            case '위험': return 'bg-red-100 text-red-800';
            case '경고': return 'bg-yellow-100 text-yellow-800';
            case '주의': return 'bg-blue-100 text-blue-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    // =========================================================================================
    // [백엔드 연동 가이드 - 승인/거부/재검토 처리]
    // 각 버튼을 클릭했을 때 실행될 함수들입니다.
    // =========================================================================================

    // 승인 처리 함수
    const handleApprove = async (id: number) => {
        try {
            const result = await approveAnomaly(id);
            if (result === null) {
                alert('승인 권한이 없거나 세션이 만료되었습니다. 다시 로그인해주세요.');
                return;
            }
            alert('정상 승인되었습니다.');
            if (selectedAnomaly && selectedAnomaly.id === id) setSelectedAnomaly(null);
            await fetchAnomalies(); // 목록 새로고침
        } catch (error: any) {
            console.error('승인 실패:', error);
            alert('처리에 실패했습니다.');
        }
    };

    // 거부 처리 함수
    const handleReject = async (id: number) => {
        try {
            const result = await rejectAnomaly(id);
            if (result === null) {
                alert('거부 권한이 없거나 세션이 만료되었습니다. 다시 로그인해주세요.');
                return;
            }
            alert('거부되었습니다.');
            if (selectedAnomaly && selectedAnomaly.id === id) setSelectedAnomaly(null);
            await fetchAnomalies(); // 목록 새로고침
        } catch (error: any) {
            console.error('거부 실패:', error);
            alert('처리에 실패했습니다.');
        }
    };

    // 재검토(Reset) 처리 함수
    const handleReset = async (id: number) => {
        if (!confirm('해당 내역을 다시 대기 상태로 되돌리시겠습니까?')) return;
        try {
            const result = await resetAnomaly(id);
            if (result === null) {
                alert('재검토 권한이 없거나 세션이 만료되었습니다. 다시 로그인해주세요.');
                return;
            }
            alert('대기 상태로 전환되었습니다.');
            if (selectedAnomaly && selectedAnomaly.id === id) setSelectedAnomaly(null);
            await fetchAnomalies(); // 목록 새로고침
        } catch (error: any) {
            console.error('재검토 실패:', error);
            alert('처리에 실패했습니다.');
        }
    };

    const navigateToUser = (userId: string) => {
        // userId format might be "user_123"
        const cleanId = userId.replace('user_', '');
        router.push(`/users?search=${cleanId}`);
    };

    return (
        <div className="space-y-6">
            <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-800">이상 거래 탐지</h2>
                <p className="text-gray-500 mt-1">실시간으로 감지된 이상 거래를 모니터링하고 관리합니다</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <AnomalySummaryCard
                    title="대기 중인 알림"
                    value={`${pendingCount}건`}
                    icon={Clock}
                    iconColor="text-yellow-600"
                    iconBgColor="bg-yellow-50"
                />
                <AnomalySummaryCard
                    title="금일 처리 완료"
                    value={`${approvedCount + rejectedCount}건`}
                    icon={CheckCircle}
                    iconColor="text-green-600"
                    iconBgColor="bg-green-50"
                />
                <AnomalySummaryCard
                    title="탐지된 위험 금액"
                    value={`₩${(totalRiskAmount / 10000).toFixed(1)}만`}
                    icon={AlertTriangle}
                    iconColor="text-red-600"
                    iconBgColor="bg-red-50"
                />
            </div>

            {/* Pending Anomalies List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                    <h3 className="text-lg font-bold text-gray-800">대기 중인 이상 거래</h3>
                    <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-xs font-medium">
                        {pendingCount}건의 검토 필요 항목
                    </span>
                </div>

                {isLoading ? (
                    <div className="p-12 text-center text-gray-500">
                        데이터를 불러오는 중입니다...
                    </div>
                ) : anomalies.filter((a: AnomalyData) => a.status === 'pending').length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                        대기 중인 이상 거래가 없습니다.
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {anomalies.filter((a: AnomalyData) => a.status === 'pending').map((anomaly: AnomalyData) => (
                            <div key={anomaly.id} className="p-6 hover:bg-gray-50 transition-colors">
                                <div className="flex items-start justify-between">
                                    <div className="flex gap-4">
                                        <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${anomaly.riskLevel === '위험' ? 'bg-red-100' : anomaly.riskLevel === '경고' ? 'bg-yellow-100' : 'bg-blue-100'
                                            }`}>
                                            <AlertTriangle className={`w-6 h-6 ${anomaly.riskLevel === '위험' ? 'text-red-600' : anomaly.riskLevel === '경고' ? 'text-yellow-600' : 'text-blue-600'
                                                }`} />
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getRiskBadge(anomaly.riskLevel)}`}>
                                                    {anomaly.riskLevel}
                                                </span>
                                                <h4 className="text-base font-bold text-gray-800">{anomaly.category}</h4>
                                                <span className="text-sm text-gray-500">• {anomaly.date}</span>
                                            </div>
                                            <p className="text-2xl font-bold text-gray-900 mb-2">₩{anomaly.amount.toLocaleString()}</p>
                                            <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                                                <span className="font-medium">의심 사유:</span>
                                                {anomaly.reason}
                                            </div>
                                            <div className="flex items-center gap-2 mt-2">
                                                <p className="text-sm text-gray-500">
                                                    사용자: <span className="font-medium text-gray-700">{anomaly.userName}</span> ({anomaly.userId})
                                                </p>
                                                <button
                                                    onClick={(e: React.MouseEvent) => { e.stopPropagation(); navigateToUser(anomaly.userId); }}
                                                    className="p-1 text-blue-500 hover:bg-blue-50 rounded-full transition-colors"
                                                    title="사용자 정보 보기"
                                                >
                                                    <ExternalLink className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setSelectedAnomaly(anomaly)}
                                            className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 font-medium text-sm transition-colors flex items-center gap-2">
                                            <Eye className="w-4 h-4" />
                                            상세 보기
                                        </button>
                                        <button
                                            onClick={() => handleReject(anomaly.id)}
                                            className="px-4 py-2 bg-red-50 text-red-600 border border-red-100 rounded-lg hover:bg-red-100 font-medium text-sm transition-colors">
                                            거부
                                        </button>
                                        <button
                                            onClick={() => handleApprove(anomaly.id)}
                                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition-colors shadow-sm">
                                            정상 승인
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Processed History */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-6 border-b border-gray-100 flex justify-between items-center text-gray-800">
                    <h3 className="text-lg font-bold">최근 처리 내역</h3>
                    <div className="flex gap-4">
                        <div className="flex items-center gap-1.5 text-xs">
                            <span className="w-2 h-2 rounded-full bg-green-500"></span>
                            <span className="text-gray-500">승인 {approvedCount}건</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs">
                            <span className="w-2 h-2 rounded-full bg-red-500"></span>
                            <span className="text-gray-500">거부 {rejectedCount}건</span>
                        </div>
                    </div>
                </div>
                <div className="divide-y divide-gray-100">
                    {anomalies.filter((a: AnomalyData) => a.status !== 'pending').length === 0 ? (
                        <div className="p-12 text-center text-gray-500 text-sm">
                            <Info className="w-8 h-8 mx-auto mb-2 opacity-20" />
                            처리된 내역이 없습니다.
                        </div>
                    ) : (
                        anomalies.filter((a: AnomalyData) => a.status !== 'pending').map((anomaly: AnomalyData) => (
                            <div
                                key={anomaly.id}
                                className="group p-4 flex items-center justify-between hover:bg-blue-50/30 transition-all cursor-pointer"
                                onClick={() => setSelectedAnomaly(anomaly)}
                            >
                                <div className="flex items-center gap-4">
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${anomaly.status === 'approved' ? 'bg-green-100' : 'bg-red-100'
                                        }`}>
                                        {anomaly.status === 'approved' ? (
                                            <CheckCircle className="w-5 h-5 text-green-600" />
                                        ) : (
                                            <XCircle className="w-5 h-5 text-red-600" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-gray-800">
                                            {anomaly.category}
                                            <span className="ml-2 font-normal text-gray-600">₩{anomaly.amount.toLocaleString()}</span>
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {anomaly.date} • {anomaly.userName}
                                            <span className="ml-2 px-1.5 py-0.5 bg-gray-100 rounded text-[10px] uppercase">{anomaly.userId}</span>
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    {/* Action Buttons visible on hover */}
                                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleReset(anomaly.id); }}
                                            className="p-1.5 bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
                                            title="재검토 요청 (대기로 변경)"
                                        >
                                            <RotateCcw className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={(e: React.MouseEvent) => { e.stopPropagation(); setSelectedAnomaly(anomaly); }}
                                            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-xs font-medium transition-colors"
                                        >
                                            상세
                                        </button>
                                    </div>

                                    <span className={`min-w-[80px] text-center px-2 py-1 rounded-full text-xs font-bold ${anomaly.status === 'approved' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                                        }`}>
                                        {anomaly.status === 'approved' ? '정상 승인됨' : '거부됨'}
                                    </span>
                                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Anomaly Detail Modal */}
            {selectedAnomaly && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                            <h3 className="text-xl font-bold text-gray-800">이상 거래 상세 정보</h3>
                            <button onClick={() => setSelectedAnomaly(null)} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                                <X className="w-5 h-5 text-gray-500" />
                            </button>
                        </div>

                        <div className="p-8 space-y-6">
                            {/* Header Status */}
                            <div className="flex items-center gap-4 p-4 rounded-xl bg-gray-50">
                                <div className={`w-14 h-14 rounded-full flex items-center justify-center ${selectedAnomaly.riskLevel === '위험' ? 'bg-red-100' :
                                    selectedAnomaly.riskLevel === '경고' ? 'bg-yellow-100' : 'bg-blue-100'
                                    }`}>
                                    <AlertTriangle className={`w-8 h-8 ${selectedAnomaly.riskLevel === '위험' ? 'text-red-600' :
                                        selectedAnomaly.riskLevel === '경고' ? 'text-yellow-600' : 'text-blue-600'
                                        }`} />
                                </div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${getRiskBadge(selectedAnomaly.riskLevel)}`}>
                                            {selectedAnomaly.riskLevel}
                                        </span>
                                        {selectedAnomaly.status !== 'pending' && (
                                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${selectedAnomaly.status === 'approved' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                                }`}>
                                                {selectedAnomaly.status === 'approved' ? '처리 완료: 정상 승인' : '처리 완료: 거부'}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-2xl font-black text-gray-900 mt-1">₩{selectedAnomaly.amount.toLocaleString()}</p>
                                </div>
                            </div>

                            {/* Details Grid */}
                            <div className="grid grid-cols-2 gap-6">
                                <div>
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">카테고리</p>
                                    <p className="text-base font-bold text-gray-800">{selectedAnomaly.category}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">거래 일시</p>
                                    <p className="text-base font-bold text-gray-800">{selectedAnomaly.date}</p>
                                </div>
                                <div className="col-span-2">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">탐지 사유</p>
                                    <p className="text-base font-medium text-gray-700 bg-red-50 border border-red-100 p-3 rounded-lg">
                                        {selectedAnomaly.reason}
                                    </p>
                                </div>
                                <div className="col-span-2">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">사용자 정보</p>
                                    <div className="flex items-center justify-between p-3 border border-gray-100 rounded-lg group">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center font-bold text-sm">
                                                {selectedAnomaly.userName[0]}
                                            </div>
                                            <div>
                                                <p className="text-sm font-bold text-gray-800">{selectedAnomaly.userName}</p>
                                                <p className="text-xs text-gray-500">{selectedAnomaly.userId}</p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => navigateToUser(selectedAnomaly.userId)}
                                            className="text-xs font-bold text-blue-600 hover:underline flex items-center gap-1"
                                        >
                                            관리 <ExternalLink className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Footer Actions */}
                        <div className="p-6 bg-gray-50 border-t border-gray-100 flex gap-3">
                            {selectedAnomaly.status === 'pending' ? (
                                <>
                                    <button
                                        onClick={() => handleReject(selectedAnomaly.id)}
                                        className="flex-1 py-3 bg-white border border-red-200 text-red-600 rounded-xl hover:bg-red-50 font-bold transition-colors"
                                    >
                                        의심 거래 거부
                                    </button>
                                    <button
                                        onClick={() => handleApprove(selectedAnomaly.id)}
                                        className="flex-1 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-bold shadow-lg shadow-blue-200 transition-colors"
                                    >
                                        정상 거래로 승인
                                    </button>
                                </>
                            ) : (
                                <button
                                    onClick={() => handleReset(selectedAnomaly.id)}
                                    className="w-full py-3 bg-white border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-bold flex items-center justify-center gap-2 transition-colors"
                                >
                                    <RotateCcw className="w-4 h-4" />
                                    대기 상태로 되돌리기 (재검토)
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
