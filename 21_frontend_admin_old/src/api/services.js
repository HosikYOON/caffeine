// Admin API Services
import { apiClient } from './client';

/**
 * 대시보드 통계 조회
 */
export const getDashboardStats = async () => {
    try {
        const response = await apiClient.get('/api/analysis/summary');
        return response.data;
    } catch (error) {
        console.error('대시보드 통계 조회 실패:', error);
        throw error;
    }
};

/**
 * 전체 분석 데이터
 */
export const getFullAnalysis = async () => {
    try {
        const response = await apiClient.get('/api/analysis/full');
        return response.data;
    } catch (error) {
        console.error('전체 분석 조회 실패:', error);
        throw error;
    }
};

/**
 * 카테고리별 소비 분석
 */
export const getCategoryBreakdown = async (months = 1) => {
    try {
        const response = await apiClient.get('/api/analysis/categories', {
            params: { months }
        });
        return response.data;
    } catch (error) {
        console.error('카테고리 분석 조회 실패:', error);
        throw error;
    }
};

/**
 * 월별 지출 추이
 */
export const getMonthlyTrend = async (months = 6) => {
    try {
        const response = await apiClient.get('/api/analysis/monthly-trend', {
            params: { months }
        });
        return response.data;
    } catch (error) {
        console.error('월별 추이 조회 실패:', error);
        throw error;
    }
};

/**
 * 거래 목록 조회
 */
export const getTransactions = async (params = {}) => {
    try {
        const response = await apiClient.get('/api/transactions', { params });
        return response.data;
    } catch (error) {
        console.error('거래 목록 조회 실패:', error);
        throw error;
    }
};

/**
 * 거래 통계
 */
export const getTransactionStats = async () => {
    try {
        const response = await apiClient.get('/api/transactions/stats/summary');
        return response.data;
    } catch (error) {
        console.error('거래 통계 조회 실패:', error);
        throw error;
    }
};
