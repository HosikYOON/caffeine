import axios from "axios";
import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

const LOCAL_BASE_URL = "http://localhost:8001/api";  // 로컬 개발
const PROD_BASE_URL = "https://api.caffeineai.net/api";  // 프로덕션

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

// 응답 인터셉터: 401 에러 시 처리
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      console.warn("인증 만료 또는 권한 없음");
    }
    return Promise.reject(error);
  }
);

/**
 * Expo Push Token을 백엔드에 등록합니다.
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

export const getUnreadNotificationCount = async (userId) => {
  try {
    const response = await apiClient.get(`/notifications/user/${userId}/unread-count`);
    return response.data.unread_count;
  } catch (error) {
    console.error('❌ 읽지 않은 알림 개수 조회 실패:', error);
    return 0;
  }
};

export const markNotificationAsRead = async (notificationId) => {
  try {
    const response = await apiClient.post(`/notifications/${notificationId}/read`);
    return response.data;
  } catch (error) {
    console.error('❌ 알림 읽음 처리 실패:', error);
    throw error;
  }
};

export const markAllNotificationsAsRead = async (userId) => {
  try {
    const response = await apiClient.post(`/notifications/user/${userId}/read-all`);
    return response.data;
  } catch (error) {
    console.error('❌ 전체 알림 읽음 처리 실패:', error);
    throw error;
  }
};
