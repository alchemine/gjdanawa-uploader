import streamlit as st
import pandas as pd

from gjdanawa_uploader.utils.crawling import *


STATE = st.session_state


def initialize_session():
    STATE.id = ""
    STATE.password = ""
    STATE.driver = get_chrome_driver()


def create_property_input(key):
    with st.container():
        col1, col2 = st.columns(2)

    with col1:
        title = st.text_input(
            "매물명", value="고현🏠시장인근주택매매", key=f"title_{key}"
        )
    with col2:
        main_view = st.checkbox(
            "메인매물 노출 (※ 메인노출시 체크해주세요)", key=f"view_{key}"
        )

    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            category1 = st.selectbox(
                "대분류", options=["주택|빌라", "..."], key=f"cat1_{key}"
            )
        with col2:
            category2 = st.selectbox(
                "중분류", options=["중분류1", "중분류2"], key=f"cat2_{key}"
            )
        with col3:
            category3 = st.selectbox(
                "소분류", options=["소분류1", "소분류2"], key=f"cat3_{key}"
            )
        with col4:
            property_type = st.selectbox(
                "매매", options=["매매", "전세", "월세"], key=f"type_{key}"
            )

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            si = st.selectbox("시", options=["경남"], key=f"si_{key}")
        with col2:
            gu = st.selectbox("구", options=["거제시"], key=f"gu_{key}")
        with col3:
            addr = st.selectbox("동", options=["고현동"], key=f"addr_{key}")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            area = st.number_input(
                "면적(㎡)", value=224.00, format="%.2f", key=f"area_{key}"
            )

        with col2:
            deal_type = st.selectbox(
                "중개대상물종류", options=["단독주택"], key=f"deal_type_{key}"
            )
        with col3:
            contract_type = st.selectbox(
                "거래형태", options=["매매"], key=f"contract_type_{key}"
            )

    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            dong = st.number_input("해당동 (단위: 동)", value=1, key=f"dong_{key}")
        with col2:
            total_floor = st.number_input(
                "총층수 (단위: 층)",
                min_value=1,
                value=2,
                step=1,
                key=f"total_floor_{key}",
            )
        with col3:
            direction = st.selectbox(
                "방향(거실기준)", options=["남향"], key=f"direction_{key}"
            )
        with col4:
            floor_type = st.selectbox(
                "해당층수", options=["저층"], key=f"floor_type_{key}"
            )

    with st.container():
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            rooms = st.number_input(
                "방수 (단위: 개)", min_value=0, value=6, step=1, key=f"rooms_{key}"
            )
        with col2:
            bathrooms = st.number_input(
                "욕실수 (단위: 개)",
                min_value=0,
                value=2,
                step=1,
                key=f"bathrooms_{key}",
            )
        with col3:
            parking = st.number_input(
                "총주차수 (단위: 대)",
                min_value=0,
                value=0,
                step=1,
                key=f"parking_{key}",
            )
        with col4:
            elevator_parking = st.number_input(
                "세대당주차수 (단위: 대)",
                min_value=0,
                value=0,
                step=1,
                key=f"elevator_parking_{key}",
            )

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            move_in_date = st.text_input(
                "입주가능일", value="협의가능", key=f"move_in_date_{key}"
            )
        with col2:
            approval_date = st.text_input(
                "사용승인일", value="1995", key=f"approval_date_{key}"
            )

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            management_fee = st.number_input(
                "관리비10만이상 (단위: 만원)", value=0, key=f"management_fee_{key}"
            )
        with col2:
            management_fee_under_10 = st.number_input(
                "관리비10만미만 (단위: 만원)",
                value=0,
                key=f"management_fee_under_10_{key}",
            )

    price_by_type = st.text_input("항목별 금액", key=f"price_by_type_{key}")
    description = st.text_input("항목만", key=f"description_{key}")
    id = st.text_input("매물고유번호", value="5454-20240817-000001", key=f"id_{key}")

    return {
        "카테고리": f"{category1} > {category2} > {category3}",
        "매물 유형": property_type,
        "메인매물 노출": main_view,
        "매물명": title,
        "위치": f"{si} {gu} {addr}",
        "면적": area,
        "중개대상물종류": deal_type,
        "거래형태": contract_type,
        "해당동": dong,
        "방향(거실기준)": direction,
        "총층수": total_floor,
        "해당층수": floor_type,
        "방수": rooms,
        "욕실수": bathrooms,
        "총주차수": parking,
        "세대당주차수": elevator_parking,
        "입주가능일": move_in_date,
        "사용승인일": approval_date,
        "관리비10만이상": management_fee,
        "항목별 금액": price_by_type,
        "관리비10만미만": management_fee_under_10,
        "항목만": description,
        "매물고유번호": id,
    }


def main():
    st.title("GJDanawa 다중 매물 업로더")

    # 로그인 정보 (사이드바)
    with st.sidebar:
        st.header("로그인 정보")
        id_value = st.text_input("아이디", value=STATE.id)
        pw_value = st.text_input("비밀번호", value=STATE.password, type="password")

        if STATE.id and STATE.password:
            pass
        elif id_value and pw_value:
            with st.spinner("로그인 중..."):
                try:
                    url = "https://gjdanawa.com"
                    load_url(STATE.driver, url)

                    id_selector = "#member_id"
                    send_keys(STATE.driver, id_selector, id_value)

                    pw_selector = "#pass"
                    send_keys(STATE.driver, pw_selector, pw_value, enter=True)
                    click_alert(STATE.driver, action="accept")
                    STATE.id, STATE.password = id_value, pw_value
                except:
                    st.error("로그인에 실패했습니다. 다시 시도해주세요.")
                    st.stop()
        else:
            st.stop()
        st.success("로그인 성공!")

    # 매물 정보 입력
    st.header("매물 정보")

    if "property_count" not in STATE:
        STATE.property_count = 1

    properties = []

    # 각 매물에 대한 탭 생성
    tabs = st.tabs([f"매물 {i+1}" for i in range(STATE.property_count)])

    for i, tab in enumerate(tabs):
        with tab:
            property_data = create_property_input(i)
            properties.append(property_data)

    if st.button("매물 추가"):
        STATE.property_count += 1
        st.rerun()

    # 제출 버튼
    if st.button("제출"):
        st.success("매물 정보가 성공적으로 제출되었습니다!")
        st.write("제출된 데이터:")
        st.json(properties)

        # DataFrame으로 표시
        df = pd.DataFrame(properties)
        st.dataframe(df)


if "initialize_session" not in STATE:
    STATE.initialize_session = initialize_session()


if __name__ == "__main__":
    main()
