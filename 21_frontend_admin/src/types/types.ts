// TypeScript Type Definitions for Admin Dashboard
// User and Transaction types based on backend schemas

// ============================================================
// User Types
// ============================================================

export interface User {
    id: number;
    email: string;
    name: string;
    nickname?: string;
    phone?: string;
    role: string;
    group_id?: number;
    status: string;
    social_provider?: string;
    social_id?: string;
    created_at: string;
    updated_at: string;
    last_login_at?: string;
}

export interface UserStats {
    total_users: number;
    active_users: number;
    new_users_this_month: number;
    admin_users: number;
}

export interface UserFilters {
    search?: string;
    role?: string;
    status?: string;
}

// ============================================================
// Transaction Types
// ============================================================

export interface Transaction {
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
    transactions: Transaction[];
    data_source: string;
}

export interface TransactionStats {
    transaction_count: number;
    total_amount: number;
    average_amount: number;
}

export interface TransactionFilters {
    user_id?: number;
    category?: string;
    start_date?: string;
    end_date?: string;
    min_amount?: number;
    max_amount?: number;
    search?: string;
    status?: string;
}
