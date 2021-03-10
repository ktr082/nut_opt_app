import opt_nutrition as on
import free_select_food as fsf
import streamlit as st


# sidebar
st.sidebar.markdown(('# How to use'))
mode = st.sidebar.radio(label='計算モード', options=('単純可視化', '最適化計算'))

if mode == '単純可視化':
    st.sidebar.text(
        '単純可視化の説明')
    fsf.show_free_select_food()

if mode == '最適化計算':
    st.sidebar.text('''
    食材の最大摂取数と摂取栄養倍率範囲を
    選択してください

    最も少ないコストで、指定倍率範囲の
    栄養が取れるように最適化します''')
    st.sidebar.markdown('')
    food_max_num = st.sidebar.number_input(label='同食材最大選択数', min_value=1,
                                           value=8, step=1)
    lower_rate, upper_rate = st.sidebar.slider('Select a range of values', 0.0,
                                               6.0, (0.6, 3.0), 0.1)
    on.show_opt_nutrition(lower_rate, upper_rate, food_max_num)
