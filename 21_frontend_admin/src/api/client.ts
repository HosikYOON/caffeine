// API Client for Admin Dashboard

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface FetchOptions extends RequestInit {
    timeout?: number;
}

async function fetchWithTimeout(url: string, options: FetchOptions = {}) {
    const { timeout = 10000, ...fetchOptions } = options;

    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal,
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

export const apiClient = {
    async get(endpoint: string) {
        const response = await fetchWithTimeout(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        return response.json();
    },

    async post(endpoint: string, data: any) {
        const response = await fetchWithTimeout(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        return response.json();
    },

    async patch(endpoint: string, data: any) {
        const response = await fetchWithTimeout(`${API_BASE_URL}${endpoint}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        return response.json();
    },

    async delete(endpoint: string) {
        const response = await fetchWithTimeout(`${API_BASE_URL}${endpoint}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        return response.json();
    },
};

// Analysis API
export async function getFullAnalysis() {
    return apiClient.get('/api/analysis/full');
}

export async function getDashboardStats() {
    return apiClient.get('/api/analysis/summary');
}

export async function getCategoryBreakdown(months = 1) {
    return apiClient.get(`/api/analysis/categories?months=${months}`);
}

export async function getMonthlyTrend(months = 6) {
    return apiClient.get(`/api/analysis/monthly-trend?months=${months}`);
}

// Transactions API
export async function getTransactions(filters?: any, page = 1, pageSize = 20) {
    const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        ...(filters?.user_id && { user_id: filters.user_id.toString() }),
        ...(filters?.category && { category: filters.category }),
        ...(filters?.start_date && { start_date: filters.start_date }),
        ...(filters?.end_date && { end_date: filters.end_date }),
        ...(filters?.min_amount && { min_amount: filters.min_amount.toString() }),
        ...(filters?.max_amount && { max_amount: filters.max_amount.toString() }),
        ...(filters?.search && { search: filters.search }),
    });
    return apiClient.get(`/api/transactions?${params.toString()}`);
}

export async function getTransactionStats() {
    return apiClient.get('/api/transactions/stats/summary');
}

export async function getTransactionById(id: number) {
    return apiClient.get(`/api/transactions/${id}`);
}

export async function updateTransactionNote(id: number, description: string) {
    return apiClient.patch(`/api/transactions/${id}/note`, { description });
}

// Users API
export async function getUsers(filters?: any) {
    const params = new URLSearchParams({
        ...(filters?.search && { search: filters.search }),
        ...(filters?.role && { role: filters.role }),
        ...(filters?.status && { status: filters.status }),
    });
    const queryString = params.toString();
    return apiClient.get(`/users${queryString ? '?' + queryString : ''}`);
}

export async function getUserStats() {
    // Note: This endpoint may need to be created on backend
    // For now, we'll calculate from user list
    const users = await getUsers();
    const now = new Date();
    const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    return {
        total_users: users.length,
        active_users: users.filter((u: any) => u.status === 'ACTIVE').length,
        new_users_this_month: users.filter((u: any) => new Date(u.created_at) >= thisMonth).length,
        admin_users: users.filter((u: any) => u.role === 'ADMIN').length,
    };
}

export async function deleteUser(id: number) {
    return apiClient.delete(`/users/${id}`);
}

