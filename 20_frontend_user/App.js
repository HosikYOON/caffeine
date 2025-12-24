import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';
import { Text, ActivityIndicator, View } from 'react-native';
import { ThemeProvider, useTheme } from './src/contexts/ThemeContext';
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import { TransactionProvider } from './src/contexts/TransactionContext';
import { AISettingsProvider } from './src/contexts/AISettingsContext';
import { ToastProvider } from './src/contexts/ToastContext';

import DashboardScreen from './src/screens/DashboardScreen';
import TransactionScreen from './src/screens/TransactionScreen';
import CouponScreen from './src/screens/CouponScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import MoreScreen from './src/screens/MoreScreen';
import AnalysisScreen from './src/screens/AnalysisScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import LoginScreen from './src/screens/LoginScreen';
import SignupScreen from './src/screens/SignupScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

const TabBarIcon = ({ name, focused }) => {
  const icons = {
    '대시보드': '📊',
    '거래내역': '💳',
    '쿠폰함': '🎟️',
    '더보기': '⚙️'
  };
  return <Text style={{ fontSize: 24, opacity: focused ? 1 : 0.5 }}>{icons[name] || ''}</Text>;
};

function MainTabs() {
  const { colors } = useTheme();

  return (
    <Tab.Navigator
      initialRouteName="대시보드"
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => <TabBarIcon name={route.name} focused={focused} />,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: {
          backgroundColor: colors.cardBackground,
          borderTopColor: colors.border,
          borderTopWidth: 1,
        },
        headerStyle: {
          backgroundColor: colors.cardBackground,
          borderBottomColor: colors.border,
          borderBottomWidth: 1,
        },
        headerTintColor: colors.text,
        headerTitleStyle: {
          fontWeight: '700',
          fontFamily: 'Inter_700Bold',
          fontSize: 18,
        },
      })}>
      <Tab.Screen name="대시보드" component={DashboardScreen} />
      <Tab.Screen
        name="거래내역"
        component={TransactionScreen}
        listeners={({ navigation }) => ({
          tabPress: (e) => {
            // 탭 클릭 시 파라미터 초기화 (이상거래 필터 해제)
            e.preventDefault();
            navigation.navigate('거래내역', { filter: null });
          },
        })}
      />
      <Tab.Screen name="쿠폰함" component={CouponScreen} />
      <Tab.Screen name="더보기" component={MoreScreen} />
    </Tab.Navigator>
  );
}

function AuthStack() {
  const { colors } = useTheme();

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        cardStyle: { backgroundColor: colors.background }
      }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Signup" component={SignupScreen} />
    </Stack.Navigator>
  );
}

function AppContent() {
  const { colors, isDarkMode } = useTheme();
  const { user, loading } = useAuth();

  // 카카오 OAuth 콜백 처리 (웹 환경에서만)
  useEffect(() => {
    if (Platform.OS === 'web' && typeof window !== 'undefined' && window.location) {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const pathname = window.location.pathname;

      // code가 있고 로그인되지 않은 경우
      if (code && !user) {
        // URL에서 code 파라미터 제거
        window.history.replaceState({}, document.title, '/');

        // 회원가입 콜백인지 로그인 콜백인지 경로로 구분
        if (pathname.includes('/signup')) {
          // 카카오 회원가입 처리
          kakaoSignup(code).then(result => {
            if (!result.success) {
              alert('카카오 회원가입 실패: ' + result.error);
            }
          });
        } else {
          // 카카오 로그인 처리
          kakaoLogin(code).then(result => {
            if (!result.success) {
              alert('카카오 로그인 실패: ' + result.error);
            }
          });
        }
      }
    }
  }, [user]);

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background }}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={{ marginTop: 16, fontSize: 16, color: colors.text }}>로딩 중...</Text>
      </View>
    );
  }

  return (
    <NavigationContainer>
      <StatusBar style={isDarkMode ? 'light' : 'auto'} />
      {user ? (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="MainTabs" component={MainTabs} />
          <Stack.Screen
            name="분석"
            component={AnalysisScreen}
            options={{
              headerShown: true,
              headerTitle: '지출 분석',
              headerStyle: { backgroundColor: colors.cardBackground },
              headerTintColor: colors.text,
            }}
          />
          <Stack.Screen
            name="프로필"
            component={ProfileScreen}
            options={{
              headerShown: true,
              headerTitle: '프로필',
              headerStyle: { backgroundColor: colors.cardBackground },
              headerTintColor: colors.text,
            }}
          />
          <Stack.Screen
            name="설정"
            component={SettingsScreen}
            options={{
              headerShown: true,
              headerTitle: '앱 설정',
              headerStyle: { backgroundColor: colors.cardBackground },
              headerTintColor: colors.text,
            }}
          />
        </Stack.Navigator>
      ) : <AuthStack />}
    </NavigationContainer>
  );
}

export default function App() {
  console.log('[App] App component starting...');
  return (
    <ThemeProvider>
      <AuthProvider>
        <AISettingsProvider>
          <ToastProvider>
            <TransactionProvider>
              <AppContent />
            </TransactionProvider>
          </ToastProvider>
        </AISettingsProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
