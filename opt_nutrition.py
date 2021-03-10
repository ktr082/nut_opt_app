import pandas as pd
from pulp import *
import plotly.graph_objs as go
import plotly.io as pio
import streamlit as st


# 定数生成
lower_rate = 0.5
upper_rate = 3.0
food_max_num = 8  # 同じものを何単位食べていいか


def show_opt_nutrition(lower_rate, upper_rate, food_max_num):
    # 上の定義変更を受けて最適化を再計算（自動実行）
    opt_status, food_df, total_cost, opted_df, fig = main_process(
        lower_rate, upper_rate, food_max_num)

    # main contents
    st.title('Optimizetion of your diet')
    st.markdown('')
    st.markdown('')

    st.markdown('## 最適化対象食品リスト')
    st.markdown('')
    st.write(food_df)

    st.markdown('')
    st.markdown('')

    # 最適化計算に成功した場合結果を表示、失敗したらアラート
    st.markdown('## 最適化結果')
    if opt_status == 'Optimal':
        st.markdown('### 総コスト : ¥'+str(total_cost))
        opted_df['総重量'] = opted_df['重量']  # なぜかreplaceでうまくいかない
        # 値段処理入れる（TODO）
        st.dataframe(opted_df[['食品名', '個数', '総重量']], 400)
        st.write(fig)
    else:
        st.write('''
        与えられた条件では最適化不可能です
        制約を緩めてください
        ''')


def main_process(lower_rate, upper_rate, food_max_num):
    # データ読み込み
    food_df, req_df = read_csvs(
        'data/food_data.csv', 'data/required_nutrition.csv')

    # 定数生成
    nut_num = req_df.shape[1]  # 栄養素の数
    # 最適化の実行
    opt_status, opted_df, total_cost, opted_food_num = calc_num_by_opt(
        food_df, req_df, lower_rate, upper_rate, food_max_num)
    # 最適化された食材×数量の持つ栄養素を計算
    nut_df_by_opted_food = calc_nut_by_food(opted_df)
    # 可視化用に各食材ごとの栄養素と基準に対する割合を算出
    graph_df, graph_df_rate = make_df_for_graph(
        nut_df_by_opted_food, req_df, opted_df, opted_food_num)
    fig = show_stack_bargraph(
        graph_df_rate, '最適化結果グラフ', '基準量に対する割合', opted_food_num)
    add_horizon_line(fig, upper_rate, 'Blue', nut_num)
    add_horizon_line(fig, 1.0, 'Black', nut_num)
    add_horizon_line(fig, lower_rate, 'Red', nut_num)
    # st_display(food_df, graph_df_rate, fig)
    return opt_status, food_df, total_cost, opted_df, fig


# CSVの読み込み
def read_csvs(food_path, req_path):
    food_df = pd.read_csv(food_path)
    req_df = pd.read_csv(req_path)
    return food_df, req_df


# 最適化
def calc_num_by_opt(food_df, req_df, lower_rate, upper_rate, food_max_num):

    # 上限制約と下限制約の作成
    lower_limit_df = req_df * lower_rate
    upper_limit_df = req_df * upper_rate
    # 特に個別にコントロールしたいものを書き換え
    lower_limit_df.loc[:, ('食塩相当量')] = 4
    lower_limit_df.loc[:, ('糖質')] = 50
    lower_limit_df.loc[:, ('ビタミンC')] = 50
    lower_limit_df.loc[:, ('エネルギー')] = 2000
    upper_limit_df.loc[:, ('エネルギー')] = 2600
    upper_limit_df.loc[:, ('食塩相当量')] = 12
    upper_limit_df.loc[:, ('糖質')] = 160

    # model,今回はコストの最小化問題
    m = LpProblem(name='opt_nut')
    # 変数
    x = [LpVariable('x%d' % i, cat=LpInteger, lowBound=0, upBound=food_max_num)
         for i in range(len(food_df))]  # 各食品の個数リスト
    # 定数
    price = food_df['値段(税抜)']
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
    status = m.solve()  # LpStatus[status] → Infeasible/Optimal
    # m.writeLP('glico.lp')

    # 元のdfに最適化で求まった個数を入れる
    opted_df = food_df
    opted_df['個数'] = 0
    for i in range(len(food_df)):
        opted_df['個数'][i] = value(x[i])
    opted_df = opted_df[opted_df['個数'] != 0]
    opted_df.reset_index(drop=True, inplace=True)
    #opted_df.rename(columns={'重量': '総重量'}, inplace=True)

    # 値段計算
    total_cost = opted_df['値段(税抜)'].sum()

    # 選択された食材数
    opted_food_num = len(opted_df)

    return LpStatus[status], opted_df, total_cost, opted_food_num


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
        index=['食品名', 'カテゴリ', '値段(税抜)', '重量', '個数'])
    graph_df_rate['合計'] = graph_df_rate.sum(axis=1)
    graph_df_rate['必要量割合'] = pd.DataFrame(graph_df.iloc[4])
    for food in range(opted_food_num):
        graph_df_rate.iloc[:, food] = graph_df_rate.iloc[:,
                                                         food]/graph_df_rate['合計']*graph_df_rate['必要量割合']

    return graph_df, graph_df_rate


# グラフ用のデータフレームからグラフを作成
def show_stack_bargraph(df, graph_title, ytitle, opted_food_num):
    data = [go.Bar(x=df.index, y=df.iloc[:, i], name=df.columns[i])
            for i in range(opted_food_num)]
    layout = go.Layout(
        title=go.layout.Title(text=graph_title),
        xaxis=go.layout.XAxis(title=df.index.name),
        yaxis=go.layout.YAxis(title=ytitle),
        barmode='stack',
        width=1000, height=600,
        margin=go.layout.Margin(l=75, r=75, b=100, t=75))
    fig = go.Figure(data=data, layout=layout)
    return fig


# グラフに横線を入れる関数
def add_horizon_line(fig, const, color, nut_num):
    fig.add_shape(type='line',
                  x0=-1, y0=const, x1=nut_num, y1=const,
                  # color:'MediumPurple','LightSeaGreen'ほか
                  line=dict(color=color, width=3, dash='dot'),
                  xref='x',
                  yref='y')
    return fig
