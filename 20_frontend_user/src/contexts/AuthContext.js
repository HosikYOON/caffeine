import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { apiClient, API_BASE_URL } from '../api/client';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth는 AuthProvider 안에서만 사용 가능합니다!');
    }
    return context;
};

// AuthProvider
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        checkLoginStatus();
    }, []);

    const checkLoginStatus = async () => {
        try {
            const userData = await AsyncStorage.getItem('user');
            if (userData) {
                setUser(JSON.parse(userData));
            }
        } catch (error) {
            console.error('로그인 상태 확인 실패:', error);
        } finally {
            setLoading(false);
        }
    };

    // 로그인
    const login = async (email, password) => {
        try {
            const params = new URLSearchParams();
            params.append('username', email);
            params.append('password', password);

            const response = await apiClient.post('/users/login', params, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            if (response.data) {
                const { access_token, refresh_token } = response.data;
                await AsyncStorage.setItem('accessToken', access_token);
                await AsyncStorage.setItem('refreshToken', refresh_token);
                await AsyncStorage.setItem('authToken', access_token);

                const userResponse = await apiClient.get('/users/me');
                if (userResponse.data) {
                    const userData = userResponse.data;
                    const prevUserJson = await AsyncStorage.getItem('user');
                    const prevUser = prevUserJson ? JSON.parse(prevUserJson) : null;
                    if (prevUser?.id && prevUser.id !== userData.id) {
                        await AsyncStorage.removeItem(`transactions_cache_${prevUser.id}`);
                        await AsyncStorage.removeItem(`last_sync_time_${prevUser.id}`);
                    }

                    await AsyncStorage.setItem('user', JSON.stringify(userData));
                    setUser(userData);
                    return { success: true };
                }
            }
            return { success: false, error: '로그인에 실패했습니다.' };
        } catch (error) {
            console.error('Login error:', error);
            let errorMessage = '이메일 또는 비밀번호가 올바르지 않습니다.';
            if (error.response?.data?.detail) {
                const detail = error.response.data.detail;
                errorMessage = Array.isArray(detail) ? detail.map(err => err.msg).join('\n') : detail;
            }
            return { success: false, error: errorMessage };
        }
    };

    // 회원가입
    const signup = async (name, email, password, birthDate) => {
        try {
            const response = await apiClient.post('/users/signup', {
                name: name,
                email: email,
                password: password,
                phone: '000-0000-0000',
                birth_date: birthDate
            });
            if (response.data) {
                return await login(email, password);
            }
            return { success: false, error: '회원가입에 실패했습니다.' };
        } catch (error) {
            console.error('Signup error:', error);
            let errorMessage = '회원가입 중 오류가 발생했습니다.';
            if (error.response?.data?.detail) {
                const detail = error.response.data.detail;
                errorMessage = Array.isArray(detail) ? detail.map(err => err.msg).join('\n') : detail;
            }
            return { success: false, error: errorMessage };
        }
    };

    const logout = async () => {
        const userJson = await AsyncStorage.getItem('user');
        const user = userJson ? JSON.parse(userJson) : null;

        await AsyncStorage.removeItem('user');
        await AsyncStorage.removeItem('accessToken');
        await AsyncStorage.removeItem('refreshToken');
        await AsyncStorage.removeItem('authToken');

        if (user?.id) {
            await AsyncStorage.removeItem(`transactions_cache_${user.id}`);
            await AsyncStorage.removeItem(`last_sync_time_${user.id}`);
        }
        setUser(null);
        if (typeof window !== 'undefined') {
            window.location.reload();
        }
    };

    // 카카오 로그인
    const kakaoLogin = async (code) => {
        try {
            const redirect_uri = typeof window !== 'undefined'
                ? `${window.location.origin}/auth/kakao/callback`
                : 'http://localhost:8081/auth/kakao/callback';

            const response = await fetch(`${API_BASE_URL}/auth/kakao`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, redirect_uri }),
            });
            if (response.ok) {
                const data = await response.json();
                const userData = {
                    id: data.user?.id || Date.now(),
                    name: data.user?.nickname || '카카오 사용자',
                    email: data.user?.email || 'kakao@user.com',
                    provider: 'kakao',
                };
                await AsyncStorage.setItem('user', JSON.stringify(userData));
                if (data.access_token) await AsyncStorage.setItem('authToken', data.access_token);
                if (data.refresh_token) await AsyncStorage.setItem('refreshToken', data.refresh_token);
                setUser(userData);
                return { success: true };
            }
            return { success: false, error: '카카오 로그인 실패' };
        } catch (error) {
            return { success: false, error: '네트워크 오류' };
        }
    };

    const kakaoSignup = async (code) => {
        try {
            const redirect_uri = typeof window !== 'undefined'
                ? `${window.location.origin}/auth/kakao/signup/callback`
                : 'http://localhost:8081/auth/kakao/signup/callback';

            const response = await fetch(`${API_BASE_URL}/auth/kakao/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, redirect_uri }),
            });
            if (response.ok) {
                const data = await response.json();
                const userData = {
                    id: data.user?.id || Date.now(),
                    name: data.user?.nickname || '카카오 사용자',
                    email: data.user?.email || 'kakao@user.com',
                    provider: 'kakao',
                };
                await AsyncStorage.setItem('user', JSON.stringify(userData));
                if (data.access_token) await AsyncStorage.setItem('authToken', data.access_token);
                setUser(userData);
                return { success: true };
            }
            return { success: false, error: '카카오 회원가입 실패' };
        } catch (error) {
            return { success: false, error: '네트워크 오류' };
        }
    };

    // 구글 로그인
    const googleLogin = async (code) => {
        try {
            const redirect_uri = typeof window !== 'undefined'
                ? `${window.location.origin}/auth/google/callback`
                : 'http://localhost:8081/auth/google/callback';

            const response = await fetch(`${API_BASE_URL}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, redirect_uri }),
            });
            if (response.ok) {
                const data = await response.json();
                const userData = {
                    id: data.user?.id || Date.now(),
                    name: data.user?.nickname || '구글 사용자',
                    email: data.user?.email || 'google@user.com',
                    provider: 'google',
                };
                await AsyncStorage.setItem('user', JSON.stringify(userData));
                if (data.access_token) await AsyncStorage.setItem('authToken', data.access_token);
                setUser(userData);
                return { success: true };
            }
            return { success: false, error: '구글 로그인 실패' };
        } catch (error) {
            return { success: false, error: '네트워크 오류' };
        }
    };

    const googleSignup = async (code) => {
        try {
            const redirect_uri = typeof window !== 'undefined'
                ? `${window.location.origin}/auth/google/signup/callback`
                : 'http://localhost:8081/auth/google/signup/callback';

            const response = await fetch(`${API_BASE_URL}/auth/google/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, redirect_uri }),
            });
            if (response.ok) {
                const data = await response.json();
                const userData = {
                    id: data.user?.id || Date.now(),
                    name: data.user?.nickname || '구글 사용자',
                    email: data.user?.email || 'google@user.com',
                    provider: 'google',
                };
                await AsyncStorage.setItem('user', JSON.stringify(userData));
                if (data.access_token) await AsyncStorage.setItem('authToken', data.access_token);
                setUser(userData);
                return { success: true };
            }
            return { success: false, error: '구글 회원가입 실패' };
        } catch (error) {
            return { success: false, error: '네트워크 오류' };
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, signup, logout, kakaoLogin, kakaoSignup, googleLogin, googleSignup }}>
            {children}
        </AuthContext.Provider>
    );
};
