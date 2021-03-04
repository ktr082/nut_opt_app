import pandas as pd
# pd.set_option("display.max_rows",100)
# pd.set_option("display.max_columns",100)
from pulp import *
import plotly.graph_objs as go
import plotly.io as pio
import streamlit as st
import copy


# 定数生成
lower_rate = 0.6
upper_rate = 3.0
food_max_num = 8  # 同じものを何単位食べていいか


def main():
    # データ読み込み
    food_df, req_df = read_csvs(
        "data/food_data.csv", "data/required_nutrition.csv")

    # 定数生成
    nut_num = req_df.shape[1]  # 栄養素の数
    # 最適化の実行
    opted_df, total_cost, opted_food_num = calc_num_by_opt(
        food_df, req_df, food_max_num)
    # 最適化された食材×数量の持つ栄養素を計算
    nut_df_by_opted_food = calc_nut_by_food(opted_df)
    # 可視化用に各食材ごとの栄養素と基準に対する割合を算出
    graph_df, graph_df_rate = make_df_for_graph(
        nut_df_by_opted_food, req_df, opted_df, opted_food_num)
    fig = show_stack_bargraph(
        graph_df_rate, '総摂取栄養グラフ', '基準量に対する割合', opted_food_num)
    add_horizon_line(fig, upper_rate, 'Black', nut_num)
    add_horizon_line(fig, lower_rate, 'Red', nut_num)
    st_display(graph_df_rate, fig)


# CSVの読み込み
def read_csvs(food_path, req_path):
    food_df = pd.read_csv(food_path)
    req_df = pd.read_csv(req_path)
    return food_df, req_df


# 最適化
def calc_num_by_opt(food_df, req_df, food_max_num):

    # 上限制約と下限制約の作成
    lower_limit_df = req_df * lower_rate
    upper_limit_df = req_df * upper_rate
    # 特に個別にコントロールしたいものを書き換え
    lower_limit_df.loc[:, ("食塩相当量")] = 4
    lower_limit_df.loc[:, ("糖質")] = 50
    lower_limit_df.loc[:, ("ビタミンC")] = 50
    lower_limit_df.loc[:, ("エネルギー")] = 2000
    upper_limit_df.loc[:, ("エネルギー")] = 2600
    upper_limit_df.loc[:, ("食塩相当量")] = 12
    upper_limit_df.loc[:, ("糖質")] = 160

    # model,今回はコストの最小化問題
    m = LpProblem(name="opt_nut")
    # 変数
    x = [LpVariable('x%d' % i, cat=LpInteger, lowBound=0, upBound=food_max_num)
         for i in range(len(food_df))]  # 各食品の個数リスト
    # 定数
    price = food_df["値段(税抜)"]
    # 目的関数
    m += lpSum(price * x)
    # 制約式
    for j in range(lower_limit_df.shape[1]):
        m += lpSum(food_df.iloc[:, 4:].iloc[:, j]
                   * x) >= lower_limit_df.iloc[:, j]
    for j in range(upper_limit_df.shape[1]):
        m += lpSum(food_df.iloc[:, 4:].iloc[:, j]
                   * x) <= upper_limit_df.iloc[:, j]

    # 求解と結果表示
    status = m.solve()
    print(LpStatus[status])
    if LpStatus[status] == 'Infeasible':
        print('optNG')
    if LpStatus[status] == 'Optimal':
        print('optOK')
    # m.writeLP('glico.lp')

    # 元のdfに最適化で求まった個数を入れる
    result_df = food_df
    result_df["個数"] = 0
    for i in range(len(food_df)):
        result_df["個数"][i] = value(x[i])
    result_df = result_df[result_df['個数'] != 0]
    result_df.reset_index(drop=True, inplace=True)

    # 値段計算
    total_cost = result_df["値段(税抜)"].sum()

    # 選択された食材数
    opted_food_num = len(result_df)

    return result_df, total_cost, opted_food_num


# 選ばれた食材について総栄養を表示
def calc_nut_by_food(opted_df):
    calc_item_list = list(opted_df.columns[2:-1])
    for food_index in range(len(opted_df)):
        for item in calc_item_list:
            opted_df.loc[food_index, item] = opted_df.loc[food_index,
                                                          item] * opted_df.loc[food_index, '個数']
    nut_df_by_opted_food = opted_df
    return nut_df_by_opted_food


# 食材ごとの栄養素量を計算したテーブルから、基準に対する割合を算出
def make_df_for_graph(nut_df_by_opted_food, req_df, opted_df, opted_food_num):
    total_nut = nut_df_by_opted_food.iloc[:, 4:-1].sum()
    total_nut = pd.DataFrame(total_nut).T

    lower_limit_df = req_df * lower_rate

    graph_df = pd.concat([total_nut, lower_limit_df])
    graph_df = pd.concat([graph_df, req_df])
    graph_df = pd.concat([graph_df, pd.DataFrame(
        round(graph_df.iloc[0]/graph_df.iloc[1], 2)).T])
    graph_df = pd.concat([graph_df, pd.DataFrame(
        round(graph_df.iloc[0]/graph_df.iloc[2], 2)).T])
    graph_df = graph_df.reset_index(drop=True)

    graph_df_rate = opted_df.T.rename(columns=opted_df.T.iloc[0]).drop(
        index=["食品名", "カテゴリ", "値段(税抜)", "重量", "個数"])
    graph_df_rate["合計"] = graph_df_rate.sum(axis=1)
    graph_df_rate["必要量割合"] = pd.DataFrame(graph_df.iloc[4])
    for food in range(opted_food_num):
        graph_df_rate.iloc[:, food] = graph_df_rate.iloc[:,
                                                         food]/graph_df_rate["合計"]*graph_df_rate["必要量割合"]

    return graph_df, graph_df_rate


# グラフ用のデータフレームからグラフを作成
def show_stack_bargraph(df, title, ytitle, opted_food_num):
    data = [go.Bar(x=df.index, y=df.iloc[:, i], name=df.columns[i])
            for i in range(opted_food_num)]
    layout = go.Layout(
        title=go.layout.Title(text=title),
        xaxis=go.layout.XAxis(title=df.index.name),
        yaxis=go.layout.YAxis(title=ytitle),
        barmode="stack",
        width=1000, height=600,
        margin=go.layout.Margin(l=75, r=75, b=100, t=75))
    fig = go.Figure(data=data, layout=layout)
    return fig


# グラフに横線を入れる関数
def add_horizon_line(fig, const, color, nut_num):
    fig.add_shape(type='line',
                  x0=-1, y0=const, x1=nut_num, y1=const,
                  # color:'MediumPurple','LightSeaGreen'ほか
                  line=dict(color=color, width=2, dash="dot"),
                  xref='x',
                  yref='y')
    return fig


# streamlitで描画
def st_display(graph_df_rate, fig):
    # sidebar
    st.sidebar.selectbox('ラベル', ('選択肢1', '選択肢2', '選択肢3'))

    with st.sidebar.beta_container():
        chosen = st.radio(
            'Sorting hat',
            ("Gryffindor", "Ravenclaw", "Hufflepuff", "Slytherin"))
        st.write(f"You are in {chosen} house!")

    # main contents
    st.title('ぼくのかんがえたさいきょうの食生活')
    st.markdown('# Markdown documents')
    st.markdown('# a')
    # st.write(graph_df_rate)
    st.write(graph_df_rate)
    st.write(fig)


main()
