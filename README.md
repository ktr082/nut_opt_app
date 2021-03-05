# nut_opt_app

pulpを使った最適化により、最も少ないコストで摂取栄養基準を満たすには何をどれだけ食べれば良いかを計算して可視化するプログラム。
streamlitでアプリ化し、ブラウザ上で制約の変更をして再計算が可能。
今後の実装機能として、PFCバランスの表示などを行う予定。


## /data

ファイル名 | 説明
------------ | -------------
nutrition_data.xlsx | [グリコDB](https://jp.glico.com/cgi-bin/navi/start.cgi?A=go1)から引っ張ってきた食材データ
food_data.csv | 元excelから食材部分だけ抜いたもの
required_nutrition.csv | 元excelから栄養摂取基準だけ抜いたもの
