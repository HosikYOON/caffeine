// User Management Page
"use client";

import { useState, useEffect } from 'react';
import { Users, Search, UserCheck, UserPlus, Shield, X } from 'lucide-react';
import { getUsers, getUserStats, deleteUser } from '@/api/client';
import type { User, UserStats } from '@/types/types';

export default function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [stats, setStats] = useState<UserStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [showModal, setShowModal] = useState(false);

    // Load users and stats on mount
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [usersData, statsData] = await Promise.all([
                getUsers(),
                getUserStats()
            ]);
            setUsers(usersData);
            setStats(statsData);
        } catch (error) {
            console.error('Failed to load users:', error);
        } finally {
            setLoading(false);
        }
    };

    // Filter users by search term
    const filteredUsers = users.filter(user =>
        user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const handleViewDetails = (user: User) => {
        setSelectedUser(user);
        setShowModal(true);
    };

    const handleDeleteUser = async (userId: number) => {
        if (!confirm('정말로 이 사용자를 삭제하시겠습니까?')) return;

        try {
            await deleteUser(userId);
            await loadData(); // Reload data
        } catch (error) {
            console.error('Failed to delete user:', error);
            alert('사용자 삭제에 실패했습니다.');
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('ko-KR');
    };

    return (
        <div className="p-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-100 mb-2">사용자 관리</h1>
                <p className="text-gray-400">전체 사용자 목록 및 관리</p>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <Users className="w-8 h-8 text-blue-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{stats.total_users}</div>
                        <div className="text-sm text-gray-400">전체 사용자</div>
                    </div>

                    <div className="bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <UserCheck className="w-8 h-8 text-green-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{stats.active_users}</div>
                        <div className="text-sm text-gray-400">활성 사용자</div>
                    </div>

                    <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <UserPlus className="w-8 h-8 text-purple-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{stats.new_users_this_month}</div>
                        <div className="text-sm text-gray-400">이번 달 신규</div>
                    </div>

                    <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-2">
                            <Shield className="w-8 h-8 text-orange-400" />
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">{stats.admin_users}</div>
                        <div className="text-sm text-gray-400">관리자</div>
                    </div>
                </div>
            )}

            {/* Search Bar */}
            <div className="mb-6">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
                    <input
                        type="text"
                        placeholder="이름 또는 이메일로 검색..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
            </div>

            {/* Users Table */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-900 border-b border-gray-700">
                        <tr>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">ID</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">이메일</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">이름</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">역할</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">상태</th>
                            <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">가입일</th>
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
                        ) : filteredUsers.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                                    사용자가 없습니다.
                                </td>
                            </tr>
                        ) : (
                            filteredUsers.map((user) => (
                                <tr key={user.id} className="hover:bg-gray-700/50 transition-colors">
                                    <td className="px-6 py-4 text-sm text-gray-300">{user.id}</td>
                                    <td className="px-6 py-4 text-sm text-gray-300">{user.email}</td>
                                    <td className="px-6 py-4 text-sm text-white font-medium">{user.name}</td>
                                    <td className="px-6 py-4 text-sm">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${user.role === 'ADMIN' ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'
                                            }`}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${user.status === 'ACTIVE' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                                            }`}>
                                            {user.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-400">{formatDate(user.created_at)}</td>
                                    <td className="px-6 py-4 text-sm">
                                        <button
                                            onClick={() => handleViewDetails(user)}
                                            className="text-blue-400 hover:text-blue-300 mr-3 transition-colors"
                                        >
                                            상세보기
                                        </button>
                                        <button
                                            onClick={() => handleDeleteUser(user.id)}
                                            className="text-red-400 hover:text-red-300 transition-colors"
                                        >
                                            삭제
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* User Detail Modal */}
            {showModal && selectedUser && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-800 border border-gray-700 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-6 border-b border-gray-700">
                            <h2 className="text-2xl font-bold text-white">사용자 상세 정보</h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="text-gray-400 hover:text-white transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 space-y-6">
                            {/* Personal Information */}
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-4">개인 정보</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">이메일</p>
                                        <p className="text-white">{selectedUser.email}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">이름</p>
                                        <p className="text-white">{selectedUser.name}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">닉네임</p>
                                        <p className="text-white">{selectedUser.nickname || '-'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">전화번호</p>
                                        <p className="text-white">{selectedUser.phone || '-'}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Account Information */}
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-4">계정 정보</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">사용자 ID</p>
                                        <p className="text-white">{selectedUser.id}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">역할</p>
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${selectedUser.role === 'ADMIN' ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'
                                            }`}>
                                            {selectedUser.role}
                                        </span>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">그룹 ID</p>
                                        <p className="text-white">{selectedUser.group_id || '-'}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">상태</p>
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${selectedUser.status === 'ACTIVE' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                                            }`}>
                                            {selectedUser.status}
                                        </span>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">가입일</p>
                                        <p className="text-white">{formatDate(selectedUser.created_at)}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">최종 수정일</p>
                                        <p className="text-white">{formatDate(selectedUser.updated_at)}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-400 mb-1">마지막 로그인</p>
                                        <p className="text-white">{selectedUser.last_login_at ? formatDate(selectedUser.last_login_at) : '-'}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Social Login */}
                            {selectedUser.social_provider && (
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-4">소셜 로그인</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <p className="text-sm text-gray-400 mb-1">제공자</p>
                                            <p className="text-white">{selectedUser.social_provider}</p>
                                        </div>
                                        <div>
                                            <p className="text-sm text-gray-400 mb-1">소셜 ID</p>
                                            <p className="text-white">{selectedUser.social_id}</p>
                                        </div>
                                    </div>
                                </div>
                            )}
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
