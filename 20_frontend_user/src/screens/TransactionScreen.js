
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity, Modal, TextInput, Alert, Platform, ScrollView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Feather } from '@expo/vector-icons';
import { apiClient, getAnomalies, reportAnomaly, ignoreAnomaly } from '../api';
import { useTheme } from '../contexts/ThemeContext';
import { useTransactions } from '../contexts/TransactionContext';
import EmptyState from '../components/EmptyState';
import AddTransactionModal from '../components/AddTransactionModal';

// 카테고리 매핑 (구 카테고리명 → 신 카테고리명)
const mapCategory = (category) => {
    const mapping = {
        '식비': '외식',
        '여가': '생활',
        '공과금': '생활',
        '의료': '생활',
        '카페': '외식',
    };
    return mapping[category] || category;
};

import { formatCurrency } from '../utils/currency';
import { EMPTY_MESSAGES } from '../constants';

export default function TransactionScreen({ navigation, route }) {
    const { colors } = useTheme();
    const { transactions, updateTransactionNote, addTransaction, removeTransaction } = useTransactions();
    const [displayTransactions, setDisplayTransactions] = useState([]);
    const [selectedTransaction, setSelectedTransaction] = useState(null);
    const [modalVisible, setModalVisible] = useState(false);
    const [addModalVisible, setAddModalVisible] = useState(false);
    const [anomalyCategoryModalVisible, setAnomalyCategoryModalVisible] = useState(false);
    const [isEditingNote, setIsEditingNote] = useState(false);
    const [editedNote, setEditedNote] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [prediction, setPrediction] = useState(null);
    const [isAnomalyMode, setIsAnomalyMode] = useState(false);

    useEffect(() => {
        const loadData = async () => {
            if (route.params?.filter === 'suspicious') {
                setIsAnomalyMode(true);
                try {
                    const anomalies = await getAnomalies();
                    const mapped = anomalies.map(a => ({
                        id: a.id,
                        merchant: a.merchant || a.userName,
                        businessName: "이상 거래 감지",
                        amount: a.amount,
                        category: a.category,
                        date: a.date,
                        cardType: a.riskLevel === 'high' ? '위험' : '주의',
                        notes: a.reason,
                        status: a.status,
                        isAnomaly: true
                    }));
                    setDisplayTransactions(mapped);
                } catch (error) {
                    console.error("Failed to load anomalies", error);
                    setDisplayTransactions([]);
                }
            } else {
                setIsAnomalyMode(false);
                setDisplayTransactions(transactions);
            }
        };
        loadData();
    }, [transactions, route.params?.filter]);

    const fetchPrediction = async () => {
        try {
            const recentTransaction = transactions[0];
            if (!recentTransaction) return;

            const requestData = {
                날짜: recentTransaction.date.split(' ')[0],
                시간: recentTransaction.date.split(' ')[1] || '00:00',
                타입: '지출',
                대분류: recentTransaction.category,
                소분류: '기타',
                내용: recentTransaction.merchant,
                금액: String(-recentTransaction.amount),
                화폐: 'KRW',
                결제수단: (recentTransaction.cardType || '신용') + '카드',
                메모: recentTransaction.notes || ''
            };

            const response = await apiClient.post('/ml/predict', {
                features: requestData
            });
            const predictedCategory = response.data.prediction;
            setPrediction(predictedCategory);

            try {
                const couponResponse = await apiClient.post('/api/coupons/generate-from-prediction', {
                    predicted_category: predictedCategory,
                    confidence: response.data.confidence || 0.8
                });

                alert(
                    `🎉 다음 소비 예측: ${predictedCategory}\n\n` +
                    `🎁 쿠폰 발급 완료!\n` +
                    `${couponResponse.data.merchant_name}에서 사용 가능한\n` +
                    `${formatCurrency(couponResponse.data.discount_amount)} 할인 쿠폰이 발급되었습니다!\n\n` +
                    `만료일: ${couponResponse.data.expiry_date}`
                );
            } catch (couponError) {
                console.error('Coupon generation failed:', couponError);
                alert(`다음 소비 예측: ${predictedCategory}\n\n쿠폰 발급 중 오류가 발생했습니다.`);
            }
        } catch (error) {
            console.error('Prediction failed:', error);
            Alert.alert('오류', '예측 실패: ' + (error.response?.data?.detail || error.message));
        }
    };

    const filteredTransactions = displayTransactions.filter(t => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            (t.merchant?.toLowerCase() || '').includes(query) ||
            (t.category?.toLowerCase() || '').includes(query) ||
            (t.notes?.toLowerCase() || '').includes(query) ||
            (t.businessName?.toLowerCase() || '').includes(query)
        );
    });

    const handleTransactionClick = (item) => {
        setSelectedTransaction(item);
        setEditedNote(item.notes || '');
        setIsEditingNote(false);
        setModalVisible(true);
    };

    const handleMarkAsAnomaly = () => {
        setModalVisible(false);
        setTimeout(() => {
            setAnomalyCategoryModalVisible(true);
        }, 300);
    };

