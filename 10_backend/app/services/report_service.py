"""
리포트 생성 서비스

주간/월간 소비 데이터를 집계하고 리포트를 생성합니다.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model.transaction import Transaction, Category
from app.db.model.user import User

logger = logging.getLogger(__name__)



from app.services.ai_service import call_gemini_api, generate_report_prompt
import os
import io
import matplotlib.pyplot as plt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak

# 한글 폰트 설정 (윈도우 기본 맑은 고딕)
FONT_PATH = "C:\\Windows\\Fonts\\malgun.ttf"
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('MalgunGothic', FONT_PATH))
    pdfmetrics.registerFont(TTFont('MalgunGothicBold', "C:\\Windows\\Fonts\\malgunbd.ttf"))
else:
    # 폰트가 없을 경우 기본 폰트 사용 (한글 깨짐 주의)
    logger.warning("Korean font not found. PDF might have encoding issues.")

def generate_category_pie_chart(top_categories: list) -> io.BytesIO:
    """
    카테고리 지출 비중을 도넛형 파이 차트로 생성합니다.
    """
    if not top_categories:
        return None
        
    labels = [c['name'] for c in top_categories]
    sizes = [c['amount'] for c in top_categories]
    
    # 세련된 인디고/슬레이트 컬러 팔레트
    colors_palette = ['#4338ca', '#6366f1', '#818cf8', '#a5b4fc', '#e2e8f0']
    
    fig, ax = plt.subplots(figsize=(10, 4)) # Wider for landscape
    
    # 폰트 설정 (맑은 고딕)
    plt.rcParams['font.family'] = 'Malgun Gothic'
    
    # 파이 차트 생성 (도넛 형태)
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels, 
        autopct='%1.1f%%', 
        startangle=140, 
        colors=colors_palette,
        pctdistance=0.85,
        explode=[0.05] + [0] * (len(top_categories) - 1), # 가장 큰 조각 살짝 강조
        textprops={'fontsize': 10, 'color': '#1e293b'}
    )
    
    # 도넛 센터 구멍
    centre_circle = plt.Circle((0,0), 0.70, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    # 텍스트 스타일링
    for text in texts:
        text.set_color('#475569')
        text.set_weight('bold')
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_weight('bold')
        
    ax.axis('equal')  # 원형 유지
    plt.tight_layout()
    
    # 메모리 버퍼에 저장
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, transparent=True)
    img_buffer.seek(0)
    plt.close()
    
    return img_buffer

def generate_daily_bar_chart(daily_data: list) -> io.BytesIO:
    """
    일별 지출 데이터를 막대 그래프로 생성합니다.
    """
    if not daily_data:
        return None
        
    # 날짜 포맷팅 (예: 01/01)
    dates = [d['date'].strftime('%m/%d') for d in daily_data]
    amounts = [d['amount'] for d in daily_data]
    
    # 그래프 스타일 설정 (가로형 슬라이드에 맞춰 더 넓게)
    fig, ax = plt.subplots(figsize=(10, 4))
    plt.rcParams['font.family'] = 'Malgun Gothic'
    
    # 막대 그래프 생성
    bars = ax.bar(dates, amounts, color='#e0e7ff', width=0.6)

    # 값 표시
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 500, f'{int(yval):,}', ha='center', va='bottom', fontsize=8, color='#475569')

    ax.set_title('일별 지출 추이', fontsize=14, color='#1e293b', pad=15)
    ax.set_ylabel('금액 (원)', fontsize=10, color='#475569')
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=45, ha='right', fontsize=9)
    ax.tick_params(axis='y', labelsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ','))) # y축 금액 콤마
    ax.set_facecolor('#f8fafc') # 배경색
    ax.grid(axis='y', linestyle='--', alpha=0.7) # y축 그리드
    
    plt.tight_layout()
    
    # 메모리 버퍼에 저장
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, transparent=True)
    img_buffer.seek(0)
    plt.close()
    
    return img_buffer

def generate_report_pdf(report_type: str, report_data: Dict[str, Any], output_path: str):
    """
    리포트 데이터를 바탕으로 '프레젠테이션 슬라이드 덱(Slide Deck)' 형태의 PDF를 생성합니다.
    (가로형 A4, 큰 폰트, 페이지 넘김 구조)
    """
    # 가로형 A4 설정
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), topMargin=40, bottomMargin=40, leftMargin=50, rightMargin=50)
    styles = getSampleStyleSheet()
    
    # --- Presentation Styles Definition ---
    # 슬라이드용 큰 폰트 스타일 정의
    
    # 1. Slide Title (Main Cover)
    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Title'],
        fontName='MalgunGothicBold',
        fontSize=42, # Presentation Scale
        leading=50,
        alignment=1, # Center
        spaceAfter=30,
        textColor=colors.HexColor("#1e293b")
    )
    
    # 2. Slide Heading (Page Title)
    slide_heading_style = ParagraphStyle(
        'SlideHeading',
        parent=styles['Heading1'],
        fontName='MalgunGothicBold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#4338ca"), # Indigo Primary
        spaceAfter=20,
        spaceBefore=10
    )
    
    # 3. Slide Body (Main Text)
    slide_body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='MalgunGothic',
        fontSize=14, # 가독성 확보
        leading=22,
        spaceAfter=12
    )

    # 4. Slide Bullet (List)
    slide_bullet_style = ParagraphStyle(
        'SlideBullet',
        parent=slide_body_style,
        leftIndent=24,
        firstLineIndent=-24,
        spaceAfter=8
    )

    # 5. Centered Body
    slide_center_style = ParagraphStyle(
        'SlideCenter',
        parent=slide_body_style,
        alignment=1
    )
    
    elements = []
    
    # --- SLIDE 1: Title Page ---
    elements.append(Spacer(1, 100))
    elements.append(Paragraph(f"Caffeine {report_type}", title_style))
    elements.append(Paragraph("Strategic Business Report", 
        ParagraphStyle('Sub', parent=title_style, fontSize=24, textColor=colors.HexColor("#64748b"))))
    elements.append(Spacer(1, 40))
    elements.append(HRFlowable(width="60%", thickness=2, color=colors.HexColor("#4338ca")))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Period: {report_data['period_start']} ~ {report_data['period_end']}", 
        ParagraphStyle('Period', parent=slide_center_style, fontSize=16, textColor=colors.HexColor("#475569"))))
    
    elements.append(PageBreak()) # Next Slide
    
    # --- SLIDE 2: Key Metrics & Financial Summary ---
    elements.append(Paragraph("1. Financial Overview (핵심 지표)", slide_heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=20))
    
    # Summary Table
    change_rate = report_data.get('change_rate', 0)
    hex_color_str = "#e53e3e" if change_rate > 0 else "#38a169" if change_rate < 0 else "#475569"
    
    summary_data = [
        [Paragraph("총 소비 금액", slide_center_style), Paragraph("총 거래 건수", slide_center_style), Paragraph("전기 대비 변동", slide_center_style)],
        [
            Paragraph(f"KRW {int(report_data['total_amount']):,}", 
                      ParagraphStyle('BigNum', parent=slide_center_style, fontSize=24, fontName='MalgunGothicBold')),
            Paragraph(f"{report_data['transaction_count']}건", 
                      ParagraphStyle('BigNum', parent=slide_center_style, fontSize=24, fontName='MalgunGothicBold')),
            Paragraph(f"<font color='{hex_color_str}'>{change_rate}%</font>", 
                      ParagraphStyle('BigNum', parent=slide_center_style, fontSize=24, fontName='MalgunGothicBold'))
        ]
    ]
    
    t_summary = Table(summary_data, colWidths=[200, 200, 200])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
    ]))
    elements.append(t_summary)
    
    # Highlights (Max Transaction)
    elements.append(Spacer(1, 30))
    if report_data.get('max_transaction'):
        max_tx = report_data['max_transaction']
        elements.append(Paragraph(f"💡 <b>최대 지출 발생</b>: {max_tx['merchant_name']} ({int(max_tx['amount']):,}원) - {max_tx['category']}", 
                                  ParagraphStyle('Highlight', parent=slide_body_style, backColor=colors.HexColor("#fff7ed"), borderPadding=10, borderRadius=8)))
    
    # Add Daily Chart here for quick view
    if report_data.get('daily_spending'):
        elements.append(Spacer(1, 20))
        daily_chart = generate_daily_bar_chart(report_data['daily_spending'])
        if daily_chart:
            from reportlab.platypus import Image
            # 가로형에 맞춰 더 넓게 배치
            img = Image(daily_chart, width=600, height=220) 
            elements.append(img)
            
    elements.append(PageBreak()) # Next Slide

    # --- SLIDE 3: Category Analysis ---
    elements.append(Paragraph("2. Category & Spending Breakdown (지출 구성)", slide_heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=20))
    
    # Layout: Left (Chart) / Right (Table)? ReportLab doesn't do columns easily without Frames.
    # Just stack them for simplicity in Slide format.
    
    if report_data.get('top_categories'):
        # 1. Pie Chart
        chart_buffer = generate_category_pie_chart(report_data['top_categories'])
        if chart_buffer:
            from reportlab.platypus import Image
            img = Image(chart_buffer, width=400, height=300)
            img.hAlign = 'CENTER' # Centered
            elements.append(img)
            elements.append(Spacer(1, 20))
            
        # 2. Top Categories Table
        cat_data = [[
            Paragraph("<b>순위</b>", slide_center_style), 
            Paragraph("<b>카테고리</b>", slide_center_style), 
            Paragraph("<b>금액</b>", slide_center_style), 
            Paragraph("<b>비중</b>", slide_center_style)
        ]]
        for i, cat in enumerate(report_data['top_categories'], 1):
            if i > 5: break # Top 5 only
            cat_data.append([
                Paragraph(str(i), slide_center_style),
                Paragraph(cat['name'], slide_center_style),
                Paragraph(f"{int(cat['amount']):,}원", slide_center_style),
                Paragraph(f"{cat['percent']:.1f}%", slide_center_style)
            ])
            
        t_cat = Table(cat_data, colWidths=[60, 200, 200, 100])
        t_cat.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f8fafc")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(t_cat)
        
    elements.append(PageBreak()) # Next Slide
    
    # --- SLIDE 4 ~ N: AI Strategy Insights ---
    # AI 내용을 파싱하여 슬라이드별로 분배
    ai_raw_content = report_data.get('ai_insight', "")
    
    # 헤드라인 추출
    import re
    headline_text = ""
    headline_match = re.search(r'(?:#\s*)?\\?\[HEADLINE\]\s*(.*)', ai_raw_content)
    if headline_match:
        headline_text = headline_match.group(1).split('\n')[0].strip().strip('"')
        ai_raw_content = ai_raw_content.replace(headline_match.group(0), "").strip()

    # 4-1. Headline Slide (Impact)
    if headline_text:
        elements.append(Spacer(1, 100))
        elements.append(Paragraph("AI Business Insight", 
            ParagraphStyle('SuperTitle', parent=title_style, fontSize=24, textColor=colors.HexColor("#6366f1"))))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f'"{headline_text}"', 
            ParagraphStyle('HeadlineMain', parent=title_style, fontSize=36, leading=46, textColor=colors.HexColor("#1e293b"))))
        elements.append(PageBreak())

    # 4-2. Content Slides
    # AI 텍스트 라인 파싱 -> '## ' 헤더를 만나면 PageBreak
    
    lines = ai_raw_content.split('\n')
    
    # 테이블 파싱용
    table_buffer = []
    
    current_slide_elements = [] # 현재 슬라이드에 담길 요소들
    first_header_seen = False

    for line in lines:
        stripped_line = line.strip()
        
        # --- 테이블 처리 로직 (기존과 동일) ---
        if stripped_line.startswith('|'):
            table_buffer.append(stripped_line)
            continue
        
        if table_buffer and not stripped_line.startswith('|'): # 테이블 버퍼에 내용이 있는데 일반 라인을 만난 경우
            # 테이블 가공 및 렌더링
            table_rows = []
            for row in table_buffer:
                 if '---' in row: continue
                 cells = [c.strip() for c in row.split('|') if c.strip()]
                 if cells:
                     # 테이블 셀 폰트도 조금 키움 (11pt)
                     p_cells = [Paragraph(c, ParagraphStyle('TC', parent=slide_body_style, fontSize=11)) for c in cells]
                     table_rows.append(p_cells)
            
            if table_rows:
                # Landscape 넓이 활용 (700px)
                col_w = 700 / len(table_rows[0])
                t = Table(table_rows, colWidths=[col_w] * len(table_rows[0]))
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0e7ff")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#4338ca")),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                    ('PADDING', (0,0), (-1,-1), 8)
                ]))
                current_slide_elements.append(t)
                current_slide_elements.append(Spacer(1, 15))
            table_buffer = [] # 초기화

        if not stripped_line:
            continue
            
        # --- 헤더 감지 -> 새 슬라이드 ---
        if stripped_line.startswith('## '):
            # 이전 슬라이드 요소들 확정 (첫 헤더가 아니면 PageBreak 추가)
            if first_header_seen:
                elements.extend(current_slide_elements)
                elements.append(PageBreak())
                current_slide_elements = []
            
            first_header_seen = True
            
            header_text = stripped_line.replace('## ', '').strip()
            # 슬라이드 제목 스타일
            current_slide_elements.append(Paragraph(header_text, slide_heading_style))
            current_slide_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=20))
            
        elif stripped_line.startswith('# '): # 혹시 모를 H1
             pass # 무시하거나 일반 텍스트로 처리
             
        # --- 리스트 및 본문 ---
        else:
            # 강조 문법 처리 (** **)
            import re
            accent_color = "#4338ca"
            line_content = re.sub(r'\*\*(.*?)\*\*', f'<font color="{accent_color}"><b>\\1</b></font>', stripped_line)
            
            if stripped_line.startswith('- ') or stripped_line.startswith('* '):
                 content = line_content[2:]
                 current_slide_elements.append(Paragraph(f"• {content}", slide_bullet_style))
            else:
                 current_slide_elements.append(Paragraph(line_content, slide_body_style))

    # 마지막 슬라이드 요소 추가
    if current_slide_elements:
        elements.extend(current_slide_elements)
        
    # --- Footer Slide ---
    elements.append(PageBreak())
    elements.append(Spacer(1, 200))
    elements.append(Paragraph("End of Report", 
        ParagraphStyle('End', parent=title_style, fontSize=24, textColor=colors.HexColor("#cbd5e1"))))
    elements.append(Paragraph("Generative AI Powered Business Intelligence", 
        ParagraphStyle('EndSub', parent=slide_center_style, fontSize=12, textColor=colors.HexColor("#94a3b8"))))

    # Build PDF
    doc.build(elements)
    logger.info(f"Slide Deck PDF generated: {output_path}")

def generate_report_html_slide(report_data: Dict[str, Any], title: str = "Monthly Business Review") -> str:
    """
    CEO/C-Level 대상의 프리미엄 전략 보고서를 HTML Slide Deck으로 생성합니다. (Light Theme, 7 Slides)
    
    Args:
        report_data: 리포트 데이터
        title: 리포트 타이틀 (예: Monthly Business Review, Weekly Business Review)
    """
    # 1. 데이터 전처리
    change_rate = report_data.get('change_rate', 0)
    change_color = "#e53e3e" if change_rate > 0 else "#2f855a" if change_rate < 0 else "#718096"
    arrow = "▲" if change_rate > 0 else "▼" if change_rate < 0 else "-"
    
    total_amount = int(report_data['total_amount'])
    tx_count = report_data['transaction_count']
    avg_ticket = int(total_amount / tx_count) if tx_count else 0
    
    max_tx = report_data.get('max_transaction', {})
    max_tx_desc = f"{max_tx.get('merchant_name','-')} ({int(max_tx.get('amount',0)):,}원)"
    
    # 2. AI 인사이트 파싱 (4개 섹션)
    ai_raw = report_data.get('ai_insight', "")
    import re
    import markdown
    
    sections = {
        "exec_summary": r"## 1\. Executive Summary(.*?)(?=## 2\.|$)",
        "b2c_insight": r"## 2\. B2C Consumer Insight(.*?)(?=## 3\.|$)",
        "b2b_strategy": r"## 3\. B2B Partnership Strategy(.*?)(?=## 4\.|$)",
        "metrics": r"## 4\. Partnership Metrics(.*?)(?=$)"
    }
    
    parsed_content = {}
    for key, pattern in sections.items():
        match = re.search(pattern, ai_raw, re.DOTALL)
        if match:
            # Markdown -> HTML 변환
            html_part = markdown.markdown(match.group(1).strip(), extensions=['tables'])
            parsed_content[key] = html_part
        else:
            parsed_content[key] = "<p>데이터 부족으로 분석이 생략되었습니다.</p>"

    # 3. HTML 템플릿 (Refined Light Mode Theme - White/Blue/Black)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Caffeine Strategic Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {{
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --text-primary: #1a202c; /* Black (Dark Gray) */
            --text-secondary: #4a5568;
            --accent: #2563eb; /* Tech Blue */
            --accent-light: #eff6ff; /* Very Light Blue */
            --border: #e2e8f0;
            --success: #2f855a;
            --danger: #e53e3e;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            overflow-x: hidden;
            line-height: 1.6;
        }}
        .slide {{
            width: 100vw; height: 100vh;
            max-width: 1280px; max-height: 720px;
            margin: 0 auto;
            position: relative;
            padding: 50px 70px;
            display: flex; flex-direction: column;
            border-bottom: 2px solid var(--border);
            page-break-after: always;
            background: #fff;
        }}
        
        /* Typography Rules for Readability */
        h1 {{ font-family: 'Poppins', sans-serif; font-size: 3.5rem; font-weight: 800; line-height: 1.1; margin-bottom: 20px; color: #000; letter-spacing: -1px; word-break: keep-all; }}
        h2 {{ font-family: 'Poppins', sans-serif; font-size: 2.2rem; font-weight: 700; color: #000; margin-bottom: 30px; display: flex; align-items: center; gap: 12px; word-break: keep-all; }}
        h3 {{ font-size: 1.4rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 15px; word-break: keep-all; }}
        
        /* Body Text Alignment & Constraints */
        p, li {{ 
            font-size: 1.15rem; 
            line-height: 1.8; /* 줄 간격 확대 */
            color: #2d3748; 
            list-style-position: outside; /* 들여쓰기 정렬 */
            word-break: keep-all; 
            text-align: left; /* 좌측 정렬로 변경 (가독성 UP) */
            letter-spacing: -0.02em; /* 자간 축소 */
            margin-bottom: 15px;
        }}
        li {{ margin-left: 20px; }}
        ul {{ max-width: 950px; }} /* 텍스트 라인 길이 제한 */
        
        /* Components */
        .badge {{ background: var(--accent-light); color: var(--accent); padding: 6px 16px; border-radius: 30px; font-size: 0.9rem; font-weight: 700; display: inline-block; margin-bottom: 20px; }}
        .header-line {{ width: 60px; height: 6px; background: var(--accent); margin-bottom: 40px; border-radius: 3px; }}
        
        /* KPI Cards */
        .kpi-container {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-top: 40px; }}
        .kpi-card {{ background: var(--bg-secondary); padding: 30px; border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .kpi-title {{ font-size: 0.95rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 15px; }}
        .kpi-value {{ font-family: 'Poppins', sans-serif; font-size: 2.5rem; font-weight: 700; color: #000; }}
        .kpi-sub {{ font-size: 0.9rem; margin-top: 10px; font-weight: 500; display: flex; align-items: center; gap: 4px; }}
        
        /* Tables (Sophisticated Look) */
        table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 20px; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
        th {{ background: #f1f5f9; text-align: left; padding: 20px; font-weight: 700; color: #334155; border-bottom: 1px solid var(--border); letter-spacing: 0.5px; }}
        td {{ padding: 20px; border-bottom: 1px solid var(--border); color: #1a202c; font-size: 1.05rem; background: #fff; }}
        tr:last-child td {{ border-bottom: none; }}
        
        /* Visual Elements */
        .pie-container {{ display: flex; align-items: center; justify-content: center; height: 400px; gap: 60px; }}
        .content-box {{ background: var(--bg-secondary); padding: 40px 50px; border-radius: 20px; border-left: 6px solid var(--accent); height: 100%; overflow-y: auto; }}
        .content-box strong {{ color: #1a202c; font-weight: 700; background: linear-gradient(120deg, #dbeafe 0%, #dbeafe 100%); background-repeat: no-repeat; background-size: 100% 40%; background-position: 0 88%; padding: 0 4px; }}
        
        .footer-page {{ position: absolute; bottom: 40px; right: 60px; font-size: 0.9rem; color: #cbd5e0; font-weight: 600; }}
    </style>
</head>
<body>

    <!-- Slide 1: Title -->
    <div class="slide" style="justify-content: center;">
        <span class="badge">CONFIDENTIAL • STRATEGIC REPORT</span>
        <h1>Vertex AI<br>Command Center</h1>
        <div class="header-line"></div>
        <p style="font-size: 1.5rem; color: var(--text-secondary);">{title}<br>{report_data['period_start']} — {report_data['period_end']}</p>
        <div style="margin-top: 60px; display: flex; gap: 20px;">
             <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--accent);">
                <i data-lucide="shield-check"></i> Verified by Vertex AI
             </div>
        </div>
        <div class="footer-page">01</div>
    </div>

    <!-- Slide 2: Executive Summary -->
    <div class="slide">
        <span class="badge">EXEC SUMMARY</span>
        <h2><i data-lucide="activity"></i> Management Brief</h2>
        <div class="content-box">
            {parsed_content['exec_summary']}
        </div>
        <div class="footer-page">02</div>
    </div>

    <!-- Slide 3: Financial KPI -->
    <div class="slide">
        <span class="badge">FINANCIAL PERFORMANCE</span>
        <h2><i data-lucide="bar-chart-2"></i> Monthly KPI Dashboard</h2>
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-title">Total Spending</div>
                <div class="kpi-value">₩{total_amount:,}</div>
                <div class="kpi-sub" style="color: {change_color}">
                    {arrow} {abs(change_rate)}% <span style="color: #64748b; font-weight: 400;">vs last month</span>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Transactions</div>
                <div class="kpi-value">{tx_count}</div>
                <div class="kpi-sub" style="color: var(--text-secondary)">Processed Count</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Avg Ticket</div>
                <div class="kpi-value">₩{avg_ticket:,}</div>
                <div class="kpi-sub" style="color: var(--text-secondary)">Per Transaction</div>
            </div>
             <div class="kpi-card" style="border-color: var(--danger);">
                <div class="kpi-title" style="color: var(--danger);">Max Value High</div>
                <div class="kpi-value" style="font-size: 1.8rem; line-height: 1.4; margin-top:5px;">{int(max_tx.get('amount',0)):,}</div>
                 <div class="kpi-sub" style="color: var(--text-secondary)">{max_tx.get('category','-')}</div>
            </div>
        </div>
        
        <div style="margin-top: 30px; padding: 25px; background: #fff5f5; border-radius: 12px; display: flex; align-items: center; gap: 20px; border: 1px solid #fed7d7;">
            <i data-lucide="alert-triangle" style="color: var(--danger); width: 32px; height: 32px;"></i>
            <div>
                <strong style="color: #c53030; font-size: 1.1rem; display: block; marginBottom: 5px;">Highest Spending Alert</strong> 
                <span style="color: #2d3748;">{max_tx.get('merchant_name','-')} 건이 단일 지출 최고액을 기록했습니다. 상세 검토가 필요합니다.</span>
            </div>
        </div>
        
        <div class="footer-page">03</div>
    </div>
    
    <!-- Slide 4: Market Share (Visual) -->
    <div class="slide">
        <span class="badge">MARKET SHARE</span>
        <h2><i data-lucide="pie-chart"></i> Category Analysis</h2>
        
        <div class="content-box" style="display: flex; align-items: center; justify-content: space-around; background: #fff; border: none; padding: 0;">
             <!-- Pie Chart -->
             <div style="width: 320px; height: 320px; border-radius: 50%; background: conic-gradient(
                #2563eb 0% 30%, 
                #3b82f6 30% 60%, 
                #60a5fa 60% 80%,
                #eff6ff 80% 100%
             ); position: relative; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">
                <div style="position: absolute; width: 180px; height: 180px; background: #fff; border-radius: 50%; top: 50%; left: 50%; transform: translate(-50%, -50%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
                    <div style="font-size: 0.9rem; color: #64748b; font-weight: 600;">TOP 1</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #1a202c;">{report_data.get('top_categories', [{}])[0].get('percent', 0):.1f}%</div>
                </div>
             </div>
             
             <!-- Legend Table -->
             <div style="width: 450px;">
                <table style="margin-top: 0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <tr>
                        <th style="background: #f7fafc;">Category</th>
                        <th style="background: #f7fafc;">Amount</th>
                        <th style="background: #f7fafc;">Share</th>
                    </tr>
                    {''.join([f"<tr><td>{cat['name']}</td><td>₩{int(cat['amount']):,}</td><td>{cat['percent']:.1f}%</td></tr>" for cat in report_data.get('top_categories', [])[:4]])}
                </table>
             </div>
        </div>
        <div class="footer-page">04</div>
    </div>

    <!-- Slide 5: B2C Insight (AI) -->
    <div class="slide">
        <span class="badge">USER BEHAVIOR</span>
        <h2><i data-lucide="users"></i> B2C Consumer Insight</h2>
        <div class="content-box">
             {parsed_content['b2c_insight']}
        </div>
        <div class="footer-page">05</div>
    </div>
    
    <!-- Slide 6: B2B Strategy (AI) -->
    <div class="slide">
        <span class="badge">BUSINESS OPPORTUNITY</span>
        <h2><i data-lucide="briefcase"></i> B2B Partnership Strategy</h2>
        <div class="content-box">
             {parsed_content['b2b_strategy']}
        </div>
        <div class="footer-page">06</div>
    </div>
    
    <!-- Slide 7: Partnership Metrics (AI Table) -->
    <div class="slide">
        <span class="badge">EXPECTED ROI</span>
        <h2><i data-lucide="table"></i> Partnership Metrics</h2>
        <div style="padding: 10px 0;">
             {parsed_content['metrics']}
        </div>
        <p style="margin-top: 20px; color: var(--text-secondary); font-size: 1rem;"><i data-lucide="info"></i> 위 지표는 유사 산업군의 평균 전환율을 기반으로 추산된 예상 수치입니다.</p>
        <div class="footer-page">07</div>
    </div>

    <script>
        lucide.createIcons();
    </script>
</body>
</html>"""

