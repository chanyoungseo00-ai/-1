import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="그라운드골프 통합 채점 시스템", layout="wide")

st.title("🏆 개인전 및 단체전 통합 자동 채점 시스템")
st.markdown("엑셀 파일을 업로드하면 **1~3일차 점수를 자동으로 인식하고 합산**하여 순위표 및 시상 명단을 생성합니다.")

st.info("""
**💡 순위 결정 규정 (공통)**
1. **총타수**가 가장 적은 선수(또는 팀)
2. 동타일 경우, **2타수**가 많은 선수(또는 팀)
3. 2타수도 같을 경우, **홀인원** 개수가 많은 선수(또는 팀)
""")

def load_and_standardize_data(file, sheet_name):
    # 1. 엑셀 데이터를 헤더 없이 불러옵니다.
    df = pd.read_excel(file, sheet_name=sheet_name, skiprows=2, header=None)
    
    # 2. 열(칸) 개수를 세어 2일차인지 3일차인지 자동 판단
    if df.shape[1] >= 17:
        # [3일차 엑셀인 경우]
        df = df.iloc[:, :17].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
            '3일차_총타수', '3일차_2타수', '3일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
    elif df.shape[1] >= 14:
        # [2일차 엑셀인 경우]
        df = df.iloc[:, :14].copy()
        df.columns = [
            '일시', '조', '타순', '소속', '이름', 
            '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
            '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
            '최종_총타수', '최종_2타수', '최종_홀인원'
        ]
        # 계산 오류를 막기 위해 3일차 칸을 0으로 투명하게 만들어줍니다.
        df['3일차_총타수'] = 0
        df['3일차_2타수'] = 0
        df['3일차_홀인원'] = 0
    else:
        raise ValueError(f"'{sheet_name}' 시트의 형식이 맞지 않습니다. 표준 엑셀 서식을 사용해 주세요.")
        
    df = df.dropna(subset=['이름', '소속'])
    
    # 3. 숫자형 데이터로 완벽하게 변환 (빈칸은 0 처리)
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
                df_ind = load_and_standardize_data(uploaded_file, '개인전 채점표')

                # 데이터 자동 보정 (빈칸이 있더라도 1+2+3일차를 알아서 합산)
                df_ind['최종_총타수'] = np.where(
                    df_ind['최종_총타수'] == 0, 
                    df_ind['1일차_총타수'] + df_ind['2일차_총타수'] + df_ind['3일차_총타수'], 
                    df_ind['최종_총타수']
                )
                df_ind['최종_2타수'] = np.where(
                    df_ind['최종_총타수'] > 0, 
                    df_ind['1일차_2타수'] + df_ind['2일차_2타수'] + df_ind['3일차_2타수'], 
                    df_ind['최종_2타수']
                )
                df_ind['최종_홀인원'] = np.where(
                    df_ind['최종_총타수'] > 0, 
                    df_ind['1일차_홀인원'] + df_ind['2일차_홀인원'] + df_ind['3일차_홀인원'], 
                    df_ind['최종_홀인원']
                )

                df_ind = df_ind[df_ind['최종_총타수'] > 0].copy()
                
                # 순위 계산
                df_ind = df_ind.sort_values(by=['최종_총타수', '최종_2타수', '최종_홀인원'], ascending=[True, False, False]).reset_index(drop=True)
                df_ind['순위'] = df_ind[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1).rank(method='min', ascending=False).astype(int)

                st.subheader("🥇 개인전 결과")
                st.success("✅ 개인전 순위 집계가 완료되었습니다.")
                
                c1, c2 = st.columns(2)
                c1.write("**시상 명단 (상위 10명)**")
                c1.dataframe(df_ind[['순위', '소속', '이름', '최종_총타수']].head(10), hide_index=True)
                
                c2.write("**전체 순위표**")
                c2.dataframe(df_ind[['순위', '소속', '이름', '최종_총타수', '최종_2타수', '최종_홀인원']], hide_index=True)

            # ==========================================
            # 2. 단체전 처리 영역
            # ==========================================
            with tab2:
                df_team_raw = load_and_standardize_data(uploaded_file, '단체전 채점표')

                # 단체전 개인별 데이터 자동 보정
                df_team_raw['최종_총타수'] = np.where(
                    df_team_raw['최종_총타수'] == 0, 
                    df_team_raw['1일차_총타수'] + df_team_raw['2일차_총타수'] + df_team_raw['3일차_총타수'], 
                    df_team_raw['최종_총타수']
                )
                df_team_raw['최종_2타수'] = np.where(
                    df_team_raw['최종_총타수'] > 0, 
                    df_team_raw['1일차_2타수'] + df_team_raw['2일차_2타수'] + df_team_raw['3일차_2타수'], 
                    df_team_raw['최종_2타수']
                )
                df_team_raw['최종_홀인원'] = np.where(
                    df_team_raw['최종_총타수'] > 0, 
                    df_team_raw['1일차_홀인원'] + df_team_raw['2일차_홀인원'] + df_team_raw['3일차_홀인원'], 
                    df_team_raw['최종_홀인원']
                )
                
                df_team_raw = df_team_raw[df_team_raw['최종_총타수'] > 0].copy()

                # 단체전 팀별 점수 합산 및 순위 계산
                df_team = df_team_raw.groupby('소속', as_index=False)[['최종_총타수', '최종_2타수', '최종_홀인원']].sum()
                df_team = df_team.sort_values(by=['최종_총타수', '최종_2타수', '최종_홀인원'], ascending=[True, False, False]).reset_index(drop=True)
                df_team['순위'] = df_team[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1).rank(method='min', ascending=False).astype(int)

                st.subheader("🤝 단체전 결과")
                st.success("✅ 단체전 팀별 점수 합산이 완료되었습니다.")
                
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
        st.error(f"오류가 발생했습니다. 시트 이름('개인전 채점표', '단체전 채점표')과 열