<<<<<<< HEAD
    // 이상거래 카테고리 선택
=======
>>>>>>> cyj_fraud
    const handleCategorySelect = (category) => {
        if (!selectedTransaction) return;

        setAnomalyCategoryModalVisible(false);
        // Only update local state if showing standard transactions
        if (!isAnomalyMode) {
            // In a real app, we would update this via API
        }

        const messages = {
            safe: '✅ 안전한 거래로 표시되었습니다.',
            suspicious: '🟡 의심 거래로 표시되었습니다.\n이상탐지 탭에서 확인할 수 있습니다.',
            dangerous: '🔴 위험 거래로 표시되었습니다.\n고객센터로 자동 신고되었습니다.'
        };

        setTimeout(() => {
            alert(messages[category]);
            if (category === 'suspicious' || category === 'dangerous') {
                // Already there or similar
            }
        }, 300);
    };

    const handleSaveNote = async () => {
        if (selectedTransaction) {
            const result = await updateTransactionNote(selectedTransaction.id, editedNote);

            if (result.success) {
                setSelectedTransaction({ ...selectedTransaction, notes: editedNote });
                // Also update display list locally to reflect change immediately
                setDisplayTransactions(prev => prev.map(t =>
                    t.id === selectedTransaction.id ? { ...t, notes: editedNote } : t
                ));
                setIsEditingNote(false);
            } else {
                alert('메모 저장 실패: ' + (result.error?.message || '알 수 없는 오류'));
            }
        }
    };

    // 거래 삭제
    const handleDeleteTransaction = async () => {
        console.log('handleDeleteTransaction 호출됨');

        if (!selectedTransaction) {
            console.log('selectedTransaction이 없음');
            return;
        }

        const txId = selectedTransaction.id;
        console.log('삭제할 거래 ID:', txId);

        // 모달 닫기
        setModalVisible(false);
        setSelectedTransaction(null);

        try {
            const result = await removeTransaction(txId);
            console.log('삭제 결과:', result);
            if (result.success) {
                console.log('거래 삭제 완료:', txId);
                // 성공 알림 (선택사항)
                // alert('거래가 삭제되었습니다.');
            } else {
                alert('거래 삭제 실패: ' + (result.error?.message || '알 수 없는 오류'));
            }
        } catch (error) {
            console.error('삭제 중 에러:', error);
            alert('거래 삭제 중 오류가 발생했습니다.');
        }
    };

    // 스타일 객체 생성 (colors 의존성)
    const s = styles(colors);

    // 거래 내역 렌더링
    const renderItem = ({ item }) => (
        <TouchableOpacity
            style={[s.transactionCard, { backgroundColor: colors.cardBackground }]}
            onPress={() => handleTransactionClick(item)}
            activeOpacity={0.7}
        >
            <View style={s.transactionHeader}>
                <View style={s.merchantInfo}>
                    <Text style={[s.merchant, { color: colors.text }]}>{item.merchant}</Text>
                    <Text style={s.cardTypeBadge(item.cardType)}>{item.cardType}</Text>
                </View>
                <Text style={s.amount}>{formatCurrency(item.amount)}</Text>
            </View>
            <View style={s.transactionDetails}>
                <Text style={[s.category, { color: colors.textSecondary }]}>{mapCategory(item.category)} | {item.date}</Text>
            </View>
            {
                item.notes ? (
                    <Text style={[s.notes, { color: colors.text }]} numberOfLines={1}>memo: {item.notes}</Text>
                ) : null
            }
        </TouchableOpacity >
    );

    return (
        <LinearGradient colors={colors.screenGradient} style={styles(colors).container}>
            {/* Header */}
            <View style={styles(colors).header}>
                <View>
                    <Text style={styles(colors).title}>{isAnomalyMode ? '이상 거래 탐지' : '거래내역'}</Text>
                    <Text style={styles(colors).subtitle}>
                        {searchQuery ? `검색 결과 ${filteredTransactions.length}건` : `총 ${displayTransactions.length}건`}
                    </Text>
                </View>
                <View style={styles(colors).headerIcon}>
                    <Feather name={isAnomalyMode ? "alert-triangle" : "file-text"} size={24} color={isAnomalyMode ? "#EF4444" : "#2563EB"} />
                </View>
            </View>

            {/* AI Prediction Card - Only show in normal mode and if transactions exist */}
            {!isAnomalyMode && transactions.length > 0 && (
                <View style={styles(colors).predictionCard}>
                    <View style={styles(colors).predictionHeader}>
                        <Text style={styles(colors).predictionIcon}>🤖</Text>
                        <Text style={styles(colors).predictionTitle}>AI 다음 소비 예측</Text>
                    </View>

                    {prediction !== null ? (
                        <Text style={styles(colors).predictionText}>
                            현재 소비 패턴 분석 결과, 다음 거래는
                            <Text style={{ fontWeight: 'bold', color: colors.primary }}>
                                {' '}{prediction}{' '}
                            </Text>
                            카테고리일 확률이 높습니다.
                        </Text>
                    ) : (
                        <Text style={styles(colors).predictionText}>
                            최근 거래 데이터를 분석하여 다음 소비 패턴을 예측합니다.
                        </Text>
                    )}

                    <TouchableOpacity
                        style={styles(colors).predictionButton}
                        onPress={fetchPrediction}
                    >
                        <Text style={styles(colors).predictionButtonText}>
                            {prediction !== null ? '다시 예측하기' : '다음 소비 예측하기'}
                        </Text>
                    </TouchableOpacity>
                </View>
            )}
            {/* Search Bar */}
            <View style={[s.searchContainer, { backgroundColor: colors.cardBackground, borderBottomColor: colors.border }]}>
                <Feather name="search" size={20} color={colors.textSecondary} style={s.searchIcon} />
                <TextInput
                    style={[s.searchInput, { color: colors.text }]}
                    placeholder="거래 내역 검색..."
                    placeholderTextColor={colors.textSecondary}
                    value={searchQuery}
                    onChangeText={setSearchQuery}
                />
                {searchQuery.length > 0 && (
                    <TouchableOpacity onPress={() => setSearchQuery('')} style={s.clearButton}>
                        <Feather name="x" size={18} color={colors.textSecondary} />
                    </TouchableOpacity>
                )}
            </View>

            {
                displayTransactions.length === 0 ? (
                    <EmptyState
                        icon="📊"
                        title={isAnomalyMode ? "이상 거래가 없습니다" : "연동된 거래내역이 없습니다"}
                        description={isAnomalyMode ? "안전하게 거래하고 계시네요!" : "프로필 → 데이터 동기화로 CSV 파일을 업로드하세요"}
                        actionText={isAnomalyMode ? "돌아가기" : "동기화 하러 가기"}
                        onAction={() => isAnomalyMode ? navigation.goBack() : navigation.navigate('프로필')}
                    />
                ) : filteredTransactions.length === 0 ? (
                    <EmptyState
                        icon="🔍"
                        title="검색 결과 없음"
                        description="검색 조건과 일치하는 거래가 없습니다"
                        actionText="검색 초기화"
                        onAction={() => setSearchQuery('')}
                    />
                ) : (
                    <FlatList
                        data={filteredTransactions}
                        renderItem={renderItem}
                        keyExtractor={item => item.id.toString()}
                        contentContainerStyle={styles(colors).list}
                    />
                )
            }

            {/* Floating Action Button for Add Transaction */}
            <TouchableOpacity
                style={[s.fab, { backgroundColor: colors.primary }]}
                onPress={() => setAddModalVisible(true)}
            >
                <Feather name="plus" size={24} color="#FFF" />
            </TouchableOpacity>

            {/* Detail Modal */}
            <Modal
                animationType="fade"
                transparent={true}
                visible={modalVisible}
                onRequestClose={() => setModalVisible(false)}
            >
                <View style={s.modalOverlay}>
                    <View style={[s.modalContent, { backgroundColor: colors.cardBackground, borderColor: colors.border }]}>
                        {selectedTransaction && (
                            <>
                                <View style={[s.modalHeader, { borderBottomColor: colors.border }]}>
                                    <Text style={[s.modalMerchant, { color: colors.text }]}>{selectedTransaction.merchant}</Text>
                                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                                        <Text style={[s.modalBusinessName, { color: colors.textSecondary }]}>{selectedTransaction.businessName}</Text>
                                        <Text style={s.cardTypeBadge(selectedTransaction.cardType)}>{selectedTransaction.cardType}</Text>
                                    </View>
                                </View>

                                <View style={[s.detailSection, { borderBottomColor: colors.border }]}>
                                    <View style={[s.detailRow, { borderBottomColor: colors.border + '40' }]}>
                                        <Text style={[s.detailLabel, { color: colors.textSecondary }]}>금액</Text>
                                        <Text style={[s.detailValueAmount, { color: colors.error }]}>{formatCurrency(selectedTransaction.amount)}</Text>
                                    </View>
                                    <View style={[s.detailRow, { borderBottomColor: colors.border + '40' }]}>
                                        <Text style={[s.detailLabel, { color: colors.textSecondary }]}>카테고리</Text>
                                        <Text style={[s.detailValue, { color: colors.text }]}>{selectedTransaction.category}</Text>
                                    </View>
                                    <View style={[s.detailRow, { borderBottomColor: colors.border + '40' }]}>
                                        <Text style={[s.detailLabel, { color: colors.textSecondary }]}>일시</Text>
                                        <Text style={[s.detailValue, { color: colors.text }]}>{selectedTransaction.date}</Text>
                                    </View>
                                    <View style={styles(colors).detailRow}>
                                        <Text style={styles(colors).detailLabel}>거래금액</Text>
                                        <Text style={styles(colors).detailValueAmount}>-{formatCurrency(selectedTransaction.amount, false)} 원</Text>
                                    </View>
                                    {!isAnomalyMode && (
                                        <View style={styles(colors).detailRow}>
                                            <Text style={styles(colors).detailLabel}>
                                                {selectedTransaction.cardType === '체크' ? '거래후잔액' : '결제액누계'}
                                            </Text>
                                            <Text style={styles(colors).detailValueBalance}>
                                                {selectedTransaction.cardType === '체크'
                                                    ? formatCurrency(selectedTransaction.balance || 0, false)
                                                    : formatCurrency(selectedTransaction.accumulated || 0, false)} 원
                                            </Text>
                                        </View>
                                    )}
                                    <View style={styles(colors).detailRow}>
                                        <Text style={styles(colors).detailLabel}>추가메모</Text>
                                        {isEditingNote ? (
                                            <View style={s.noteEditContainer}>
                                                <TextInput
                                                    style={[s.noteInput, { color: colors.text, borderColor: colors.border, backgroundColor: colors.background }]}
                                                    value={editedNote}
                                                    onChangeText={setEditedNote}
                                                    autoFocus
                                                />
                                                <TouchableOpacity onPress={handleSaveNote} style={s.noteSaveButton}>
                                                    <Text style={s.noteSaveText}>저장</Text>
                                                </TouchableOpacity>
                                            </View>
                                        ) : (
                                            <TouchableOpacity onPress={() => setIsEditingNote(true)} style={s.noteClickable}>
                                                <Text style={[s.detailValue, { color: colors.text }]}>{selectedTransaction.notes || '(없음)'}</Text>
                                                <Feather name="edit-2" size={14} color={colors.textSecondary} style={s.noteEditHint} />
                                            </TouchableOpacity>
                                        )}
                                    </View>
                                </View>

                                {/* Action Buttons */}
                                <View style={s.modalActions}>
                                    <TouchableOpacity
                                        style={[s.actionButton, s.deleteButton]}
                                        onPress={handleDeleteTransaction}
                                        activeOpacity={0.7}
                                    >
                                        <Feather name="trash-2" size={18} color="#EF4444" />
                                        <Text style={s.deleteButtonText}>삭제</Text>
                                    </TouchableOpacity>

                                    <TouchableOpacity style={[s.actionButton, s.anomalyButton]} onPress={handleMarkAsAnomaly}>
                                        <Feather name="alert-triangle" size={18} color="#F59E0B" />
                                        <Text style={s.anomalyButtonText}>이상거래 신고</Text>
                                    </TouchableOpacity>
                                </View>

                                <TouchableOpacity
                                    style={[s.closeButton, { backgroundColor: colors.background, borderColor: colors.border }]}
                                    onPress={() => setModalVisible(false)}
                                >
                                    <Text style={[s.closeButtonText, { color: colors.text }]}>닫기</Text>
                                </TouchableOpacity>
                            </>
                        )}
                    </View>
                </View>
            </Modal>

            {/* Add Transaction Modal */}
            <AddTransactionModal
                visible={addModalVisible}
                onClose={() => setAddModalVisible(false)}
                onSuccess={() => {
                    setAddModalVisible(false);
                }}
            />

            {/* Anomaly Action Modal (Report / Ignore) */}
            <Modal
                animationType="fade"
                transparent={true}
                visible={anomalyCategoryModalVisible}
                onRequestClose={() => setAnomalyCategoryModalVisible(false)}>
                <View style={styles(colors).modalOverlay}>
                    <View style={styles(colors).categoryModalContent}>
                        <Text style={styles(colors).modalTitle}>⚠️ 이상거래 확인</Text>

                        {selectedTransaction && (
                            <View style={styles(colors).categoryTransactionInfo}>
                                <Text style={styles(colors).categoryTransactionName}>
                                    {selectedTransaction.merchant}
                                </Text>
                                <Text style={styles(colors).categoryTransactionAmount}>
                                    {formatCurrency(selectedTransaction.amount)}
                                </Text>
                            </View>
                        )}

                        <Text style={styles(colors).modalText}>
                            본인이 사용하지 않은 거래인가요?
                        </Text>

                        <View style={styles(colors).actionButtons}>
                            {/* 조건부 렌더링: 이미 신고/무시된 경우 메시지 표시 */}
                            {(selectedTransaction?.notes === 'User Reported' || selectedTransaction?.status === 'reported') ? (
                                <View style={styles(colors).reportButton}>
                                    <Text style={styles(colors).reportButtonText}>🚨 이미 신고가 접수되었습니다.</Text>
                                    <Text style={{ ...styles(colors).actionButtonSubText, marginTop: 4 }}>관리자 확인 대기 중</Text>
                                </View>
                            ) : (selectedTransaction?.status === 'ignored' || selectedTransaction?.notes === 'User Ignored') ? (
                                <View style={{ ...styles(colors).actionButtonIgnore, backgroundColor: colors.success }}>
                                    <Text style={styles(colors).actionButtonText}>✅ 이미 무시한 알림입니다.</Text>
                                    <Text style={styles(colors).actionButtonSubText}>더 이상 알림이 뜨지 않습니다.</Text>
                                </View>
                            ) : (
                                <>
                                    {/* 신고하기 버튼 */}
                                    <TouchableOpacity
                                        style={styles(colors).actionButtonReport}
                                        onPress={async () => {
                                            try {
                                                await reportAnomaly(selectedTransaction.id);

                                                // 즉시 상태 반영
                                                setSelectedTransaction(prev => ({ ...prev, notes: 'User Reported', status: 'pending' }));
                                                setDisplayTransactions(prev => prev.map(t =>
                                                    t.id === selectedTransaction.id ? { ...t, notes: 'User Reported', status: 'pending' } : t
                                                ));

                                                setTimeout(() => {
                                                    alert('🚨 신고가 접수되었습니다.\n관리자 확인 후 조치됩니다.');
                                                    setAnomalyCategoryModalVisible(false);
                                                }, 300);
                                            } catch (e) {
                                                alert('신고 처리 중 오류가 발생했습니다.');
                                            }
                                        }}>
                                        <Text style={styles(colors).actionButtonText}>🚨 신고하기</Text>
                                        <Text style={styles(colors).actionButtonSubText}>관리자에게 알림</Text>
                                    </TouchableOpacity>

                                    {/* 무시하기 버튼 */}
                                    <TouchableOpacity
                                        style={styles(colors).actionButtonIgnore}
                                        onPress={async () => {
                                            try {
                                                await ignoreAnomaly(selectedTransaction.id);

                                                // 즉시 상태 반영
                                                setSelectedTransaction(prev => ({ ...prev, notes: 'User Ignored', status: 'ignored' }));
                                                setDisplayTransactions(prev => prev.map(t =>
                                                    t.id === selectedTransaction.id ? { ...t, notes: 'User Ignored', status: 'ignored' } : t
                                                ));

                                                setTimeout(() => {
                                                    alert('✅ 확인되었습니다.\n더 이상 알림이 뜨지 않습니다.');
                                                    setAnomalyCategoryModalVisible(false);
                                                }, 300);
                                            } catch (e) {
                                                alert('처리 중 오류가 발생했습니다.');
                                            }
                                        }}>
                                        <Text style={styles(colors).actionButtonText}>👌 내가 쓴 거 맞아요</Text>
                                        <Text style={styles(colors).actionButtonSubText}>알림 무시하기</Text>
                                    </TouchableOpacity>
                                </>
                            )}
                        </View>

                        <TouchableOpacity
                            style={styles(colors).categoryModalCancel}
                            onPress={() => setAnomalyCategoryModalVisible(false)}>
                            <Text style={styles(colors).categoryModalCancelText}>취소</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </Modal>
        </LinearGradient>
    );
}

