import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="그라운드골프 3일차 통합 채점 시스템", layout="wide")

st.title("🏆 개인전 및 단체전 통합 자동 채점 시스템 (3일차용)")
st.markdown("엑셀 파일을 업로드하면 **1~3일차 점수를 합산**하여 순위표 및 시상 명단을 한 번에 자동 생성합니다.")

st.info("""
**💡 순위 결정 규정 (공통)**
1. **총타수**가 가장 적은 선수(또는 팀)
2. 동타일 경우, **2타수**가 많은 선수(또는 팀)
3. 2타수도 같을 경우, **홀인원** 개수가 많은 선수(또는 팀)
""")

uploaded_file = st.file_uploader("채점표 엑셀 파일을 업로드해주세요 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    tab1, tab2 = st.tabs(["🥇 개인전 결과", "🤝 단체전 결과"])
    
    # ★ 3일차 컬럼 추가 (총 17개 열)
    col_names = [
        '일시', '조', '타순', '소속', '이름', 
        '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
        '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
        '3일차_총타수', '3일차_2타수', '3일차_홀인원', 
        '최종_총타수', '최종_2타수', '최종_홀인원'
    ]

    try:
        with st.spinner("1~3일차 순위를 계산하고 시상표를 작성 중입니다..."):
            
            # ==========================================
            # 1. 개인전 처리 영역
            # ==========================================
            with tab1:
                df_ind_raw = pd.read_excel(uploaded_file, sheet_name='개인전 채점표', skiprows=2, usecols=range(17), names=col_names)
                df_ind_raw = df_ind_raw.dropna(subset=['이름', '소속'])
                
                # 숫자 변환 (3일차 포함)
                num_cols = [
                    '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
                    '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
                    '3일차_총타수', '3일차_2타수', '3일차_홀인원', 
                    '최종_총타수', '최종_2타수', '최종_홀인원'
                ]
                for col in num_cols:
                    df_ind_raw[col] = pd.to_numeric(df_ind_raw[col], errors='coerce').fillna(0).astype(int)

                # 데이터 자동 보정 (1, 2, 3일차 자동 합산)
                df_ind = df_ind_raw.copy()
                df_ind['최종_총타수'] = np.where(df_ind['최종_총타수'] == 0, df_ind['1일차_총타수'] + df_ind['2일차_총타수'] + df_ind['3일차_총타수'], df_ind['최종_총타수'])
                df_ind['최종_2타수'] = np.where(df_ind