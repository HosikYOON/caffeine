import React, { useState } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity, TextInput, ScrollView } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { formatCurrency } from '../utils/currency';
import EmptyState from '../components/EmptyState';
import { EMPTY_MESSAGES } from '../constants';

// ============================================================
// TODO: 백엔드 연결 시 수정 필요
// ============================================================
// 현재는 MOCK 쿠폰 데이터를 사용하고 있습니다.
// 백엔드 API 연결 시 이 데이터를 실제 API 호출로 교체하세요.
//
// 백엔드 API 엔드포인트 예시:
// - GET /api/coupons - 사용자의 전체 쿠폰 목록
//   Response: { coupons: [...] }
//
// - POST /api/coupons/{id}/use - 쿠폰 사용
//   Request: { merchantId, discount }
//   Response: { success, qrCode, barcode, usedDate }
//
// - GET /api/coupons/available - 사용 가능한 쿠폰만
//   Response: { coupons: [...] }
//
// - POST /api/coupons/issue - AI 예측 기반 자동 쿠폰 발급
//   Request: { merchantId, triggeredBy: 'banner' | 'prediction' }
//   Response: { coupon, message }
//
// useEffect에서 API 호출 예시:
// useEffect(() => {
//     const fetchCoupons = async () => {
//         try {
//             const token = await AsyncStorage.getItem('authToken');
//             const response = await fetch(`${API_BASE_URL}/coupons`, {
//                 headers: { 'Authorization': `Bearer ${token}` }
//             });
//             const data = await response.json();
//             
//             // ⚠️ 중요: 백엔드에서 daysLeft를 제공하지 않는 경우 계산 필요
//             const couponsWithDaysLeft = data.coupons.map(coupon => ({
//                 ...coupon,
//                 daysLeft: coupon.status === 'available' 
//                     ? calculateDaysLeft(coupon.expiryDate) 
//                     : undefined
//             }));
//             
//             setCoupons(couponsWithDaysLeft);
//         } catch (error) {
//             console.error('쿠폰 로드 실패:', error);
//         }
//     };
//     fetchCoupons();
// }, []);
// ============================================================

// Helper Function: 만료일까지 남은 일수 계산
const calculateDaysLeft = (expiryDate) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0); // 시간 부분 제거 (날짜만 비교)

    const expiry = new Date(expiryDate);
    expiry.setHours(0, 0, 0, 0);

    const diffTime = expiry - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    return Math.max(0, diffDays); // 음수 방지
};


const MOCK_COUPONS = [
    {
        id: 1,
        merchant: '스타벅스',
        icon: '', // TODO: 아이콘 추가 (이모지 또는 이미지 URL)
        discount: 2000,
        category: '식비',
        expiryDate: '2024-12-15',
        status: 'available',
        description: 'AI 예측 기반 자동 발급',
        minPurchase: 10000,
        daysLeft: 14
    },
    {
        id: 2,
        merchant: 'GS25',
        icon: '', // TODO: 아이콘 추가
        discount: 1000,
        category: '편의점',
        expiryDate: '2024-12-05',
        status: 'available',
        description: '거래 100건 달성 보너스',
        minPurchase: 5000,
        daysLeft: 4
    },
    {
        id: 3,
        merchant: '올리브영',
        icon: '', // TODO: 아이콘 추가
        discount: 5000,
        category: '쇼핑',
        expiryDate: '2024-12-20',
        status: 'available',
        description: '이번 달 쇼핑 카테고리 1위',
        minPurchase: 30000,
        daysLeft: 19
    },
    {
        id: 4,
        merchant: 'CGV',
        icon: '', // TODO: 아이콘 추가
        discount: 3000,
        category: '여가',
        expiryDate: '2024-12-03',
        status: 'available',
        description: '주말 특가 쿠폰',
        minPurchase: 15000,
        daysLeft: 2
    },
    {
        id: 5,
        merchant: '맥도날드',
        icon: '', // TODO: 아이콘 추가
        discount: 3000,
        category: '식비',
        expiryDate: '2024-11-28',
        status: 'used',
        description: '첫 거래 축하 쿠폰',
        minPurchase: 10000,
        usedDate: '2024-11-28'
    },
    {
        id: 6,
        merchant: '이마트',
        icon: '', // TODO: 아이콘 추가
        discount: 10000,
        category: '쇼핑',
        expiryDate: '2024-11-25',
        status: 'expired',
        description: '대용량 구매 쿠폰',
        minPurchase: 100000
    },
];

