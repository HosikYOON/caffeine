import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
    RefreshControl,
    ActivityIndicator
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import {
    getNotifications,
    getUnreadNotificationCount,
    markNotificationAsRead,
    markAllNotificationsAsRead
} from '../api/client';

export default function NotificationsScreen({ navigation }) {
    const { colors } = useTheme();
    const { user } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);

    const fetchNotifications = useCallback(async () => {
        if (!user?.id) return;

        try {
            const data = await getNotifications(user.id);
            setNotifications(data || []);

            const count = await getUnreadNotificationCount(user.id);
            setUnreadCount(count);
        } catch (error) {
            console.error('알림 로드 실패:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [user?.id]);

    useEffect(() => {
        fetchNotifications();
    }, [fetchNotifications]);

    const onRefresh = useCallback(() => {
        setRefreshing(true);
        fetchNotifications();
    }, [fetchNotifications]);

    const handleMarkAsRead = async (notificationId) => {
        try {
            await markNotificationAsRead(notificationId);
            setNotifications(prev =>
                prev.map(n =>
                    n.id === notificationId ? { ...n, is_read: true } : n
                )
            );
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error('알림 읽음 처리 실패:', error);
        }
    };

    const handleMarkAllAsRead = async () => {
        if (!user?.id) return;

        try {
            await markAllNotificationsAsRead(user.id);
            setNotifications(prev =>
                prev.map(n => ({ ...n, is_read: true }))
            );
            setUnreadCount(0);
            alert('✅ 모든 알림을 읽음 처리했습니다.');
        } catch (error) {
            console.error('전체 읽음 처리 실패:', error);
        }
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return '방금 전';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}일 전`;

        return date.toLocaleDateString('ko-KR', {
            month: 'short',
            day: 'numeric'
        });
    };

    const getTypeIcon = (type) => {
        switch (type) {
            case 'anomaly': return '⚠️';
            case 'promotion': return '🎁';
            case 'system': return '🔔';
            default: return '📬';
        }
    };

    if (loading) {
        return (
            <LinearGradient colors={colors.screenGradient} style={styles.container}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#2563EB" />
                    <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
                        알림을 불러오는 중...
                    </Text>
                </View>
            </LinearGradient>
        );
    }

    return (
        <LinearGradient colors={colors.screenGradient} style={styles.container}>
            {/* 헤더 */}
            <View style={styles.header}>
                <Text style={[styles.headerTitle, { color: colors.text }]}>
                    알림
                </Text>
                {unreadCount > 0 && (
                    <TouchableOpacity
                        style={styles.markAllButton}
                        onPress={handleMarkAllAsRead}
                    >
                        <Text style={styles.markAllText}>모두 읽음</Text>
                    </TouchableOpacity>
                )}
            </View>

            {/* 읽지 않은 알림 카운트 */}
            {unreadCount > 0 && (
                <View style={styles.unreadBadge}>
                    <Text style={styles.unreadText}>
                        📬 읽지 않은 알림 {unreadCount}개
                    </Text>
                </View>
            )}

            <ScrollView
                style={styles.scrollView}
                showsVerticalScrollIndicator={false}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={onRefresh}
                        tintColor="#2563EB"
                    />
                }
            >
                {notifications.length === 0 ? (
                    <View style={styles.emptyContainer}>
                        <Text style={styles.emptyIcon}>🔔</Text>
                        <Text style={[styles.emptyTitle, { color: colors.text }]}>
                            알림이 없습니다
                        </Text>
                        <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
                            새로운 알림이 도착하면 여기에 표시됩니다
                        </Text>
                    </View>
                ) : (
                    notifications.map((notification) => (
                        <TouchableOpacity
                            key={notification.id}
                            style={[
                                styles.notificationCard,
                                { backgroundColor: colors.cardBackground },
                                !notification.is_read && styles.unreadCard
                            ]}
                            onPress={() => handleMarkAsRead(notification.id)}
                            activeOpacity={0.7}
                        >
                            <View style={styles.notificationIcon}>
                                <Text style={styles.iconText}>
                                    {getTypeIcon(notification.type)}
                                </Text>
                            </View>
                            <View style={styles.notificationContent}>
                                <View style={styles.notificationHeader}>
                                    <Text style={[
                                        styles.notificationTitle,
                                        { color: colors.text },
                                        !notification.is_read && styles.unreadTitle
                                    ]}>
                                        {notification.title}
                                    </Text>
                                    {!notification.is_read && (
                                        <View style={styles.unreadDot} />
                                    )}
                                </View>
                                <Text
                                    style={[styles.notificationMessage, { color: colors.textSecondary }]}
                                    numberOfLines={2}
                                >
                                    {notification.message}
                                </Text>
                                <Text style={[styles.notificationTime, { color: colors.textSecondary }]}>
                                    {formatDate(notification.created_at)}
                                </Text>
                            </View>
                        </TouchableOpacity>
                    ))
                )}
                <View style={{ height: 100 }} />
            </ScrollView>
        </LinearGradient>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: 12,
        fontSize: 16,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingTop: 50,
        paddingBottom: 16,
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: '700',
    },
    markAllButton: {
        backgroundColor: '#2563EB',
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 20,
    },
    markAllText: {
        color: '#FFFFFF',
        fontSize: 14,
        fontWeight: '600',
    },
    unreadBadge: {
        marginHorizontal: 20,
        marginBottom: 16,
        backgroundColor: '#DBEAFE',
        padding: 12,
        borderRadius: 12,
    },
    unreadText: {
        color: '#1D4ED8',
        fontSize: 14,
        fontWeight: '600',
        textAlign: 'center',
    },
    scrollView: {
        flex: 1,
        paddingHorizontal: 20,
    },
    emptyContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingTop: 100,
    },
    emptyIcon: {
        fontSize: 64,
        marginBottom: 16,
    },
    emptyTitle: {
        fontSize: 20,
        fontWeight: '600',
        marginBottom: 8,
    },
    emptySubtitle: {
        fontSize: 14,
        textAlign: 'center',
    },
    notificationCard: {
        flexDirection: 'row',
        padding: 16,
        borderRadius: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 8,
        elevation: 2,
    },
    unreadCard: {
        borderLeftWidth: 4,
        borderLeftColor: '#2563EB',
    },
    notificationIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: '#F3F4F6',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 14,
    },
    iconText: {
        fontSize: 24,
    },
    notificationContent: {
        flex: 1,
    },
    notificationHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 4,
    },
    notificationTitle: {
        fontSize: 16,
        fontWeight: '500',
        flex: 1,
    },
    unreadTitle: {
        fontWeight: '700',
    },
    unreadDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#2563EB',
        marginLeft: 8,
    },
    notificationMessage: {
        fontSize: 14,
        lineHeight: 20,
        marginBottom: 6,
    },
    notificationTime: {
        fontSize: 12,
    },
});
