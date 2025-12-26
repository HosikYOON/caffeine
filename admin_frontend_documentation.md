# Admin Frontend Technical Documentation (`21_frontend_admin`)

**Last Updated:** 2024-12-24
**Project:** Caffeine Admin Dashboard

---

## 1. 프로젝트 개요 (Executive Summary)

`21_frontend_admin`은 **Caffeine** 서비스의 중앙 관제 시스템입니다.
흩어져 있는 사용자 거래 데이터와 시스템 상태를 **실시간으로 통합/시각화**하여, 운영자가 직관적으로 시스템 현황을 파악하고 제어할 수 있도록 돕습니다.

높은 안정성과 성능을 보장하기 위해 **Next.js 16 (App Router)** 과 **React 19**의 최신 기능을 도입하였으며, **TypeScript**를 통해 견고한 타입 시스템을 구축했습니다.

---

## 2. 기술 스택 심층 분석 (Tech Stack Deep Dive)

### 2.1. Core Framework: Next.js 16 & React 19
*   **Next.js 16 (App Router)**
    *   **선정 이유**: 기존 Pages Router의 복잡성을 해소하고, **Server Component**와 **Client Component**의 명확한 분리를 통해 번들 사이즈를 최적화하기 위함.
    *   **활용**: `layout.tsx`를 통한 공통 레이아웃 관리, `loading.tsx`를 통한 Suspense 기반 로딩 처리.
*   **React 19**
    *   **선정 이유**: 최신 Hook (`useActionState`, `useOptimistic` 등) 지원 및 렌더링 성능 개선.
    *   **활용**: `useState`, `useEffect`, `useMemo`를 복합적으로 사용하여 복잡한 필터링 로직과 비동기 데이터 처리를 효율적으로 구현.

### 2.2. UI/UX: Tailwind CSS 4 & Recharts
*   **Tailwind CSS 4**
    *   **특징**: 빌드 타임에 사용된 클래스만 CSS로 생성하는 JIT(Just-In-Time) 컴파일러 내장.
    *   **장점**: 별도의 CSS 파일 관리 불필요, `clsx` 및 `tailwind-merge`와 결합하여 동적 스타일링 용이.
*   **Recharts**
    *   **특징**: React 컴포넌트 기반의 차트 라이브러리 (D3.js 기반).
    *   **활용**: 데이터 변경 시 애니메이션 지원, ResponsiveContainer를 통한 반응형 차트 구현.

### 2.3. State & Logic: TypeScript & Custom Hooks
*   **TypeScript 5**: API 응답 타입(`interface User`, `interface Transaction`)을 엄격히 정의하여 `undefined` 참조 오류 방지.
*   **Context API**: 전역 인증 상태(`AuthContext`) 관리에 사용.

---

## 3. 핵심 기능 구현 상세 (Implementation Details)

### 3.1. API 클라이언트 아키텍처 (Layered Architecture)

API 호출의 중복을 막고 유지보수성을 높이기 위해 **Base Client - Service Layer** 구조를 채택했습니다.

#### [Core] `src/api/baseClient.ts`
`fetch` API를 래핑하여 **Timeout 처리**와 **JWT 토큰 자동 주입** 기능을 수행합니다.

```typescript
// src/api/baseClient.ts (핵심 로직 발췌)

async function fetchWithTimeout(url: string, options: FetchOptions = {}) {
    const { timeout = 30000, headers = {}, ...fetchOptions } = options;

    // 1. AbortController를 이용한 Timeout 구현
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    // 2. JWT 토큰 자동 주입 (Interceptor 패턴)
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
    const authHeaders: Record<string, string> = {};
    if (token) {
        authHeaders['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, {
            ...fetchOptions,
            headers: {
                ...headers,
                ...authHeaders, // 기존 헤더와 병합
            },
            signal: controller.signal,
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}
```

### 3.2. 인증 시스템 (`Authentication Flow`)

보안을 위해 **OAuth2PasswordRequestForm** 표준을 준수하며, 클라이언트 사이드에서 세션을 관리합니다.

#### [Hook] `src/hooks/useAuth.ts`
앱 실행 시 토큰 유효성을 검사하고, 사용자 정보를 전역 상태로 관리합니다.

