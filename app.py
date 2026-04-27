import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="그라운드골프 개인전 채점 시스템", layout="wide")

st.title("🏆 개인전 전용 자동 채점 시스템")
st.markdown("채점이 완료된 **[개인전 채점표]** 시트가 포함된 엑셀 파일을 업로드하면, 공식 규정에 따라 순위표와 시상자 명단을 자동 생성합니다.")

st.info("""
**💡 개인전 순위 결정 규정 (우선순위 반영됨)**
1. **총타수**가 가장 적은 선수
2. 동타일 경우, **2타수**가 많은 선수
3. 2타수도 같을 경우, **홀인원** 개수가 많은 선수
""")

uploaded_file = st.file_uploader("개인전 채점표가 포함된 엑셀 파일을 업로드해주세요 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        with st.spinner("개인전 순위를 계산 중입니다..."):
            # 1. 엑셀 파일에서 데이터 읽기 (성명 대신 이름 사용)
            col_names = [
                '일시', '조', '타순', '소속', '이름', 
                '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
                '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
                '최종_총타수', '최종_2타수', '최종_홀인원'
            ]
            
            # 실제 '개인전 채점표' 시트 읽기
            df = pd.read_excel(uploaded_file, sheet_name='개인전 채점표', skiprows=2, names=col_names)
            
            # 2. 데이터 정제 (이름과 소속이 있는 데이터만 사용)
            df = df.dropna(subset=['이름', '소속'])
            
            score_cols = ['최종_총타수', '최종_2타수', '최종_홀인원']
            for col in score_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                
            # 합계 데이터 보정 로직
            df['최종_총타수'] = np.where(df['최종_총타수'] == 0, 
                                        pd.to_numeric(df['1일차_총타수'], errors='coerce').fillna(0) + 
                                        pd.to_numeric(df['2일차_총타수'], errors='coerce').fillna(0), 
                                        df['최종_총타수'])
            df['최종_2타수'] = np.where(df['최종_총타수'] > 0, 
                                        pd.to_numeric(df['1일차_2타수'], errors='coerce').fillna(0) + 
                                        pd.to_numeric(df['2일차_2타수'], errors='coerce').fillna(0), 
                                        df['최종_2타수'])
            df['최종_홀인원'] = np.where(df['최종_총타수'] > 0, 
                                        pd.to_numeric(df['1일차_홀인원'], errors='coerce').fillna(0) + 
                                        pd.to_numeric(df['2일차_홀인원'], errors='coerce').fillna(0), 
                                        df['최종_홀인원'])

            df = df[df['최종_총타수'] > 0].copy()

            # 3. 순위 산정 로직 (총타수 ➔ 2타수 ➔ 홀인원)
            df = df.sort_values(by=['최종_총타수', '최종_2타수', '최종_홀인원'], ascending=[True, False, False]).reset_index(drop=True)
            
            df['순위'] = df[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(
                lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1
            ).rank(method='min', ascending=False).astype(int)

            ranking_df = df[['순위', '소속', '이름', '최종_총타수', '최종_2타수', '최종_홀인원']].copy()
            ranking_df.columns = ['순위', '소속', '이름', '총타수', '2타수', '홀인원']

            # 4. 개인전 시상자 명단 (1~5위 및 장려상 5명)
            award_titles = ['1위', '2위', '3위', '4위', '5위'] + ['장려상'] * 5
            awards_data = []
            
            for i, title in enumerate(award_titles):
                if i < len(ranking_df):
                    player = ranking_df.iloc[i]
                    awards_data.append([title, player['소속'], player['이름'], player['총타수'], player['2타수'], player['홀인원']])
                else:
                    awards_data.append([title, '', '', '', '', ''])
                    
            awards_df = pd.DataFrame(awards_data, columns=['구분', '소속', '이름', '총타수', '2타수', '홀인원'])

            # 결과 화면 표시
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("🥇 개인전 시상자 명단")
                st.dataframe(awards_df, use_container_width=True, hide_index=True)
            with col2:
                st.subheader("📊 개인전 전체 순위표")
                st.dataframe(ranking_df, use_container_width=True, hide_index=True)

            # 5. 엑셀 파일 생성 및 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                ranking_df.to_excel(writer, index=False, sheet_name='개인전 순위표')
                awards_df.to_excel(writer, index=False, sheet_name='개인전 시상(출력물)')
                
            processed_data = output.getvalue()
            
            st.success("✅ 개인전 채점이 완료되었습니다!")
            st.download_button(
                label="📥 개인전 결과 엑셀 다운로드",
                data=processed_data,
                file_name="제18회_대한체육회장배_개인전_결과.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"오류가 발생했습니다. 엑셀의 열 제목이 '이름'인지, 시트 이름이 '개인전 채점표'인지 확인해주세요: {e}")