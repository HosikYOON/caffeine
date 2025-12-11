"""
더미 데이터 생성 스크립트

2025-12-10: AWS RDS PostgreSQL용 테스트 데이터 생성
- 사용자: 기존 5명 활용
- 거래: 500건 (최근 6개월)
- 패턴: 시간대, 카테고리, 금액 다양화
"""

import psycopg2
from datetime import datetime, timedelta
import random

# RDS 연결 정보
DB_CONFIG = {
    'host': 'caffeine-database.c58og6ke6t36.ap-northeast-2.rds.amazonaws.com',
    'port': 5432,
    'user': 'postgres',
    'password': 'caffeineapprds',
    'database': 'postgres'
}

# 카테고리별 가맹점 템플릿
MERCHANTS = {
    1: [  # 외식
        '스타벅스 {}점', '투썸플레이스 {}점', '이디야커피 {}점',
        '맥도날드 {}점', '버거킹 {}점', 'KFC {}점',
        '공차 {}점', '할리스커피 {}점', '빽다방 {}점',
        '스시로 {}점', '아웃백 {}점', '제일제면소 {}점',
        '본죽 {}점', '김밥천국 {}점', '교촌치킨 {}점',
    ],
    2: [  # 교통
        '카카오택시', '우버택시', '타다',
        '서울교통카드', '지하철', '버스',
        'SK엔크린', 'GS칼텍스', '현대오일뱅크',
    ],
    3: [  # 쇼핑
        '쿠팡', '무신사', '29CM', 'W컨셉',
        '네이버쇼핑', 'SSG닷컴', '11번가',
        '올리브영 {}점', '다이소 {}점', '이마트 {}점',
    ],
    4: [  # 식료품
        'GS25 {}점', 'CU {}점', '세븐일레븐 {}점',
        '이마트 트레이더스', '코스트코', '롯데마트',
        '농협하나로마트', '홈플러스', '메가마트',
    ],
    5: [  # 생활
        '넷플릭스', '유튜브 프리미엄', '왓챠',
        'CGV {}점', '롯데시네마 {}점', '메가박스 {}점',
        '스포츠센터', 'YES24', '교보문고',
        '다이소', '이케아', '무인세탁소',
    ],
    6: [  # 주유
        'SK주유소 {}점', 'GS칼텍스 {}점', '현대오일뱅크 {}점',
        'S-OIL {}점', '알뜰주유소 {}점',
    ]
}

# 지역 리스트
LOCATIONS = ['강남', '역삼', '서초', '잠실', '홍대', '신촌', '이태원', '명동', '종로', '여의도', 
             '건대', '성수', '왕십리', '노원', '강북', '마포', '용산', '송파', '광진', '동대문']

# 카테고리별 평균 금액 및 표준편차
CATEGORY_AMOUNTS = {
    1: (8000, 5000),    # 외식: 평균 8,000원 ± 5,000원
    2: (15000, 10000),  # 교통: 평균 15,000원 ± 10,000원
    3: (50000, 30000),  # 쇼핑: 평균 50,000원 ± 30,000원
    4: (25000, 15000),  # 식료품: 평균 25,000원 ± 15,000원
    5: (15000, 10000),  # 생활: 평균 15,000원 ± 10,000원
    6: (60000, 20000),  # 주유: 평균 60,000원 ± 20,000원
}

# 시간대별 카테고리 확률 (아침, 점심, 저녁, 심야)
TIME_CATEGORY_PROB = {
    'morning': {1: 0.5, 2: 0.3, 4: 0.1, 5: 0.1},      # 아침: 외식(카페) 50%
    'lunch': {1: 0.6, 2: 0.2, 3: 0.1, 4: 0.1},        # 점심: 외식 60%
    'evening': {1: 0.4, 3: 0.3, 4: 0.2, 5: 0.1},      # 저녁: 외식/쇼핑
    'night': {5: 0.5, 1: 0.3, 3: 0.2},                # 심야: 생활/OTT
}

# 요일별 카테고리 확률
WEEKDAY_CATEGORY_PROB = {
    'weekday': {1: 0.3, 2: 0.3, 4: 0.2, 5: 0.1, 6: 0.1},
    'weekend': {1: 0.4, 3: 0.3, 5: 0.2, 6: 0.1},
}


def get_merchant_name(category_id):
    """카테고리에 맞는 랜덤 가맹점 생성"""
    template = random.choice(MERCHANTS.get(category_id, ['알 수 없음']))
    if '{}' in template:
        return template.format(random.choice(LOCATIONS))
    return template


def get_random_amount(category_id):
    """카테고리별 랜덤 금액 생성"""
    mean, std = CATEGORY_AMOUNTS.get(category_id, (10000, 5000))
    amount = int(random.gauss(mean, std))
    # 최소 1,000원, 100원 단위로 반올림
    return max(1000, round(amount / 100) * 100)


def get_category_by_time(dt):
    """시간대에 따른 카테고리 선택"""
    hour = dt.hour
    is_weekend = dt.weekday() >= 5
    
    # 시간대 결정
    if 6 <= hour < 11:
        time_slot = 'morning'
    elif 11 <= hour < 14:
        time_slot = 'lunch'
    elif 14 <= hour < 22:
        time_slot = 'evening'
    else:
        time_slot = 'night'
    
    # 시간대별 확률 가져오기
    probs = TIME_CATEGORY_PROB.get(time_slot, {1: 0.4, 2: 0.2, 3: 0.2, 4: 0.1, 5: 0.1})
    
    # 주말 보정
    if is_weekend:
        weekend_probs = WEEKDAY_CATEGORY_PROB['weekend']
        # 시간대와 주말 확률 혼합
        probs = {k: (probs.get(k, 0) + weekend_probs.get(k, 0)) / 2 for k in set(probs) | set(weekend_probs)}
    
    # 확률 기반 선택
    categories = list(probs.keys())
    weights = list(probs.values())
    return random.choices(categories, weights=weights)[0]


