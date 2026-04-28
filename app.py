import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="그라운드골프 통합 채점 시스템", layout="wide")

st.title("🏆 개인전 및 단체전 통합 자동 채점 시스템")
st.markdown("엑셀 파일을 업로드하면 설정된 대회 일정에 맞춰 순위표 및 시상 명단을 정확하게 생성합니다.")

with st.sidebar:
    st.header("⚙️ 채점 설정")
    # [핵심] 컴퓨터가 헷갈리지 않도록 2일차/3일차를 직접 선택하는 스위치 추가
    tournament_days = st.radio("🗓️ 대회 일정 선택", ("2일차 대회", "3일차 대회"), index=0)
    st.info("💡 현재 업로드하려는 엑셀 파일의 형식에 맞게 일정을 선택해 주세요.")

st.info("""
**💡 순위 결정 규정 (공통)**
1. **총타수**가 가장 적은 선수(또는 팀)
2. 동타일 경우, **2타수**가 많은 선수(또는 팀)
3. 2타수도 같을 경우, **홀인원** 개수가 많은 선수(또는 팀)
""")

def load_and_standardize_data(file, sheet_name, days_setting):
    # 엑셀 데이터를 헤더 없이 불러옵니다.
    df = pd.read_excel(file, sheet_name=sheet_name, skiprows=2, header=None)
    
    # 사용자가 선택한 스위치에 따라 칸 수를 강제로 제한하여 쓰레기값(우측 표) 혼입 방지
    if days_setting == "3일차 대회":
        df = df.iloc[:, :17].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
            '3일차_총타수', '3일차_2타수', '3일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
    else: # 2일차 대회
        df = df.iloc[:, :14].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
        # 2일차일 경우 계산 오류를 막기 위해 3일차 데이터를 전부 0으로 투명 처리
        df['3일차_총타수'] = 0
        df['3일차_2타수'] = 0
        df['3일차_홀인원'] = 0
        
    df = df.dropna(subset=['이름', '소속'])
    
    # 빈칸이나 잘못된 글자는 모두 0으로 변환하여 계산 에러 방지
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
        with st.spinner("순위를 계산하고 시상표를 작성 중입니다..."):
            
            # ==========================================
            # 1. 개인전 처리 영역
            # ==========================================
            with tab1:
                df_ind = load_and_standardize_data(uploaded_file, '개인전 채점표', tournament_days)

                # [완벽 보정] 진행 요원의 합산 실수를 100% 무시하고 컴퓨터가 일차별 점수를 직접 합산함
                df_ind['최종_총타수'] = df_ind['1일차_총타수'] + df_ind['2일차_총타수'] + df_ind['3일차_총타수']
                df_ind['최종_2타수'] = df_ind['1일차_2타수'] + df_ind['2일차_2타수'] + df_ind['3일차_2타수']
                df_ind['최종_홀인원'] = df_ind['1일차_홀인원'] + df_ind['2일차_홀인원'] + df_ind['3일차_홀인원']

                df_ind = df_ind[df_ind['최종_총타수'] > 0].copy()
                
                # 순위 정렬 및 부여
                df_ind = df_ind.sort_values(
                    by=['최종_총타수', '최종_2타수', '최종_홀인원'], 
                    ascending=[True, False, False]
                ).reset_index(drop=True)
                
                df_ind['순위'] = df_ind[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(
                    lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1
                ).rank(method='min', ascending=False).astype(int)

                st.subheader("🥇 개인전 결과")
                st.success("✅ 개인전 점수 보정 및 순위 집계가 완료되었습니다.")
                
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

                # 단체전 역시 엑셀의 합계표를 무시하고 1,2,3일차 원본 데이터를 바탕으로 100% 강제 합산
                df_team_raw['최종_총타수'] = df_team_raw['1일차_총타수'] + df_team_raw['2일차_총타수'] + df_team_raw['3일차_총타수']
                df_team_raw['최종_2타수'] = df_team_raw['1일차_2타수'] + df_team_raw['2일차_2타수'] + df_team_raw['3일차_2타수']
                df_team_raw['최종_홀인원'] = df_team_raw['1일차_홀인원'] + df_team_raw['2일차_홀인원'] + df_team_raw['3일차_홀인원']
                
                df_team_raw = df_team_raw[df_team_raw['최종_총타수'] > 0].copy()

                # 단체전 팀별 그룹화 및 합산
                df_team = df_team_raw.groupby('소속', as_index=False)[['최종_총타수', '최종_2타수', '최종_홀인원']].sum()
                
                # 팀 순위 정렬 및 부여
                df_team = df_team.sort_values(
                    by=['최종_총타수', '최종_2타수', '최종_홀인원'], 
                    ascending=[True, False, False]
                ).reset_index(drop=True)
                
                df_team['순위'] = df_team[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(
                    lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1
                ).rank(method='min', ascending=False).astype(int)

                st.subheader("🤝 단체전 결과")
                st.success("✅ 단체전 팀별 점수 보정 및 합산이 완료되었습니다.")
                
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
            f"시트 이름('개인전 채점표', '단체전 채점표')과 열 구조를 확인해주세요: {e}"
        )