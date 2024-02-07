import matplotlib.pyplot as plt

file_path = 'IBC_time_1000.txt'
time_list = []
s_list = []
s = 0
with open(file_path, 'r') as file:
    # ファイルから行ごとに読み込んでリストにする
    lines = file.readlines()
    
    # 各行を処理する例
    for line in lines:
        s = s+1
        print(s) 
        s_list.append(s)
        time_list.append(float(line.strip()))  # 行末の改行を取り除いて表示



# for time in time_list:
# 	# ヒストグラムを描画
plt.bar(s_list, time_list, color='blue', edgecolor='blue', linewidth=2)

# グラフのタイトルや軸ラベルの追加
plt.title('Frequency Distribution')
plt.xlabel('IBC A → B [s](Time to completion of simulated PoS)')
plt.ylabel('Frequency')

# グラフの保存
plt.savefig('IBC_time_AtoB_1000.png')
plt.clf()

import numpy as np


# ヒストグラムをプロット
plt.hist(time_list, bins=30, density=True, edgecolor='black', alpha=0.7)

# 相対度数密度にするためには、density=Trueを指定します。

# グラフの装飾
plt.xlabel('X-axis')
plt.ylabel('Relative Frequency Density')
plt.title('Histogram with Relative Frequency Density')

# グラフの保存
plt.savefig('IBC_time_AtoB_1000_Density.png')
plt.clf()

# plt.plot(x, y)
# plt.xscale('log')  # x軸を対数スケールに変換
# plt.xlabel('Logarithmic Scale (base 10)')
# plt.ylabel('y')
# plt.title('Plot with Logarithmic x-axis')
# plt.grid(True)
# plt.show()
# plt.show()
# plt.savefig('IBC_time_AtoB_1000_log.png')