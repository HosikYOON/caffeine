export interface AnomalyData {
    id: number;
    category: string;
    amount: number;
    date: string;
    reason: string;
    riskLevel: '위험' | '경고' | '주의';
    status: 'pending' | 'approved' | 'rejected';
    userId: string;
    userName: string;
}

// 사용자 관리
export interface UserData {
    id: number;
    email: string;
    name: string;
    created_at: string;
    is_active: boolean;
    is_superuser: boolean;
}

// 거래 관리
export interface TransactionData {
    id: number;
    merchant: string;
    amount: number;
    category: string;
    transaction_date: string;
    description?: string;
    status: string;
    currency: string;
}

export interface TransactionListResponse {
    total: number;
    page: number;
    page_size: number;
    transactions: TransactionData[];
    data_source: string;
}

export interface TransactionFilters {
    user_id?: number;
    category?: string;
    start_date?: string;
    end_date?: string;
    min_amount?: number;
    max_amount?: number;
    search?: string;
    page?: number;
    page_size?: number;
}
