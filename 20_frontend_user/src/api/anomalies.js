import { apiClient } from './client';

/**
 * 이상 거래 목록 조회
 * @param {string} userId - 사용자 ID (선택)
 */
export const getAnomalies = async (userId = null) => {
    try {
        const response = await apiClient.get('/anomalies');
        return response.data;
    } catch (error) {
        console.error('이상 거래 조회 실패:', error);
        return [];
    }
};

/**
 * 이상 거래 신고 (Confirm Fraud)
 * @param {number} txId - 거래 ID
 */
export const reportAnomaly = async (txId) => {
    try {
        const response = await apiClient.post(`/anomalies/${txId}/report`);
        return response.data;
    } catch (error) {
        console.error('이상 거래 신고 실패:', error);
        throw error;
    }
};

/**
 * 이상 거래 무시 (Mark as Safe)
 * @param {number} txId - 거래 ID
 */
export const ignoreAnomaly = async (txId) => {
    try {
        const response = await apiClient.post(`/anomalies/${txId}/ignore`);
        return response.data;
    } catch (error) {
        console.error('이상 거래 무시 실패:', error);
        throw error;
    }
};
