import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="그라운드골프 통합 채점 시스템", layout="wide")

st.title("🏆 개인전 및 단체전 통합 자동 채점 시스템")
st.markdown("엑셀 파일을 업로드하면 **설정된 대회 일정(1~3일차)**에 따라 점수를 정확히 합산하여 순위표를 생성합니다.")

with st.sidebar:
    st.header("⚙️ 채점 설정")
    # [위원장님 요청] 1일차 대회 버튼을 추가하여 선택의 폭을 넓혔습니다.
    tournament_days = st.radio(
        "🗓️ 대회 일정 선택", 
        ("1일차 대회", "2일차 대회", "3일차 대회"), 
        index=0
    )
    st.info("💡 현재 업로드하려는 엑셀 파일의 실제 경기 일수를 선택해 주세요.")

st.info("""
**💡 순위 결정 규정 (공통)**
1. **총타수**가 가장 적은 선수(또는 팀)
2. 동타일 경우, **2타수**가 많은 선수(또는 팀)
3. 2타수도 같을 경우, **홀인원** 개수가 많은 선수(또는 팀)
""")

def load_and_standardize_data(file, sheet_name, days_setting):
    # 엑셀 데이터를 헤더 없이 불러옵니다.
    df = pd.read_excel(file, sheet_name=sheet_name, skiprows=2, header=None)
    
    # 선택된 일정에 따라 필요한 열(Column) 개수만 정확히 추출 (쓰레기값 혼입 방지)
    if days_setting == "3일차 대회":
        df = df.iloc[:, :17].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
            '3일차_총타수', '3일차_2타수', '3일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
    elif days_setting == "2일차 대회":
        df = df.iloc[:, :14].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
        # 3일차 데이터는 존재하지 않으므로 0으로 투명 처리
        df['3일차_총타수'], df['3일차_2타수'], df['3일차_홀인원'] = 0, 0, 0
    else: # 1일차 대회
        df = df.iloc[:, :11].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
        # 2~3일차 데이터는 존재하지 않으므로 0으로 투명 처리
        df['2일차_총타수'], df['2일차_2타수'], df['2일차_홀인원'] = 0, 0, 0
        df['3일차_총타수'], df['3일차_2타수'], df['3일차_홀인원'] = 0, 0, 0
        
    df = df.dropna(subset=['이름', '소속'])
    
    # 숫자형 데이터 변환 및 결측치 0 처리
    num_cols = [
        '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
        '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
        '3일차_총타수', '3일차_2타수', '3일차_홀인원', 
        '최종_총타수', '최종_2타수', '최종_홀인원'
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
    return df

uploaded_file = st.file_uploader("채점표 엑셀 파일을 업로드해주세요 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    tab1, tab2 = st.tabs(["🥇 개인전 결과", "🤝 단체전 결과"])

    try:
        with st.spinner("설정된 일정에 따라 순위를 정밀하게 계산 중입니다..."):
            
            # ==========================================
            # 1. 개인전 처리 영역
            # ==========================================
            with tab1:
                df_ind = load_and_standardize_data(uploaded_file, '개인전 채점표', tournament_days)

                # [강력 보정] 선택된 일차수의 점수만 합산하여 최종 필드 덮어쓰기
                df_ind['최종_총타수'] = df_ind['1일차_총타수'] + df_ind['2일차_총타수'] + df_ind['3일차_총타수']
                df_ind['최종_2타수'] = df_ind['1일차_2타수'] + df_ind['2일차_2타수'] + df_ind['3일차_2타수']
                df_ind['최종_홀인원'] = df_ind['1일차_홀인원'] + df_ind['2일차_홀인원'] + df_ind['3일차_홀인원']

                df_ind = df_ind[df_ind['최종_총타수'] > 0].copy()
                
                # 순위 정렬
                df_ind = df_ind.sort_values(
                    by=['최종_총타수', '최종_2타수', '최종_홀인원'], 
                    ascending=[True, False, False]
                ).reset_index(drop=True)
                
                df_ind['순위'] = df_ind[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(
                    lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1
                ).rank(method='min', ascending=False).astype(int)

                st.subheader(f"🥇 개인전 결과 ({tournament_days})")
                st.success(f"✅ {tournament_days} 기준 순위 집계가 완료되었습니다.")
                
                c1, c2 = st.columns(2)
                c1.write("**시상 명단 (상위 10명)**")
                c1.dataframe(df_ind[['순위', '소속', '이름', '최종_총타수']].head(10), hide_index=True)
                
                c2.write("**전체 순위표**")
                c2.dataframe(df_ind[['순위', '소속', '이름', '최종_총타수', '최종_2타수', '최종_홀인원']], hide_index=True)

            # ==========================================
            # 2. 단체전 처리 영역
            # ==========================================
            with tab2:
                df_team_raw = load_and_standardize_data(uploaded_file, '단체전 채점표', tournament_days)

                df_team_raw['최종_총타수'] = df_team_raw['1일차_총타수'] + df_team_raw['2일차_총타수'] + df_team_raw['3일차_총타수']
                df_team_raw['최종_2타수'] = df_team_raw['1일차_2타수'] + df_team_raw['2일차_2타수'] + df_team_raw['3일차_2타수']
                df_team_raw['최종_홀인원'] = df_team_raw['1일차_홀인원'] + df_team_raw['2일차_홀인원'] + df_team_raw['3일차_홀인원']
                
                df_team_raw = df_team_raw[df_team_raw['최종_총타수'] > 0].copy()

                # 팀별 합산
                df_team = df_team_raw.groupby('소속', as_index=False)[['최종_총타수', '최종_2타수', '최종_홀인원']].sum()
                
                # 순위 정렬
                df_team = df_team.sort_values(
                    by=['최종_총타수', '최종_2타수', '최종_홀인원'], 
                    ascending=[True, False, False]
                ).reset_index(drop=True)
                
                df_team['순위'] = df_team[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(
                    lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1
                ).rank(method='min', ascending=False).astype(int)

                st.subheader(f"🤝 단체전 결과 ({tournament_days})")
                st.success(f"✅ {tournament_days} 기준 팀별 합산이 완료되었습니다.")
                
                c3, c4 = st.columns(2)
                c3.write("**단체전 시상팀 (상위 5팀)**")
                c3.dataframe(df_team[['순위', '소속', '최종_총타수']].head(5), hide_index=True)
                
                c4.write("**단체전 전체 순위표**")
                c4.dataframe(df_team[['순위', '소속', '최종_총타수', '최종_2타수', '최종_홀인원']], hide_index=True)

            # ==========================================
            # 3. 엑셀 다운로드
            # ==========================================
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_ind.to_excel(writer, index=False, sheet_name='개인전_결과')
                df_team.to_excel(writer, index=False, sheet_name='단체전_결과')
            
            st.markdown("---")
            st.download_button(
                label="📥 최종 통합 결과 엑셀 다운로드", 
                data=output.getvalue(), 
                file_name="최종_채점결과_통합본.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(
            f"오류가 발생했습니다. "
            f"시트 이름('개인전 채점표', '단체전 채점표')과 파일 형식을 확인해주세요: {e}"
        )