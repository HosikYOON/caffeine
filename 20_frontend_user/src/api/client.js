import axios from "axios";
import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

const LOCAL_BASE_URL = "http://localhost:8001/api";  // 로컬 개발 (FastAPI /api prefix 대응)
const PROD_BASE_URL = "https://d26uyg5darllja.cloudfront.net/api";

// 환경 판별: 웹에서 localhost면 로컬, 그 외(앱 포함)는 프로덕션
const isLocal =
  Platform.OS === "web" &&
  typeof window !== "undefined" &&
  window.location?.hostname?.includes("localhost");

export const API_BASE_URL = isLocal ? LOCAL_BASE_URL : PROD_BASE_URL;

// API Client - Axios 인스턴스
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: false,
});

// 요청 인터셉터: 모든 API 요청에 Authorization 헤더 자동 추가
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem("authToken");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error("토큰 로드 실패:", error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터: 401 에러 시 처리 (선택적)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      console.warn("인증 만료 또는 권한 없음");
      // 필요시 로그아웃 처리 또는 토큰 갱신 로직
    }
    return Promise.reject(error);
  }
);

/**
 * Expo Push Token을 백엔드에 등록합니다.
 * 
 * @param {string} pushToken - Expo Push Token (ExponentPushToken[xxx] 형식)
 * @returns {Promise<Object>} 등록 결과
 */
export const registerPushToken = async (pushToken) => {
  try {
    const response = await apiClient.post('/users/register-push-token', {
      push_token: pushToken
    });
    console.log('✅ Push Token 등록 성공:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Push Token 등록 실패:', error);
    throw error;
  }
};

// =============================================
// 알림 센터 API
// =============================================

/**
 * 사용자의 알림 목록을 조회합니다.
 * 
 * @param {number} userId - 사용자 ID
 * @param {Object} options - 옵션
 * @param {number} options.limit - 최대 개수 (기본 50)
 * @param {boolean} options.unreadOnly - 읽지 않은 알림만 조회
 * @returns {Promise<Array>} 알림 목록
 */
export const getNotifications = async (userId, options = {}) => {
  try {
    const { limit = 50, unreadOnly = false } = options;
    const response = await apiClient.get(`/notifications/user/${userId}`, {
      params: { limit, unread_only: unreadOnly }
    });
    return response.data;
  } catch (error) {
    console.error('❌ 알림 조회 실패:', error);
    throw error;
  }
};

/**
 * 읽지 않은 알림 개수를 조회합니다.
 * 
 * @param {number} userId - 사용자 ID
 * @returns {Promise<number>} 읽지 않은 알림 개수
 */
export const getUnreadNotificationCount = async (userId) => {
  try {
    const response = await apiClient.get(`/notifications/user/${userId}/unread-count`);
    return response.data.unread_count;
  } catch (error) {
    console.error('❌ 읽지 않은 알림 개수 조회 실패:', error);
    return 0;
  }
};

/**
 * 알림을 읽음 처리합니다.
 * 
 * @param {number} notificationId - 알림 ID
 * @returns {Promise<Object>} 결과
 */
export const markNotificationAsRead = async (notificationId) => {
  try {
    const response = await apiClient.post(`/notifications/${notificationId}/read`);
    return response.data;
  } catch (error) {
    console.error('❌ 알림 읽음 처리 실패:', error);
    throw error;
  }
};

/**
 * 모든 알림을 읽음 처리합니다.
 * 
 * @param {number} userId - 사용자 ID
 * @returns {Promise<Object>} 결과
 */
export const markAllNotificationsAsRead = async (userId) => {
  try {
    const response = await apiClient.post(`/notifications/user/${userId}/read-all`);
    return response.data;
  } catch (error) {
    console.error('❌ 전체 알림 읽음 처리 실패:', error);
    throw error;
  }
};