export default function CouponScreen() {
    const { colors } = useTheme();
    const [coupons, setCoupons] = useState(MOCK_COUPONS);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('전체');
    const [showUsed, setShowUsed] = useState(false);

    const categories = ['전체', '식비', '쇼핑', '편의점', '여가'];

    // 필터링 로직
    const filteredCoupons = coupons.filter(coupon => {
        // 검색어 필터
        if (searchQuery && !coupon.merchant.toLowerCase().includes(searchQuery.toLowerCase())) {
            return false;
        }
        // 카테고리 필터
        if (selectedCategory !== '전체' && coupon.category !== selectedCategory) {
            return false;
        }
        // 상태 필터
        if (!showUsed && (coupon.status === 'used' || coupon.status === 'expired')) {
            return false;
        }
        return true;
    });

    // 상태별 분류
    const availableCoupons = filteredCoupons.filter(c => c.status === 'available' && c.daysLeft > 7);
    const expiringSoonCoupons = filteredCoupons.filter(c => c.status === 'available' && c.daysLeft <= 7);

    // 전체 쿠폰에서 사용완료 쿠폰 계산 (토글 버튼이 항상 보이도록)
    const allUsedCoupons = coupons.filter(c => c.status === 'used' || c.status === 'expired');
    // 필터링된 사용완료 쿠폰 (검색 & 카테고리 고려)
    const usedCoupons = filteredCoupons.filter(c => c.status === 'used' || c.status === 'expired');

    // ============================================================
    // TODO: 백엔드 연결 - 쿠폰 사용
    // ============================================================
    // 백엔드 API 연결 시 이 함수를 수정하여 실제 쿠폰 사용 처리를 하세요.
    //
    // 백엔드 API 엔드포인트:
    // - POST /api/coupons/{couponId}/use
    //
    // 요청 예시:
    // const handleUseCoupon = async (coupon) => {
    //     try {
    //         const token = await AsyncStorage.getItem('authToken');
    //         const response = await fetch(`${API_BASE_URL}/coupons/${coupon.id}/use`, {
    //             method: 'POST',
    //             headers: {
    //                 'Content-Type': 'application/json',
    //                 'Authorization': `Bearer ${token}`
    //             },
    //             body: JSON.stringify({
    //                 merchantId: coupon.merchantId,
    //                 discount: coupon.discount
    //             })
    //         });
    //
    //         if (!response.ok) throw new Error('쿠폰 사용 실패');
    //
    //         const result = await response.json();
    //         // 쿠폰 상태 업데이트
    //         setCoupons(prev => prev.map(c => 
    //             c.id === coupon.id 
    //                 ? { ...c, status: 'used', usedDate: new Date().toISOString() }
    //                 : c
    //         ));
    //
    //         // QR 코드 또는 바코드 표시
    //         if (result.qrCode) {
    //             // QR 코드 모달 표시
    //         }
    //
    //         alert(`✅ 쿠폰이 사용되었습니다!`);
    //     } catch (error) {
    //         console.error('쿠폰 사용 실패:', error);
    //         alert('쿠폰 사용 중 오류가 발생했습니다.');
    //     }
    // };
    // ============================================================
    const handleUseCoupon = (coupon) => {
        // 현재는 Mock 처리 (백엔드 연결 시 위 주석 참고하여 API 호출로 교체)
        alert(`${coupon.merchant} 쿠폰 사용하기\n\n할인 금액: ${formatCurrency(coupon.discount)}\n최소 구매금액: ${formatCurrency(coupon.minPurchase)}\n\n실제 앱에서는 QR 코드나 바코드가 표시됩니다.`);
    };

    const CouponCard = ({ item }) => {
        const isExpiringSoon = item.status === 'available' && item.daysLeft <= 7;
        const isUsed = item.status === 'used' || item.status === 'expired';

        return (
            <TouchableOpacity
                style={[
                    styles(colors).couponCard,
                    isUsed && styles(colors).couponCardUsed,
                    isExpiringSoon && styles(colors).couponCardExpiring
                ]}
                onPress={() => !isUsed && handleUseCoupon(item)}
                disabled={isUsed}
                activeOpacity={0.7}>

                <View style={styles(colors).couponHeader}>
                    <Text style={styles(colors).couponIcon}>{item.icon}</Text>
                    <View style={styles(colors).couponInfo}>
                        <Text style={[styles(colors).couponMerchant, isUsed && styles(colors).textMuted]}>
                            {item.merchant}
                        </Text>
                        <Text style={[styles(colors).couponCategory, isUsed && styles(colors).textMuted]}>
                            {item.category}
                        </Text>
                    </View>
                    {item.status === 'available' && (
                        <View style={[
                            styles(colors).statusBadge,
                            isExpiringSoon && styles(colors).statusBadgeWarning
                        ]}>
                            <Text style={[
                                styles(colors).statusBadgeText,
                                isExpiringSoon && styles(colors).statusBadgeTextWarning
                            ]}>
                                {isExpiringSoon ? `${item.daysLeft}일 남음` : '사용가능'}
                            </Text>
                        </View>
                    )}
                    {item.status === 'used' && (
                        <View style={styles(colors).statusBadgeUsed}>
                            <Text style={styles(colors).statusBadgeTextUsed}>사용완료</Text>
                        </View>
                    )}
                    {item.status === 'expired' && (
                        <View style={styles(colors).statusBadgeExpired}>
                            <Text style={styles(colors).statusBadgeTextExpired}>만료됨</Text>
                        </View>
                    )}
                </View>

                <View style={styles(colors).couponDivider} />

                <View style={styles(colors).couponBody}>
                    <Text style={[styles(colors).couponDescription, isUsed && styles(colors).textMuted]}>
                        {item.description}
                    </Text>
                    <View style={styles(colors).couponDetails}>
                        <View style={styles(colors).couponDetailRow}>
                            <Text style={[styles(colors).couponDetailLabel, isUsed && styles(colors).textMuted]}>
                                할인 금액
                            </Text>
                            <Text style={[styles(colors).couponDiscount, isUsed && styles(colors).textMuted]}>
                                {formatCurrency(item.discount)}
                            </Text>
                        </View>
                        <View style={styles(colors).couponDetailRow}>
                            <Text style={[styles(colors).couponDetailLabel, isUsed && styles(colors).textMuted]}>
                                최소 구매
                            </Text>
                            <Text style={[styles(colors).couponDetailValue, isUsed && styles(colors).textMuted]}>
                                {formatCurrency(item.minPurchase)}
                            </Text>
                        </View>
                        <View style={styles(colors).couponDetailRow}>
                            <Text style={[styles(colors).couponDetailLabel, isUsed && styles(colors).textMuted]}>
                                {item.status === 'used' ? '사용일' : '만료일'}
                            </Text>
                            <Text style={[styles(colors).couponDetailValue, isUsed && styles(colors).textMuted]}>
                                {item.status === 'used' ? item.usedDate : item.expiryDate}
                            </Text>
                        </View>
                    </View>
                </View>

                {item.status === 'available' && (
                    <TouchableOpacity
                        style={styles(colors).useCouponButton}
                        onPress={() => handleUseCoupon(item)}>
                        <Text style={styles(colors).useCouponButtonText}>사용하기</Text>
                    </TouchableOpacity>
                )}
            </TouchableOpacity>
        );
    };

    const SectionHeader = ({ title, count }) => (
        <View style={styles(colors).sectionHeader}>
            <Text style={styles(colors).sectionTitle}>{title}</Text>
            <View style={styles(colors).countBadge}>
                <Text style={styles(colors).countBadgeText}>{count}</Text>
            </View>
        </View>
    );

    return (
        <View style={styles(colors).container}>
            {/* Header */}
            <View style={styles(colors).header}>
                <Text style={styles(colors).title}>내 쿠폰</Text>
                <Text style={styles(colors).subtitle}>
                    사용 가능: {availableCoupons.length + expiringSoonCoupons.length}개
                </Text>
            </View>

            {/* Search Bar */}
            <View style={styles(colors).searchContainer}>
                <Text style={styles(colors).searchIcon}>🔍</Text>
                <TextInput
                    style={styles(colors).searchInput}
                    placeholder="가맹점 검색..."
                    placeholderTextColor={colors.textSecondary}
                    value={searchQuery}
                    onChangeText={setSearchQuery}
                />
                {searchQuery !== '' && (
                    <TouchableOpacity
                        style={styles(colors).clearButton}
                        onPress={() => setSearchQuery('')}>
                        <Text style={styles(colors).clearIcon}>✕</Text>
                    </TouchableOpacity>
                )}
            </View>

            {/* Category Filter */}
            <View style={styles(colors).categoryContainer}>
                {categories.map(category => (
                    <TouchableOpacity
                        key={category}
                        style={[
                            styles(colors).categoryChip,
                            selectedCategory === category && styles(colors).categoryChipActive
                        ]}
                        onPress={() => setSelectedCategory(category)}>
                        <Text style={[
                            styles(colors).categoryChipText,
                            selectedCategory === category && styles(colors).categoryChipTextActive
                        ]}>
                            {category}
                        </Text>
                    </TouchableOpacity>
                ))}
            </View>

            {/* Coupon List */}
            <ScrollView style={styles(colors).scrollView}>
                {/* Expiring Soon */}
                {expiringSoonCoupons.length > 0 && (
                    <View style={styles(colors).section}>
                        <SectionHeader title="곧 만료" count={expiringSoonCoupons.length} />
                        {expiringSoonCoupons.map(coupon => (
                            <CouponCard key={coupon.id} item={coupon} />
                        ))}
                    </View>
                )}

                {/* Available */}
                {availableCoupons.length > 0 && (
                    <View style={styles(colors).section}>
                        <SectionHeader title="사용 가능" count={availableCoupons.length} />
                        {availableCoupons.map(coupon => (
                            <CouponCard key={coupon.id} item={coupon} />
                        ))}
                    </View>
                )}

                {/* Used/Expired Toggle */}
                {allUsedCoupons.length > 0 && (
                    <View style={styles(colors).section}>
                        <TouchableOpacity
                            style={styles(colors).usedToggle}
                            onPress={() => setShowUsed(!showUsed)}>
                            <Text style={styles(colors).usedToggleText}>
                                사용 완료 / 만료 ({allUsedCoupons.length})
                            </Text>
                            <Text style={styles(colors).usedToggleIcon}>
                                {showUsed ? '▼' : '▶'}
                            </Text>
                        </TouchableOpacity>

                        {showUsed && usedCoupons.map(coupon => (
                            <CouponCard key={coupon.id} item={coupon} />
                        ))}
                    </View>
                )}

                {/* Empty State */}
                {filteredCoupons.length === 0 && (
                    <EmptyState
                        icon="🎫"
                        title="쿠폰이 없습니다"
                        description="AI가 예측한 쿠폰을 받아보세요!"
                    />
                )}
            </ScrollView>
        </View>
    );
}