const styles = (colors) => StyleSheet.create({
    container: { flex: 1 },
    listContainer: { padding: 16, paddingBottom: 100 },
    transactionCard: {
        padding: 16,
        borderRadius: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
        elevation: 3,
    },
    transactionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
    merchantInfo: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    merchant: { fontSize: 16, fontWeight: 'bold' },
    cardTypeBadge: (type) => ({
        fontSize: 11,
        color: type === '신용' || type === '주의' ? '#2563EB' : type === '위험' ? '#EF4444' : '#059669',
        backgroundColor: type === '신용' || type === '주의' ? '#DBEAFE' : type === '위험' ? '#FEE2E2' : '#D1FAE5',
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 8,
        fontWeight: '600',
        overflow: 'hidden',
    }),
    amount: { fontSize: 18, fontWeight: '700', color: '#2563EB' },
    transactionDetails: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
    category: { fontSize: 14 },
    date: { fontSize: 12 },
    notes: { fontSize: 12, marginTop: 4, fontStyle: 'italic' },

    // Search styles
    searchContainer: { flexDirection: 'row', alignItems: 'center', padding: 16, borderBottomWidth: 1 },
    searchIcon: { fontSize: 20, marginRight: 12 },
    searchInput: { flex: 1, fontSize: 16, padding: 0 },
    clearButton: { padding: 8 },

    // Modal styles
    modalOverlay: { flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.5)', justifyContent: 'center', alignItems: 'center', padding: 20 },
    modalContent: { borderRadius: 16, padding: 24, width: '100%', maxWidth: 500, borderWidth: 1 },
    modalTitle: { fontSize: 20, fontWeight: 'bold', marginBottom: 20, textAlign: 'center' },
    modalHeader: { alignItems: 'center', marginBottom: 20, paddingBottom: 16, borderBottomWidth: 1 },
    modalMerchant: { fontSize: 20, fontWeight: 'bold', marginBottom: 8 },
    modalBusinessName: { fontSize: 13 },

    detailSection: { marginBottom: 20, paddingBottom: 16, borderBottomWidth: 1 },
    detailRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1 },
    detailLabel: { fontSize: 14, flex: 0.4 },
    detailValue: { fontSize: 14, flex: 0.6, textAlign: 'right' },
    detailValueAmount: { fontSize: 16, fontWeight: 'bold', flex: 0.6, textAlign: 'right' },

    noteClickable: { flex: 0.6, flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 8 },
    noteEditHint: { fontSize: 14, opacity: 0.5 },
    noteEditContainer: { flex: 0.6, flexDirection: 'row', gap: 8, alignItems: 'center' },
    noteInput: { flex: 1, borderWidth: 1, borderRadius: 8, padding: 8, fontSize: 14 },
    noteSaveButton: { backgroundColor: '#10B981', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
    noteSaveText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },

    // Action Buttons
    modalActions: { flexDirection: 'row', gap: 12, marginBottom: 16 },
    actionButton: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 12, borderRadius: 8, gap: 6 },
    deleteButton: { backgroundColor: '#FEE2E2' },
    deleteButtonText: { color: '#EF4444', fontWeight: 'bold', fontSize: 14 },
    anomalyButton: { backgroundColor: '#FEF3C7' },
    anomalyButtonText: { color: '#F59E0B', fontWeight: 'bold', fontSize: 14 },

    closeButton: { padding: 14, borderRadius: 8, borderWidth: 1, alignItems: 'center' },
    closeButtonText: { fontWeight: 'bold', fontSize: 14 },

    // Add Modal Styles
    inputGroup: { marginBottom: 16 },
    label: { fontSize: 14, marginBottom: 8, fontWeight: '500' },
    input: { borderWidth: 1, borderRadius: 8, padding: 12, fontSize: 16 },
    modalButtons: { flexDirection: 'row', gap: 12, marginTop: 8 },
    modalButtonCancel: { flex: 1, padding: 14, borderRadius: 8, borderWidth: 1, alignItems: 'center' },
    modalButtonConfirm: { flex: 1, padding: 14, borderRadius: 8, alignItems: 'center' },
    modalButtonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
    modalButtonTextCancel: { fontWeight: 'bold', fontSize: 16 },

    // FAB
    fab: {
        position: 'absolute',
        right: 20,
        bottom: 20,
        width: 56,
        height: 56,
        borderRadius: 28,
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.30,
        shadowRadius: 4.65,
        elevation: 8,
    },

    // Category Modal styles
    categoryModalContent: {
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: 24,
        width: '100%',
        maxWidth: 500,
        borderWidth: 1,
        borderColor: colors.border,
    },
    categoryTransactionInfo: {
        alignItems: 'center',
        padding: 16,
        backgroundColor: colors.background,
        borderRadius: 12,
        marginBottom: 20,
    },
    categoryTransactionName: {
        fontSize: 16,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 4,
    },
    categoryTransactionAmount: {
        fontSize: 20,
        fontWeight: 'bold',
        color: colors.error,
    },
    categoryOptions: {
        gap: 12,
        marginBottom: 20,
    },
    categoryOption: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        borderRadius: 12,
        borderWidth: 2,
    },
    categoryOptionSafe: {
        borderColor: colors.success,
        backgroundColor: colors.success + '10',
    },
    categoryOptionSuspicious: {
        borderColor: colors.warning,
        backgroundColor: colors.warning + '10',
    },
    categoryOptionDangerous: {
        borderColor: colors.error,
        backgroundColor: colors.error + '10',
    },
    categoryOptionIcon: {
        fontSize: 32,
        marginRight: 16,
    },
    categoryOptionContent: {
        flex: 1,
    },
    categoryOptionTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: colors.text,
        marginBottom: 4,
    },
    categoryOptionDesc: {
        fontSize: 13,
        color: colors.textSecondary,
        lineHeight: 18,
    },
    actionButtons: {
        flexDirection: 'column',
        gap: 12,
        marginBottom: 20,
        width: '100%',
    },
    actionButtonReport: {
        backgroundColor: '#EF4444',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
        shadowColor: '#EF4444',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 4,
    },
    actionButtonIgnore: {
        backgroundColor: '#3B82F6',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
        shadowColor: '#3B82F6',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 4,
    },
    actionButtonText: {
        color: '#FFFFFF',
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 2,
    },
    actionButtonSubText: {
        color: 'rgba(255, 255, 255, 0.8)',
        fontSize: 12,
    },
    reportButton: {
        backgroundColor: colors.error,
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
        marginBottom: 12,
    },
    reportButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
    },
    categoryModalCancel: {
        padding: 14,
        borderRadius: 12,
        backgroundColor: colors.background,
        borderWidth: 1,
        borderColor: colors.border,
        alignItems: 'center',
    },
    categoryModalCancelText: {
        color: colors.text,
        fontSize: 14,
        fontWeight: 'bold',
>>>>>>> cyj_fraud
    },

    // Prediction Card styles
    predictionCard: {
        marginHorizontal: 16,
        marginTop: 8,
        marginBottom: 16,
        padding: 20,
        backgroundColor: '#DBEAFE',
        borderRadius: 16,
        borderWidth: 1.5,
        borderColor: '#93C5FD',
        shadowColor: '#2563EB',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 4,
    },
    predictionHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    predictionIcon: {
        fontSize: 24,
        marginRight: 10,
    },
    predictionTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: '#1E40AF',
    },
    predictionText: {
        fontSize: 14,
        color: '#1E3A8A',
        lineHeight: 22,
        marginBottom: 16,
    },
    predictionButton: {
        backgroundColor: '#2563EB',
        padding: 14,
        borderRadius: 12,
        alignItems: 'center',
    },
    predictionButtonDisabled: {
        backgroundColor: '#93C5FD',
        opacity: 0.5,
    },
    predictionButtonText: {
        color: '#FFFFFF',
        fontSize: 15,
        fontWeight: '700',
    },
});
