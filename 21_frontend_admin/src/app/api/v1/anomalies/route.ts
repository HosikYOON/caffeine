import { NextResponse } from 'next/server';

export async function GET() {
    return NextResponse.json([
        {
            id: 1,
            category: '해외결제',
            amount: 1250000,
            date: '2024-11-29 03:45',
            reason: '평소 거래 패턴과 다름 (심야 시간 + 고액)',
            riskLevel: '위험',
            status: 'pending',
            userId: 'user_001',
            userName: '김철수'
        },
        {
            id: 2,
            category: '게임',
            amount: 55000,
            date: '2024-11-29 14:20',
            reason: '단시간 다회 결제 시도 (5분 내 3회)',
            riskLevel: '경고',
            status: 'pending',
            userId: 'user_042',
            userName: '이영희'
        },
        {
            id: 3,
            category: '편의점',
            amount: 250000,
            date: '2024-11-28 23:10',
            reason: '카테고리 평균 대비 고액 결제',
            riskLevel: '주의',
            status: 'approved',
            userId: 'user_103',
            userName: '박민수'
        },
    ]);
}
