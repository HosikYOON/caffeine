import { apiClient } from './client';

/**
 * 이상 거래 목록 조회
 * @param {string} userId - 사용자 ID (선택)
 */
export const getAnomalies = async (userId = null) => {
    try {
        const response = await apiClient.get('/api/anomalies');
        return response.data;
    } catch (error) {
        console.error('이상 거래 조회 실패:', error);
        return [];
    }
};
