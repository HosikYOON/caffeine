// Transaction Management Page
"use client";

import { useState, useEffect } from 'react';
import { CreditCard, Search, DollarSign, TrendingUp, Calendar, Filter, ChevronLeft, ChevronRight, X, Edit } from 'lucide-react';
import { getTransactions, getTransactionStats, getTransactionById, updateTransactionNote } from '@/api/client';
import type { Transaction, TransactionStats, TransactionListResponse } from '@/types/types';

export default function TransactionsPage() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [stats, setStats] = useState<TransactionStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(20);
    const [total, setTotal] = useState(0);
    const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
    const [showModal, setShowModal] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    const [editingNote, setEditingNote] = useState(false);
    const [noteValue, setNoteValue] = useState('');

    // Filters
    const [filters, setFilters] = useState({
        search: '',
        category: '',
        start_date: '',
        end_date: '',
        min_amount: '',
        max_amount: '',
    });

    // Load transactions and stats on mount and filter changes
    useEffect(() => {
        loadData();
    }, [page, filters]);

    const loadData = async () => {
        setLoading(true);
        try {
            const filterParams = {
                ...filters,
                min_amount: filters.min_amount ? parseFloat(filters.min_amount) : undefined,
                max_amount: filters.max_amount ? parseFloat(filters.max_amount) : undefined,
            };

            const [transactionData, statsData] = await Promise.all([
                getTransactions(filterParams, page, pageSize),
                getTransactionStats()
            ]);

            setTransactions(transactionData.transactions);
            setTotal(transactionData.total);
            setStats(statsData.stats);
        } catch (error) {
            console.error('Failed to load transactions:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleViewDetails = async (transaction: Transaction) => {
        setSelectedTransaction(transaction);
        setNoteValue(transaction.description || '');
        setShowModal(true);
        setEditingNote(false);
    };

    const handleSaveNote = async () => {
        if (!selectedTransaction) return;

        try {
            await updateTransactionNote(selectedTransaction.id, noteValue);
            setEditingNote(false);
            await loadData(); // Reload data
            // Update selected transaction
            setSelectedTransaction({
                ...selectedTransaction,
                description: noteValue
            });
        } catch (error) {
            console.error('Failed to update note:', error);
            alert('메모 수정에 실패했습니다.');
        }
    };

    const handleFilterChange = (key: string, value: string) => {
        setFilters(prev => ({ ...prev, [key]: value }));
        setPage(1); // Reset to first page
    };

    const clearFilters = () => {
        setFilters({
            search: '',
            category: '',
            start_date: '',
            end_date: '',
            min_amount: '',
            max_amount: '',
        });
        setPage(1);
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: 'KRW'
        }).format(amount);
    };

    const formatDateTime = (dateString: string) => {
        return new Date(dateString).toLocaleString('ko-KR');
    };

    const totalPages = Math.ceil(total / pageSize);

    return (
        <div className="p-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-100 mb-2">거래 관리</h1>
                <p className="text-gray-400">전체 거래 내역 및 관리</p>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <CreditCard className="w-8 h-8 text-blue-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{stats.transaction_count}</div>
                        <div className="text-sm text-gray-400">전체 거래</div>
                    </div>

                    <div className="bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <DollarSign className="w-8 h-8 text-green-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{formatCurrency(stats.total_amount)}</div>
                        <div className="text-sm text-gray-400">총 거래액</div>
                    </div>

                    <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <TrendingUp className="w-8 h-8 text-purple-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{formatCurrency(stats.average_amount)}</div>
                        <div className="text-sm text-gray-400">평균 거래액</div>
                    </div>

                    <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <Calendar className="w-8 h-8 text-orange-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{transactions.length}</div>
                        <div className="text-sm text-gray-400">현재 페이지</div>
                    </div>
                </div>
            )}

            {/* Filter Toggle and Search */}
            <div className="mb-6 flex gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
                    <input
                        type="text"
                        placeholder="가맹점명 또는 메모로 검색..."
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={`px-6 py-3 rounded-lg transition-colors flex items-center gap-2 ${showFilters ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                        }`}
                >
                    <Filter className="w-5 h-5" />
                    필터
                </button>
            </div>

            {/* Advanced Filters */}
            {showFilters && (
                <div className="mb-6 p-6 bg-gray-800 border border-gray-700 rounded-lg">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">시작 날짜</label>
                            <input
                                type="date"
                                value={filters.start_date}
                                onChange={(e) => handleFilterChange('start_date', e.target.value)}
                                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">종료 날짜</label>
                            <input
                                type="date"
                                value={filters.end_date}
                                onChange={(e) => handleFilterChange('end_date', e.target.value)}
                                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">카테고리</label>
                            <input
                                type="text"
                                placeholder="예: 외식, 교통"
                                value={filters.category}
                                onChange={(e) => handleFilterChange('category', e.target.value)}
                                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">최소 금액</label>
                            <input
                                type="number"
                                placeholder="0"
                                value={filters.min_amount}
                                onChange={(e) => handleFilterChange('min_amount', e.target.value)}
                                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">최대 금액</label>
                            <input
                                type="number"
                                placeholder="1000000"
                                value={filters.max_amount}
                                onChange={(e) => handleFilterChange('max_amount', e.target.value)}
                                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div className="flex items-end">
                            <button
                                onClick={clearFilters}
                                className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                            >
                                필터 초기화
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Transactions Table */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden mb-6">
                <table className="w-full">
                    <thead className="bg-gray-900 border-b border-gray-700">
                        <tr>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">ID</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">날짜 & 시간</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">가맹점</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">카테고리</th>
                            <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">금액</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">상태</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">작업</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {loading ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                                    로딩 중...
                                </td>
                            </tr>
                        ) : transactions.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                                    거래 내역이 없습니다.
                                </td>
                            </tr>
                        ) : (
                            transactions.map((tx) => (
                                <tr key={tx.id} className="hover:bg-gray-700/50 transition-colors">
                                    <td className="px-6 py-4 text-sm text-gray-300">{tx.id}</td>
                                    <td className="px-6 py-4 text-sm text-gray-300">{formatDateTime(tx.transaction_date)}</td>
                                    <td className="px-6 py-4 text-sm text-white font-medium">{tx.merchant}</td>
                                    <td className="px-6 py-4 text-sm">
                                        <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-medium">
                                            {tx.category}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-right text-white font-semibold">
                                        {formatCurrency(tx.amount)}
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${tx.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                                            }`}>
                                            {tx.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        <button
                                            onClick={() => handleViewDetails(tx)}
                                            className="text-blue-400 hover:text-blue-300 transition-colors"
                                        >
                                            상세보기
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between">
                <div className="text-sm text-gray-400">
                    총 {total}개 중 {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, total)}개 표시
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition-colors"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-white">
                        페이지 {page} / {totalPages}
                    </span>
                    <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700 transition-colors"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* Transaction Detail Modal */}
            {showModal && selectedTransaction && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-800 border border-gray-700 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-6 border-b border-gray-700">
                            <h2 className="text-2xl font-bold text-white">거래 상세 정보</h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="text-gray-400 hover:text-white transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-sm text-gray-400 mb-1">거래 ID</p>
                                    <p className="text-white font-mono">{selectedTransaction.id}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-400 mb-1">거래 시간</p>
                                    <p className="text-white">{formatDateTime(selectedTransaction.transaction_date)}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-400 mb-1">가맹점</p>
                                    <p className="text-white font-medium">{selectedTransaction.merchant}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-400 mb-1">카테고리</p>
                                    <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-medium">
                                        {selectedTransaction.category}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-400 mb-1">금액</p>
                                    <p className="text-2xl text-white font-bold">{formatCurrency(selectedTransaction.amount)}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-400 mb-1">통화</p>
                                    <p className="text-white">{selectedTransaction.currency}</p>
                                </div>
                                <div className="col-span-2">
                                    <p className="text-sm text-gray-400 mb-1">상태</p>
                                    <span className={`px-2 py-1 rounded text-xs font-medium ${selectedTransaction.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                                        }`}>
                                        {selectedTransaction.status}
                                    </span>
                                </div>
                            </div>

                            {/* Description/Note Section */}
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <p className="text-sm text-gray-400">메모</p>
                                    {!editingNote && (
                                        <button
                                            onClick={() => setEditingNote(true)}
                                            className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                                        >
                                            <Edit className="w-4 h-4" />
                                            수정
                                        </button>
                                    )}
                                </div>
                                {editingNote ? (
                                    <div className="space-y-2">
                                        <textarea
                                            value={noteValue}
                                            onChange={(e) => setNoteValue(e.target.value)}
                                            className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            rows={3}
                                        />
                                        <div className="flex gap-2">
                                            <button
                                                onClick={handleSaveNote}
                                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                                            >
                                                저장
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setEditingNote(false);
                                                    setNoteValue(selectedTransaction.description || '');
                                                }}
                                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                                            >
                                                취소
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-white bg-gray-900 p-3 rounded">
                                        {selectedTransaction.description || '메모가 없습니다.'}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="p-6 border-t border-gray-700 flex justify-end">
                            <button
                                onClick={() => setShowModal(false)}
                                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                            >
                                닫기
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
