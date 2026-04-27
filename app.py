import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="그라운드골프 대회 자동 채점 시스템", layout="wide")

st.title("🏆 개인전 자동 채점 및 시상표 생성 시스템")
st.markdown("채점이 완료된 **[개인전 채점표]** 시트가 포함된 엑셀 파일을 업로드하면, 공식 규정에 따라 순위표와 시상자 명단을 자동 생성합니다.")

st.info("""
**💡 순위 결정 규정 (우선순위 반영됨)**
1. **총타수**가 가장 적은 선수
2. 동타일 경우, **2타수**가 많은 선수
3. 2타수도 같을 경우, **홀인원** 개수가 많은 선수
*(※ 위 조건이 모두 같을 경우 공동 순위로 처리되며, 규정에 따라 연장자순(백카운트) 등은 대회 위원장님의 최종 재량이 필요할 수 있습니다.)*
""")

uploaded_file = st.file_uploader("채점표 엑셀 파일을 업로드해주세요 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        with st.spinner("순위를 계산하고 시상표를 작성 중입니다..."):
            # 1. 엑셀 파일에서 데이터 읽기 
            col_names = [
                '일시', '조', '타순', '소속', '성명', 
                '1일차_총타수', '1일차_2타수', '1일차_홀인원', 
                '2일차_총타수', '2일차_2타수', '2일차_홀인원', 
                '최종_총타수', '최종_2타수', '최종_홀인원'
            ]
            
            # 실제 '개인전 채점표' 시트 읽기
            df = pd.read_excel(uploaded_file, sheet_name='개인전 채점표', skiprows=2, names=col_names)
            
            # 2. 데이터 정제
            df = df.dropna(subset=['성명', '소속'])
            
            score_cols = ['최종_총타수', '최종_2타수', '최종_홀인원']
            for col in score_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                
            df['최종_총타수'] = np.where(df['최종_총타수'] == 0, pd.to_numeric(df['1일차_총타수'], errors='coerce').fillna(0) + pd.to_numeric(df['2일차_총타수'], errors='coerce').fillna(0), df['최종_총타수'])
            df['최종_2타수'] = np.where(df['최종_총타수'] > 0, pd.to_numeric(df['1일차_2타수'], errors='coerce').fillna(0) + pd.to_numeric(df['2일차_2타수'], errors='coerce').fillna(0), df['최종_2타수'])
            df['최종_홀인원'] = np.where(df['최종_총타수'] > 0, pd.to_numeric(df['1일차_홀인원'], errors='coerce').fillna(0) + pd.to_numeric(df['2일차_홀인원'], errors='coerce').fillna(0), df['최종_홀인원'])

            df = df[df['최종_총타수'] > 0].copy()

            # 3. ★ 에러 발생 원인 수정 완료 (0 대신 정확한 열 이름 명시) ★
            df = df.sort_values(by=['최종_총타수', '최종_2타수', '최종_홀인원'], ascending=[True, False, False]).reset_index(drop=True)
            
            df['순위'] = df[['최종_총타수', '최종_2타수', '최종_홀인원']].apply(
                lambda x: (-x['최종_총타수'], x['최종_2타수'], x['최종_홀인원']), axis=1
            ).rank(method='min', ascending=False).astype(int)

            ranking_df = df[['순위', '소속', '성명', '최종_총타수', '최종_2타수', '최종_홀인원']].copy()
            ranking_df.columns = ['순위', '소속', '성명', '총타수', '2타수', '홀인원']

            # 4. 시상자 명단(출력물) 생성
            awards_data = []
            award_titles = ['1위', '2위', '3위', '4위', '5위'] + ['장려상'] * 5
            
            for i, title in enumerate(award_titles):
                if i < len(ranking_df):
                    player = ranking_df.iloc[i]
                    awards_data.append([title, player['소속'], player['성명'], player['총타수'], player['2타수'], player['홀인원']])
                else:
                    awards_data.append([title, '', '', '', '', ''])
                    
            awards_df = pd.DataFrame(awards_data, columns=['구분', '소속', '성명', '총타수', '2타수', '홀인원'])

            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("🥇 개인전 시상자 명단")
                st.dataframe(awards_df, use_container_width=True, hide_index=True)
            with col2:
                st.subheader("📊 전체 최종 순위표")
                st.dataframe(ranking_df, use_container_width=True, hide_index=True)

            # 5. 다운로드 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                ranking_df.to_excel(writer, index=False, sheet_name='개인전 순위표')
                awards_df.to_excel(writer, index=False, sheet_name='개인전 시상(출력물)')
                
            processed_data = output.getvalue()
            
            st.success("채점 및 순위표 생성이 완료되었습니다! 아래 버튼을 눌러 엑셀을 다운로드하세요.")
            st.download_button(
                label="📥 최종 순위표 및 시상명단 엑셀 다운로드",
                data=processed_data,
                file_name="제18회_개인전_최종결과.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except ValueError as ve:
        st.error(f"엑셀 파일 구조 오류: 업로드하신 파일에 '개인전 채점표' 시트가 있는지 확인해주세요. ({ve})")
    except Exception as e:
        st.error(f"오류가 발생했습니다. 파일 형식을 다시 확인해주세요: {e}")