async def generate_weekly_report(db: AsyncSession) -> Dict[str, Any]:
    """
    주간 리포트 데이터를 생성합니다. (지난주 월~일)
    
    Args:
        db: 데이터베이스 세션
    
    Returns:
        dict: 리포트 데이터
    """
    # 실행 시점 (보통 월요일 오전)
    today = datetime.now()
    
    # 지난주 월요일 구하기
    # today.weekday(): 월(0) ~ 일(6)
    # 이번주 월요일: today - timedelta(days=today.weekday())
    # 지난주 월요일: 이번주 월요일 - 7일
    this_week_monday = today - timedelta(days=today.weekday())
    start_of_week = this_week_monday - timedelta(days=7)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 지난주 일요일 (이번주 월요일 00:00 직전)
    end_of_week = this_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 지지난 주 (증감율 비교용)
    last_week_start = start_of_week - timedelta(days=7)
    last_week_end = start_of_week
    
    # 이번 주(실제로는 지난 주) 거래 데이터 (이상 거래 제외)
    this_week_query = select(
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= start_of_week,
            Transaction.transaction_time < end_of_week,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    )
    this_week_result = await db.execute(this_week_query)
    this_week_data = this_week_result.first()
    
    # 최대 지출 거래 조회 (카테고리명 포함)
    max_tx_query = select(Transaction, Category.name).join(
        Category, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_week,
            Transaction.transaction_time < end_of_week,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    ).order_by(Transaction.amount.desc()).limit(1)
    max_tx_result = await db.execute(max_tx_query)
    max_tx_row = max_tx_result.first()
    
    max_transaction = max_tx_row[0] if max_tx_row else None
    max_cat_name = max_tx_row[1] if max_tx_row else None
    
    # 이상 거래 조회
    fraud_tx_query = select(Transaction).where(
        and_(
            Transaction.transaction_time >= start_of_week,
            Transaction.transaction_time < end_of_week,
            Transaction.is_fraudulent == True
        )
    ).order_by(Transaction.transaction_time.desc())
    fraud_tx_result = await db.execute(fraud_tx_query)
    fraud_transactions = fraud_tx_result.scalars().all()

    # 지난 주(실제로는 지지난 주) 거래 데이터 (이상 거래 제외)
    last_week_query = select(
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= last_week_start,
            Transaction.transaction_time < last_week_end,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    )
    last_week_result = await db.execute(last_week_query)
    last_week_data = last_week_result.first()
    
    # 카테고리별 집계 (이상 거래 제외)
    category_query = select(
        Category.name,
        func.sum(Transaction.amount).label("amount"),
        func.count(Transaction.id).label("count")
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_week,
            Transaction.transaction_time < end_of_week,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(5)
    
    category_result = await db.execute(category_query)
    categories = category_result.all()
    
    # 전주 대비 증감율 계산
    this_week_total = float(this_week_data.total_amount or 0)
    last_week_total = float(last_week_data.total_amount or 0)
    
    if last_week_total > 0:
        change_rate = ((this_week_total - last_week_total) / last_week_total) * 100
    else:
        change_rate = 0
    
    report_data = {
        "period_start": start_of_week.strftime("%Y-%m-%d"),
        "period_end": (end_of_week - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_amount": this_week_total,
        "transaction_count": this_week_data.count or 0,
        "change_rate": round(change_rate, 1),
        "top_categories": [],
        "max_transaction": None,
        "fraud_transactions": []
    }
    
    # 카테고리 데이터 처리 (비율 계산)
    if categories and this_week_total > 0:
        for cat in categories:
            cat_amount = float(cat.amount)
            # 전체 지출액 대비 비중으로 계산
            percentage = (cat_amount / this_week_total) * 100
            report_data["top_categories"].append({
                "name": cat.name, 
                "amount": cat_amount, 
                "count": int(cat.count),
                "percent": percentage
            })
            
    if max_transaction:
        report_data["max_transaction"] = {
            "merchant_name": max_transaction.merchant_name,
            "amount": float(max_transaction.amount),
            "date": max_transaction.transaction_time.strftime("%m/%d"),
            "category": max_cat_name
        }

    # 이상 거래 데이터 처리
    for tx in fraud_transactions:
        report_data["fraud_transactions"].append({
            "merchant_name": tx.merchant_name,
            "amount": float(tx.amount),
            "date": tx.transaction_time.strftime("%m/%d %H:%M"),
            "description": tx.description
        })

    # AI Insight 생성
    try:
        prompt = generate_report_prompt("주간 소비", report_data)
        ai_insight = await call_gemini_api(prompt)
        report_data["ai_insight"] = ai_insight
        logger.info(f"Generated AI Insight (Weekly): {ai_insight}")
    except Exception as e:
        logger.error(f"Failed to generate AI insight: {e}")
        report_data["ai_insight"] = "AI 분석을 불러올 수 없습니다."

    return report_data


async def generate_monthly_report(db: AsyncSession) -> Dict[str, Any]:
    """
    월간 리포트 데이터를 생성합니다. (지난달 1일 ~ 말일)
    
    Args:
        db: 데이터베이스 세션
    
    Returns:
        dict: 리포트 데이터
    """
    # 실행 시점 (보통 1일 오전)
    today = datetime.now()
    
    # 이번 달 1일
    this_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 지난 달 1일 (start_of_month)
    if this_month_start.month == 1:
        start_of_month = this_month_start.replace(year=this_month_start.year - 1, month=12)
    else:
        start_of_month = this_month_start.replace(month=this_month_start.month - 1)
        
    # 지난 달의 다음 달 1일 == 이번 달 1일 (end_of_month)
    # 쿼리에서 < end_of_month 로 사용하여 지난 달 말일까지 포함
    end_of_month = this_month_start
    
    # 지지난 달 (증감율 비교용)
    if start_of_month.month == 1:
        last_month_start = start_of_month.replace(year=start_of_month.year - 1, month=12)
    else:
        last_month_start = start_of_month.replace(month=start_of_month.month - 1)
    last_month_end = start_of_month
    
    # 이번 달 거래 데이터 (이상 거래 제외)
    this_month_query = select(
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= start_of_month,
            Transaction.transaction_time < end_of_month,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    )
    this_month_result = await db.execute(this_month_query)
    this_month_data = this_month_result.first()
    
    # 최대 지출 거래 조회 (이상 거래 제외)
    max_tx_query = select(Transaction, Category.name).join(
        Category, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_month,
            Transaction.transaction_time < end_of_month,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    ).order_by(Transaction.amount.desc()).limit(1)
    max_tx_result = await db.execute(max_tx_query)
    max_tx_row = max_tx_result.first()
    
    max_transaction = max_tx_row[0] if max_tx_row else None
    max_cat_name = max_tx_row[1] if max_tx_row else None

    # 이상 거래 조회
    fraud_tx_query = select(Transaction).where(
        and_(
            Transaction.transaction_time >= start_of_month,
            Transaction.transaction_time < end_of_month,
            Transaction.is_fraudulent == True
        )
    ).order_by(Transaction.transaction_time.desc())
    fraud_tx_result = await db.execute(fraud_tx_query)
    fraud_transactions = fraud_tx_result.scalars().all()
    
    # 지난 달 거래 데이터 (이상 거래 제외)
    last_month_query = select(
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= last_month_start,
            Transaction.transaction_time < last_month_end,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    )
    last_month_result = await db.execute(last_month_query)
    last_month_data = last_month_result.first()
    
    # 카테고리별 집계 (이상 거래 제외)
    category_query = select(
        Category.name,
        func.sum(Transaction.amount).label("amount"),
        func.count(Transaction.id).label("count")
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_month,
            Transaction.transaction_time < end_of_month,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(5)
    
    category_result = await db.execute(category_query)
    categories = category_result.all()
    
    # 전월 대비 증감율 계산
    this_month_total = float(this_month_data.total_amount or 0)
    last_month_total = float(last_month_data.total_amount or 0)
    
    if last_month_total > 0:
        change_rate = ((this_month_total - last_month_total) / last_month_total) * 100
    else:
        change_rate = 0
    
    report_data = {
        "period_start": start_of_month.strftime("%Y-%m-%d"),
        "period_end": (end_of_month - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_amount": this_month_total,
        "transaction_count": this_month_data.count or 0,
        "change_rate": round(change_rate, 1),
        "top_categories": [],
        "max_transaction": None,
        "fraud_transactions": []
    }
    
    # 카테고리 데이터 처리 (비율 계산)
    if categories and this_month_total > 0:
        for cat in categories:
            cat_amount = float(cat.amount)
            # 전체 지출액 대비 비중으로 계산
            percentage = (cat_amount / this_month_total) * 100
            report_data["top_categories"].append({
                "name": cat.name, 
                "amount": cat_amount, 
                "count": int(cat.count),
                "percent": percentage
            })
            
    if max_transaction:
        report_data["max_transaction"] = {
            "merchant_name": max_transaction.merchant_name,
            "amount": float(max_transaction.amount),
            "date": max_transaction.transaction_time.strftime("%m/%d"),
            "category": max_cat_name
        }

    # 이상 거래 데이터 처리
    for tx in fraud_transactions:
        report_data["fraud_transactions"].append({
            "merchant_name": tx.merchant_name,
            "amount": float(tx.amount),
            "date": tx.transaction_time.strftime("%m/%d %H:%M"),
            "description": tx.description
        })

    # AI Insight 생성
    try:
        prompt = generate_report_prompt("월간 소비", report_data)
        ai_insight = await call_gemini_api(prompt)
        report_data["ai_insight"] = ai_insight
        logger.info(f"Generated AI Insight (Monthly): {ai_insight}")
    except Exception as e:
        logger.error(f"Failed to generate AI insight: {e}")
        report_data["ai_insight"] = "AI 분석을 불러올 수 없습니다."

    return report_data


async def generate_daily_report(db: AsyncSession) -> Dict[str, Any]:
    """
    일간 리포트 데이터를 생성합니다. (전날 데이터)
    
    Args:
        db: 데이터베이스 세션
    
    Returns:
        dict: 리포트 데이터
    """
    # 어제 (00:00:00 ~ 23:59:59)
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 그저께 (증감율 비교용)
    day_before_yesterday_start = start_of_day - timedelta(days=1)
    day_before_yesterday_end = start_of_day

    # 어제 거래 데이터 (이상 거래 제외)
    yesterday_query = select(
        func.count(Transaction.id).label("count"),
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= start_of_day,
            Transaction.transaction_time < end_of_day,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    )
    yesterday_result = await db.execute(yesterday_query)
    yesterday_data = yesterday_result.first()

    # 최대 지출 거래 조회 (카테고리명 포함)
    max_tx_query = select(Transaction, Category.name).join(
        Category, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_day,
            Transaction.transaction_time < end_of_day,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    ).order_by(Transaction.amount.desc()).limit(1)
    max_tx_result = await db.execute(max_tx_query)
    max_tx_row = max_tx_result.first()
    
    max_transaction = max_tx_row[0] if max_tx_row else None
    max_cat_name = max_tx_row[1] if max_tx_row else None

    # 이상 거래 조회
    fraud_tx_query = select(Transaction).where(
        and_(
            Transaction.transaction_time >= start_of_day,
            Transaction.transaction_time < end_of_day,
            Transaction.is_fraudulent == True
        )
    ).order_by(Transaction.transaction_time.desc())
    fraud_tx_result = await db.execute(fraud_tx_query)
    fraud_transactions = fraud_tx_result.scalars().all()

    # 그저께 거래 데이터 (이상 거래 제외)
    day_before_query = select(
        func.sum(Transaction.amount).label("total_amount")
    ).where(
        and_(
            Transaction.transaction_time >= day_before_yesterday_start,
            Transaction.transaction_time < day_before_yesterday_end,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    )
    day_before_result = await db.execute(day_before_query)
    day_before_data = day_before_result.first()

    # 카테고리별 집계 (이상 거래 제외)
    category_query = select(
        Category.name,
        func.sum(Transaction.amount).label("amount"),
        func.count(Transaction.id).label("count")
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).where(
        and_(
            Transaction.transaction_time >= start_of_day,
            Transaction.transaction_time < end_of_day,
            Transaction.status == "completed",
            Transaction.is_fraudulent == False
        )
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(5)
    
    category_result = await db.execute(category_query)
    categories = category_result.all()

    # 전일 대비 증감율 계산
    yesterday_total = float(yesterday_data.total_amount or 0)
    day_before_total = float(day_before_data.total_amount or 0)
    
    if day_before_total > 0:
        change_rate = ((yesterday_total - day_before_total) / day_before_total) * 100
    else:
        change_rate = 0
    
    report_data = {
        "period_start": start_of_day.strftime("%Y-%m-%d"),
        "period_end": start_of_day.strftime("%Y-%m-%d"),
        "total_amount": yesterday_total,
        "transaction_count": yesterday_data.count or 0,
        "change_rate": round(change_rate, 1),
        "top_categories": [],
        "max_transaction": None,
        "fraud_transactions": []
    }

    # 카테고리 데이터 처리
    if categories and yesterday_total > 0:
        for cat in categories:
            cat_amount = float(cat.amount)
            # 전체 지출액 대비 비중으로 계산
            percentage = (cat_amount / yesterday_total) * 100
            report_data["top_categories"].append({
                "name": cat.name, 
                "amount": cat_amount, 
                "count": int(cat.count),
                "percent": percentage
            })
            
    if max_transaction:
        report_data["max_transaction"] = {
            "merchant_name": max_transaction.merchant_name,
            "amount": float(max_transaction.amount),
            "date": max_transaction.transaction_time.strftime("%H:%M"),
            "category": max_cat_name
        }

    # 이상 거래 데이터 처리
    for tx in fraud_transactions:
        report_data["fraud_transactions"].append({
            "merchant_name": tx.merchant_name,
            "amount": float(tx.amount),
            "date": tx.transaction_time.strftime("%H:%M"),
            "description": tx.description
        })

    # AI Insight 생성
    try:
        # 일간 리포트는 데이터 양이 적으므로 간략한 프롬프트 사용
        prompt = generate_report_prompt("일간 소비", report_data)
        ai_insight = await call_gemini_api(prompt)
        report_data["ai_insight"] = ai_insight
        logger.info(f"Generated AI Insight (Daily): {ai_insight}")
    except Exception as e:
        logger.error(f"Failed to generate AI insight: {e}")
        report_data["ai_insight"] = "AI 분석을 불러올 수 없습니다."

    return report_data


def format_report_html(report_data: Dict[str, Any]) -> str:
    """
    리포트 데이터를 HTML 형식으로 변환합니다.
    """
    # 증감율에 따른 색상 및 아이콘
    change_rate = report_data["change_rate"]
    if change_rate > 0:
        change_color = "#e53e3e"  # Red-600
        change_icon = "↑"
    elif change_rate < 0:
        change_color = "#38a169"  # Green-600
        change_icon = "↓"
    else:
        change_color = "#718096"  # Gray-600
        change_icon = "="
    
    # 지표 데이터 구성
    stats = [
        ("총 소비 (정상 거래)", f"₩{report_data['total_amount']:,.0f}", ""),
        ("거래 건수", f"{report_data['transaction_count']}건", ""),
        ("전기 대비", f"{change_icon} {abs(change_rate):.1f}%", change_color)
    ]
    
    stats_html = ""
    for label, value, color in stats:
        color_style = f"color: {color};" if color else ""
        stats_html += f"""
        <div class="stat">
            <span class="stat-label">{label}</span>
            <span class="stat-value" style="{color_style}">{value}</span>
        </div>
        """
        
    # 상위 카테고리 HTML 생성
    categories_html = ""
    for cat in report_data["top_categories"][:3]:
        # 바 색상
        bar_color = "#667eea" if cat['percent'] > 90 else "#a3bffa"
        
        categories_html += f"""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; align-items: flex-end;">
                <div>
                    <span style="font-size: 15px; font-weight: 700; color: #1a202c;">{cat['name']}</span>
                    <span style="font-size: 12px; color: #718096; margin-left: 6px;">({cat['count']}건)</span>
                </div>
                <span style="font-size: 15px; font-weight: 700; color: #2d3748;">₩{cat['amount']:,.0f}</span>
            </div>
            <div style="background-color: #edf2f7; height: 8px; border-radius: 4px; width: 100%; overflow: hidden;">
                <div style="background: {bar_color}; height: 8px; border-radius: 4px; width: {cat['percent']}%;"></div>
            </div>
        </div>
        """
        
    # 최대 지출 하이라이트
    max_spend_html = ""
    if report_data.get("max_transaction"):
        tx = report_data["max_transaction"]
        max_spend_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 800; color: #667eea; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">🏆 Highest Spending</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 800; color: #1a202c; font-size: 17px;">{tx['merchant_name']}</div>
                    <div style="font-size: 13px; color: #718096;">{tx['date']} 결제</div>
                </div>
                <div style="font-weight: 800; color: #e53e3e; font-size: 20px;">
                    ₩{tx['amount']:,.0f}
                </div>
            </div>
        </div>
        """
    
    # 이상 거래 섹션
    fraud_html = ""
    if report_data.get("fraud_transactions"):
        fraud_items = report_data["fraud_transactions"]
        fraud_count = len(fraud_items)
        fraud_total = sum(item["amount"] for item in fraud_items)
        
        fraud_list_html = ""
        for tx in fraud_items:
            fraud_list_html += f"""
            <div style="padding: 12px 0; border-bottom: 1px solid #fed7d7; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 700; color: #c53030; font-size: 14px;">{tx.get('merchant_name')}</div>
                    <div style="font-size: 12px; color: #e53e3e;">{tx.get('date')}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700; color: #c53030; font-size: 15px;">₩{tx.get('amount'):,.0f}</div>
                </div>
            </div>
            """
            
        fraud_html = f"""
        <div style="background-color: #fff5f5; border: 1px solid #feb7b7; border-radius: 12px; margin-bottom: 24px; overflow: hidden; padding: 16px;">
            <div style="font-weight: 800; color: #c53030; font-size: 15px; display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span>🚨 이상 거래 탐지 ({fraud_count}건)</span>
                <span>총 ₩{fraud_total:,.0f}</span>
            </div>
            {fraud_list_html}
        </div>
        """

    # AI Insight Section
    ai_insight_html = ""
    if "ai_insight" in report_data and report_data["ai_insight"]:
        raw_insight = report_data['ai_insight']
        # Markdown 굵게 표시를 HTML로 변환
        formatted_insight = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', raw_insight)
        
        ai_insight_html = f"""
        <div class="ai-insight-box">
            <div class="ai-insight-title">
                <span style="margin-right: 10px;">💡</span> AI 수석 분석가 비즈니스 인사이트
            </div>
            <div class="ai-content">{formatted_insight}</div>
        </div>
        """

    # HTML 구조 조립
    html = f"""
    {max_spend_html}
    {fraud_html}
    
    {stats_html}

    <div style="margin-top: 40px; margin-bottom: 15px;">
        <h3 style="font-size: 18px; color: #1a202c; font-weight: 800; margin-bottom: 20px; border-left: 4px solid #667eea; padding-left: 12px;">📊 상위 지출 카테고리</h3>
        {categories_html}
    </div>

    {ai_insight_html}
    """
    
    return html
