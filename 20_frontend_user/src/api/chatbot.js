/**
 * Chatbot API Service
 * LLM 챗봇과의 통신을 담당하는 모듈
 */

// API 기본 URL (환경변수로 관리 권장)
const LLM_API_URL = 'http://localhost:9102';

/**
 * AI 챗봇에게 메시지 전송
 * @param {Object} params - 요청 파라미터
 * @param {string} params.message - 사용자 메시지
 * @param {number} params.budget - 월 예산 (기본값: 1,000,000)
 * @param {Object} params.spendingHistory - 지출 내역 정보
 * @returns {Promise<Object>} AI 응답
 */
export const sendChatMessage = async ({ message, budget = 1000000, spendingHistory = {} }) => {
    try {
        const response = await fetch(`${LLM_API_URL}/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                budget,
                spending_history: spendingHistory,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ChatbotError(
                `API 요청 실패: ${response.status}`,
                response.status,
                errorData
            );
        }

        const data = await response.json();
        return {
            success: true,
            message: data.message,
            type: data.type || 'chat',
            model: data.model,
        };
    } catch (error) {
        if (error instanceof ChatbotError) {
            throw error;
        }
        throw new ChatbotError(
            '네트워크 오류가 발생했습니다',
            0,
            { originalError: error.message }
        );
    }
};

/**
 * 거래에 대한 AI 평가 요청
 * @param {Object} params - 요청 파라미터
 * @param {Object} params.transaction - 거래 정보
 * @param {number} params.budget - 월 예산
 * @param {Object} params.spendingHistory - 지출 내역 정보
 * @returns {Promise<Object>} AI 평가 응답
 */
export const evaluateTransaction = async ({ transaction, budget = 1000000, spendingHistory = {} }) => {
    try {
        const response = await fetch(`${LLM_API_URL}/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction,
                budget,
                spending_history: spendingHistory,
            }),
        });

        if (!response.ok) {
            throw new ChatbotError(`AI 평가 요청 실패: ${response.status}`, response.status);
        }

        const data = await response.json();
        return {
            success: true,
            message: data.message,
            type: 'transaction',
            model: data.model,
        };
    } catch (error) {
        console.error('AI 평가 실패:', error);
        return {
            success: false,
            message: null,
            error: error.message,
        };
    }
};

/**
 * 챗봇 커스텀 에러 클래스
 */
export class ChatbotError extends Error {
    constructor(message, statusCode, data = {}) {
        super(message);
        this.name = 'ChatbotError';
        this.statusCode = statusCode;
        this.data = data;
    }
}

/**
 * 기본 에러 메시지 생성
 * @param {Error} error - 에러 객체
 * @returns {string} 사용자 친화적 에러 메시지
 */
export const getErrorMessage = (error) => {
    if (error instanceof ChatbotError) {
        if (error.statusCode === 0) {
            return '네트워크 연결을 확인해주세요 😥';
        }
        if (error.statusCode >= 500) {
            return '서버에 문제가 생겼어요. 잠시 후 다시 시도해주세요 🔧';
        }
        if (error.statusCode >= 400) {
            return '요청에 문제가 있어요. 다시 시도해주세요 🤔';
        }
    }
    return '죄송해요, 잠시 문제가 생겼어요. 다시 말씀해주시겠어요? 😥';
};