def generate_transaction_time(base_date, user_id):
    """사용자별 거래 시간 생성 (생활 패턴 반영)"""
    # 사용자별 선호 시간대
    user_patterns = {
        1: (7, 22),   # 아침형 인간
        2: (9, 22),   # 일반형
        3: (10, 23),  # 저녁형 인간
        4: (8, 21),   # 규칙형
        5: (11, 23),  # 야행성
    }
    
    start_hour, end_hour = user_patterns.get(user_id, (9, 22))
    
    # 시간 범위 보정 (0-23)
    start_hour = max(0, min(23, start_hour))
    end_hour = max(0, min(23, end_hour))
    
    # 랜덤 시간 생성
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return base_date.replace(hour=hour, minute=minute, second=second)


def generate_description(category_id, merchant):
    """거래 설명 생성"""
    descriptions = {
        1: ['점심', '저녁', '간식', '커피', '디저트', '회식', '데이트', '혼밥'],
        2: ['출근', '퇴근', '미팅', '외근', '주유', '주차'],
        3: ['생필품', '의류', '전자기기', '선물', '취미', '인테리어'],
        4: ['장보기', '식료품', '야식', '과일', '간식거리'],
        5: ['구독', '영화', '독서', '운동', '취미', '여가'],
        6: ['주유', '세차', '정비'],
    }
    
    desc_list = descriptions.get(category_id, [''])
    if random.random() < 0.7:  # 70% 확률로 설명 추가
        return random.choice(desc_list)
    return None


def is_anomaly(amount, category_id, hour):
    """이상거래 판단 (간단한 룰 기반)"""
    mean, std = CATEGORY_AMOUNTS.get(category_id, (10000, 5000))
    
    # 1. 금액이 평균의 3배 이상
    if amount > mean * 3:
        return True, 85.0
    
    # 2. 심야 시간 (2-5시) + 고액
    if 2 <= hour <= 5 and amount > 50000:
        return True, 75.0
    
    # 3. 외식인데 20만원 이상
    if category_id == 1 and amount > 200000:
        return True, 90.0
    
    return False, 0.0


def generate_dummy_data(num_transactions=500):
    """더미 데이터 생성"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print(f"🎲 {num_transactions}건의 거래 데이터 생성 시작...")
    
    # 기존 거래 삭제 (선택사항)
    # cur.execute("DELETE FROM transactions WHERE id > 8")
    
    # 6개월 전부터 현재까지
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    user_ids = [1, 2, 3, 4, 5]
    transactions_per_user = num_transactions // len(user_ids)
    
    created_count = 0
    anomaly_count = 0
    
    for user_id in user_ids:
        print(f"  사용자 {user_id} 데이터 생성 중...")
        
        # 각 사용자별 거래 생성
        for i in range(transactions_per_user):
            # 랜덤 날짜 생성
            random_days = random.randint(0, 180)
            transaction_date = start_date + timedelta(days=random_days)
            
            # 거래 시간 생성
            transaction_time = generate_transaction_time(transaction_date, user_id)
            
            # 카테고리 선택
            category_id = get_category_by_time(transaction_time)
            
            # 가맹점 이름
            merchant = get_merchant_name(category_id)
            
            # 금액
            amount = get_random_amount(category_id)
            
            # 설명
            description = generate_description(category_id, merchant)
            
            # 이상거래 체크
            is_anom, anom_score = is_anomaly(amount, category_id, transaction_time.hour)
            
            # 데이터 삽입
            cur.execute('''
                INSERT INTO transactions (
                    user_id, category_id, amount, currency, 
                    merchant_name, description, status, 
                    transaction_time, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ''', (
                user_id, category_id, amount, 'KRW',
                merchant, description, 'completed',
                transaction_time
            ))
            
            # 이상거래면 anomalies 테이블에도 추가
            if is_anom:
                tx_id = cur.fetchone()
                cur.execute('''
                    INSERT INTO anomalies (
                        transaction_id, user_id, severity, reason, is_resolved
                    ) VALUES (currval('transactions_id_seq'), %s, %s, %s, FALSE)
                ''', (
                    user_id,
                    'high' if anom_score > 80 else 'medium',
                    f'비정상적인 금액 또는 시간대 (점수: {anom_score})'
                ))
                anomaly_count += 1
            
            created_count += 1
            
            if (created_count % 100) == 0:
                conn.commit()
                print(f"    {created_count}건 생성 완료...")
    
    # 최종 커밋
    conn.commit()
    
    # 결과 확인
    cur.execute('SELECT COUNT(*) FROM transactions')
    total = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM anomalies')
    total_anomalies = cur.fetchone()[0]
    
    print(f"\n✅ 데이터 생성 완료!")
    print(f"   총 거래: {total}건")
    print(f"   이상거래: {total_anomalies}건 ({total_anomalies/total*100:.1f}%)")
    print(f"\n📊 카테고리별 통계:")
    
    cur.execute('''
        SELECT c.name, COUNT(*) as cnt, AVG(t.amount) as avg_amount
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        GROUP BY c.name
        ORDER BY cnt DESC
    ''')
    
    for row in cur.fetchall():
        print(f"   {row[0]}: {row[1]}건 (평균 {int(row[2]):,}원)")
    
    conn.close()


if __name__ == '__main__':
    generate_dummy_data(500)
