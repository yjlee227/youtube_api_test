import streamlit as st
import os
import googleapiclient.discovery
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 초기 설정 ---
st.set_page_config(
    page_title="글로벌 인기 유튜브 동영상",
    page_icon="🎬",
    layout="wide"
)

# --- 상태 관리 --- 
# 페이지가 재실행되어도 유지되어야 하는 값들을 st.session_state에 저장
if 'youtube' not in st.session_state:
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    
    # --- 디버깅 로그 추가 시작 ---
    st.write(f"DEBUG: API_KEY from os.getenv: {API_KEY[:4] + '...' if API_KEY else 'None'}")
    # --- 디버깅 로그 추가 끝 ---

    if API_KEY:
        try:
            st.session_state.youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)
        except Exception as e:
            st.error(f"API 클라이언트 생성 중 오류 발생: {e}")
            st.session_state.youtube = None
    else:
        st.error("🚨 환경 변수 'YOUTUBE_API_KEY'를 찾을 수 없습니다. Streamlit Cloud Secrets를 확인해주세요.")
        st.session_state.youtube = None

# 국가 리스트
COUNTRIES = {
    "대한민국": "KR", "미국": "US", "일본": "JP", "영국": "GB", "프랑스": "FR", 
    "독일": "DE", "캐나다": "CA", "인도": "IN", "브라질": "BR", "베트남": "VN"
}

# --- API 호출 함수 ---
@st.cache_data(ttl=3600)
def get_video_categories(region_code):
    """특정 국가의 동영상 카테고리 리스트를 가져옵니다."""
    if not st.session_state.youtube:
        return {}
    try:
        request = st.session_state.youtube.videoCategories().list(
            part="snippet",
            regionCode=region_code
        )
        response = request.execute()
        categories = {item['snippet']['title']: item['id'] for item in response['items'] if item['snippet'].get('assignable', False)}
        return {"전체": "0", **categories}
    except Exception as e:
        # --- 디버깅 로그 추가 시작 ---
        st.write("DEBUG: Error fetching categories from YouTube API:")
        st.exception(e)
        # --- 디버깅 로그 추가 끝 ---
        return {"전체": "0"}

@st.cache_data(ttl=3600)
def get_popular_videos(region_code, video_category_id="0", max_results=30):
    """YouTube API를 호출하여 인기 동영상 리스트를 가져옵니다."""
    if not st.session_state.youtube:
        st.error("🚨 환경 변수 'YOUTUBE_API_KEY'를 설정하지 않았거나 API 클라이언트 생성에 실패했습니다.")
        return None
    try:
        request_params = {
            'part': "snippet,statistics",
            'chart': "mostPopular",
            'regionCode': region_code,
            'maxResults': max_results
        }
        if video_category_id and video_category_id != "0":
            request_params['videoCategoryId'] = video_category_id
            
        request = st.session_state.youtube.videos().list(**request_params)
        response = request.execute()
        return response.get("items", [])
    except googleapiclient.errors.HttpError as e:
        st.error(f"😭 API 호출 중 오류가 발생했습니다: {e}")
        st.error("API 키가 유효하지 않거나 할당량이 초과되었을 수 있습니다.")
        return None
    except Exception as e:
        st.error(f"😭 알 수 없는 오류가 발생했습니다: {e}")
        return None

# --- 메인 UI 구성 ---
st.title("🌍 글로벌 인기 유튜브 동영상")

# --- 필터링 UI ---
cols = st.columns([2, 2, 1]) # 컬럼 비율 조정
with cols[0]:
    selected_country_name = st.selectbox("국가 선택", list(COUNTRIES.keys()))
    selected_region_code = COUNTRIES[selected_country_name]

with cols[1]:
    categories = get_video_categories(selected_region_code)
    # 카테고리가 성공적으로 로드되었는지 확인 후 selectbox 생성
    if categories:
        selected_category_name = st.selectbox("카테고리 선택", list(categories.keys()))
        selected_category_id = categories[selected_category_name]
    else:
        # 카테고리를 불러오지 못했을 경우 (API 오류 등)
        selected_category_name = st.selectbox("카테고리 선택", ["카테고리 로딩 실패"], disabled=True)
        selected_category_id = None

# --- 동영상 리스트 표시 ---
# 버튼을 누르면 비디오 목록을 표시
if cols[2].button("🔄 동영상 불러오기"):
    if selected_category_id:
        st.markdown("---")
        category_title = f" ({selected_category_name})" if selected_category_id != "0" else ""
        st.header(f"🔥 지금 {selected_country_name}{category_title}에서 가장 인기있는 동영상")

        with st.spinner("동영상을 불러오는 중입니다..."):
            video_items = get_popular_videos(selected_region_code, selected_category_id)

            if video_items:
                video_cols = st.columns(3)
                for i, video in enumerate(video_items):
                    try:
                        with video_cols[i % 3]:
                            with st.container(border=True):
                                snippet = video["snippet"]
                                statistics = video["statistics"]
                                video_id = video["id"]
                                
                                st.image(snippet["thumbnails"]["high"]["url"])
                                st.subheader(f"[{snippet['title']}](https://www.youtube.com/watch?v={video_id})")
                                st.write(f"**채널:** {snippet['channelTitle']}")
                                st.write(f"**조회수:** {int(statistics.get('viewCount', 0)):,}회")
                    except KeyError as e:
                        with video_cols[i % 3]:
                            st.warning(f"⚠️ 일부 동영상 데이터가 누락되었습니다: {e}")
                        continue
            elif st.session_state.youtube:
                st.info("해당 조건의 동영상이 없거나, API를 불러오는 데 실패했습니다.")
    else:
        st.error("카테고리 정보를 불러올 수 없어 동영상을 검색할 수 없습니다.")
else:
    # 초기 화면
    st.info("상단에서 국가와 카테고리를 선택한 후 [동영상 불러오기] 버튼을 눌러주세요.")