```typescript
// src/hooks/useAuth.ts

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);

    // 초기화 로직: 새로고침 시에도 로그인 유지
    useEffect(() => {
        const initAuth = async () => {
            const token = localStorage.getItem('accessToken');
            if (token) {
                try {
                    // 토큰이 있으면 사용자 정보 조회
                    apiClient.get('/users/me')
                        .then(userData => setUser(userData))
                        .catch(() => logout()); // 실패 시 로그아웃
                } catch (error) {
                    logout();
                }
            } 
            // ...리다이렉트 로직
        };
        initAuth();
    }, []);

    // 로그인 함수
    const login = (token: string, refreshToken: string) => {
        localStorage.setItem('accessToken', token);
        localStorage.setItem('refreshToken', refreshToken);
        
        // 로그인 성공 직후 사용자 정보 fetch
        apiClient.get('/users/me').then(userData => {
            setUser(userData);
            router.push('/');
        });
    };
    
    // ...
}
```

### 3.3. 고성능 데이터 시각화 (`Data Visualization`)

대량의 거래 데이터를 클라이언트에서 실시간으로 필터링하고 차트에 반영합니다. 성능 저하를 막기 위해 `useMemo`를 적극 활용했습니다.

#### [Component] `src/components/AdminIntegratedAnalysis.jsx`

```javascript
// src/components/AdminIntegratedAnalysis.jsx

const AdminIntegratedAnalysis = () => {
    // 상태 정의
    const [transactions, setTransactions] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState(null);

    // 1. 필터링 로직 최적화 (useMemo)
    // 의존성 배열([transactions, searchQuery...])이 변할 때만 재연산
    const filteredTransactions = useMemo(() => {
        let filtered = transactions;

        if (searchQuery) {
            // 검색어 필터링
            filtered = filtered.filter(tx => 
                tx.merchant.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }
        if (selectedCategory) {
            // 차트 클릭 시 카테고리 필터링
            filtered = filtered.filter(tx => tx.category === selectedCategory);
        }
        return filtered;
    }, [transactions, searchQuery, selectedCategory]);

    // 2. 차트 데이터 가공 (Raw Data -> Chart Data)
    const categoryData = useMemo(() => {
        const categoryMap = {};
        filteredTransactions.forEach(tx => {
            if (!categoryMap[tx.category]) categoryMap[tx.category] = 0;
            categoryMap[tx.category] += tx.amount;
        });
        // Recharts에서 요구하는 배열 형태({name, value})로 변환
        return Object.keys(categoryMap).map(category => ({
            name: category,
            value: categoryMap[category],
            color: CATEGORY_COLORS[category]
        }));
    }, [filteredTransactions]);

    return (
        // 3. 차트 렌더링 (클릭 이벤트 연동)
        <ResponsiveContainer width="100%" height={300}>
            <PieChart>
                <Pie 
                    data={categoryData} 
                    dataKey="value"
                    onClick={(data) => setSelectedCategory(data.name)} // Drill-down 기능
                />
            </PieChart>
        </ResponsiveContainer>
    );
};
```

---

## 4. 트러블슈팅 사례 (Troubleshooting)

### 4.1. Double Prefix Issue (API Path 404 Error)

*   **현상**: 로그인 시도 시 `POST http://localhost:8001/api/api/users/login 404 (Not Found)` 에러 발생.
*   **원인**: 
    1.  환경변수 `NEXT_PUBLIC_API_URL`이 `http://localhost:8001/api`로 설정됨.
    2.  코드 내에서 `apiClient.post('/api/users/login')`과 같이 하드코딩된 접두사를 추가.
    3.  결과적으로 `/api`가 두 번 중복됨.
*   **해결**: **DRY (Don't Repeat Yourself)** 원칙 적용. Base URL 관리는 `baseClient.ts`에 위임하고, 비즈니스 로직에서는 순수 엔드포인트만 관리하도록 수정.

**[Before] 수정 전 코드**
```typescript
// 중복된 접두사 사용
return apiClient.get('/api/users/me'); 
// 결합 결과: http://localhost:8001/api/api/users/me (404)
```

**[After] 수정 후 코드**
```typescript
// 접두사 제거
return apiClient.get('/users/me');
// 결합 결과: http://localhost:8001/api/users/me (200 OK)
```

---

## 5. 실행 및 배포 가이드 (Deployment)

### 개발 환경 (Local)
```bash
cd 21_frontend_admin
npm install
npm run dev
```

### Docker 환경 (Production-like)
```bash
# 프로젝트 루트에서 실행
docker-compose --env-file .env.local up --build -d
```
*   **포트**: Frontend(3000), Backend(8000/8001)
*   **네트워크**: `caf_network` 브리지 네트워크를 통해 컨테이너 간 통신.