const styles = (colors) => StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background
    },

    // Header
    header: {
        padding: 20,
        backgroundColor: colors.cardBackground,
        borderBottomWidth: 1,
        borderBottomColor: colors.border
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 4
    },
    subtitle: {
        fontSize: 14,
        color: colors.textSecondary
    },

    // Search
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: colors.cardBackground,
        padding: 12,
        borderBottomWidth: 1,
        borderBottomColor: colors.border
    },
    searchIcon: { fontSize: 18, marginRight: 10 },
    searchInput: { flex: 1, fontSize: 15, color: colors.text, padding: 0 },
    clearButton: { padding: 8 },
    clearIcon: { fontSize: 18, color: colors.textSecondary },

    // Category Filter
    categoryContainer: {
        flexDirection: 'row',
        paddingHorizontal: 12,
        paddingVertical: 8,
        gap: 8,
        backgroundColor: colors.cardBackground,
        borderBottomWidth: 1,
        borderBottomColor: colors.border
    },
    categoryChip: {
        flex: 1,
        paddingVertical: 8,
        borderRadius: 16,
        backgroundColor: colors.background,
        borderWidth: 1,
        borderColor: colors.border,
        alignItems: 'center',
        justifyContent: 'center'
    },
    categoryChipActive: {
        backgroundColor: colors.primary,
        borderColor: colors.primary
    },
    categoryChipText: {
        fontSize: 13,
        color: colors.text,
        fontWeight: '600'
    },
    categoryChipTextActive: {
        color: '#fff',
        fontWeight: 'bold'
    },

    // Scroll View
    scrollView: { flex: 1 },

    // Section
    section: { marginBottom: 16 },
    sectionHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 16,
        paddingBottom: 8
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: colors.text
    },
    countBadge: {
        backgroundColor: colors.primary,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 10
    },
    countBadgeText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold'
    },

    // Coupon Card
    couponCard: {
        backgroundColor: colors.cardBackground,
        marginHorizontal: 16,
        marginBottom: 12,
        borderRadius: 12,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: colors.border
    },
    couponCardUsed: {
        opacity: 0.6
    },
    couponCardExpiring: {
        borderColor: '#ffc107',
        borderWidth: 2
    },

    couponHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        gap: 12
    },
    couponIcon: {
        fontSize: 40
    },
    couponInfo: {
        flex: 1
    },
    couponMerchant: {
        fontSize: 18,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 4
    },
    couponCategory: {
        fontSize: 14,
        color: colors.textSecondary
    },

    statusBadge: {
        backgroundColor: '#28a745',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12
    },
    statusBadgeWarning: {
        backgroundColor: '#ffc107'
    },
    statusBadgeText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold'
    },
    statusBadgeTextWarning: {
        color: '#000'
    },
    statusBadgeUsed: {
        backgroundColor: '#6c757d',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12
    },
    statusBadgeTextUsed: {
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold'
    },
    statusBadgeExpired: {
        backgroundColor: '#dc3545',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12
    },
    statusBadgeTextExpired: {
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold'
    },

    couponDivider: {
        height: 1,
        backgroundColor: colors.border,
        marginHorizontal: 16
    },

    couponBody: {
        padding: 16
    },
    couponDescription: {
        fontSize: 14,
        color: colors.textSecondary,
        marginBottom: 12
    },
    couponDetails: {
        gap: 8
    },
    couponDetailRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center'
    },
    couponDetailLabel: {
        fontSize: 14,
        color: colors.textSecondary
    },
    couponDiscount: {
        fontSize: 20,
        fontWeight: 'bold',
        color: colors.primary
    },
    couponDetailValue: {
        fontSize: 14,
        color: colors.text,
        fontWeight: '500'
    },

    useCouponButton: {
        backgroundColor: colors.primary,
        padding: 16,
        alignItems: 'center'
    },
    useCouponButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold'
    },

    textMuted: {
        color: colors.textSecondary,
        opacity: 0.7
    },

    // Used Toggle
    usedToggle: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 16,
        backgroundColor: colors.cardBackground,
        marginHorizontal: 16,
        borderRadius: 12,
        marginBottom: 12
    },
    usedToggleText: {
        fontSize: 16,
        fontWeight: '600',
        color: colors.text
    },
    usedToggleIcon: {
        fontSize: 14,
        color: colors.textSecondary
    }
});
