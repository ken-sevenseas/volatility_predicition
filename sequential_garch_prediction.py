import yfinance as yf
from arch import arch_model
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import boto3
import os
import zipfile
from statsmodels.graphics.tsaplots import plot_acf

# 諸手数料の設定
TRADING_FEE = 0.001  # 取引手数料（0.1%）
SLIPPAGE = 0.0005  # スリッページ（0.05%）
SPREAD = 0.0003  # スプレッド（0.03%）


def download_data(symbol, start_date, end_date):
    """Yahoo Financeからデータを取得し、リターンを計算"""
    data = yf.download(symbol, start=start_date, end=end_date)
    data["Return"] = np.log(data["Adj Close"] / data["Adj Close"].shift(1))
    data["Abs_Return"] = data["Return"].abs()
    return data.dropna()


def upload_to_s3(local_file, bucket_name, s3_file_name):
    """ローカルファイルをS3にアップロード"""
    s3 = boto3.client("s3")
    try:
        s3.upload_file(local_file, bucket_name, s3_file_name)
        print(f"Upload Successful: {s3_file_name}")
    except Exception as e:
        print(f"Upload failed: {e}")


def zip_folder(folder_path, zip_name):
    """フォルダをZIPに圧縮"""
    zip_file_path = f"{folder_path}/{zip_name}.zip"
    with zipfile.ZipFile(zip_file_path, "w") as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), file)
    return zip_file_path


def plot_returns(data, file_name):
    """リターンとその自己相関のプロット"""
    plt.figure(figsize=(10, 6))
    plt.plot(data["Return"], label="Daily Returns")
    plt.title("Nikkei 225 Daily Returns")
    plt.xlabel("Date")
    plt.ylabel("Return")
    plt.savefig(f"/tmp/{file_name}_returns.png")

    plt.figure(figsize=(10, 5))
    plot_acf(data["Return"], lags=30)
    plt.title("ACF of Nikkei 225 Daily Returns")
    plt.xlabel("Lag")
    plt.ylabel("Autocorrelation")
    plt.savefig(f"/tmp/{file_name}_acf.png")

    plt.figure(figsize=(10, 5))
    plot_acf(data["Abs_Return"], lags=30)
    plt.title("ACF of Absolute Nikkei 225 Daily Returns")
    plt.xlabel("Lag")
    plt.ylabel("Autocorrelation")
    plt.savefig(f"/tmp/{file_name}_abs_acf.png")
    plt.close()


def fit_garch_model(returns, p=1, q=1):
    """GARCHモデルをフィッティング"""
    model = arch_model(returns, vol="Garch", p=p, q=q)
    return model.fit(disp="off")


def run_simulation(
    data, train_size_rate=0.8, initial_balance=10000000, volatility_threshold=5
):
    """アルゴリズムトレードシミュレーション"""
    balance = initial_balance
    balance_history = []
    position = 0  # ロング: 100, ショート: -100

    train_size = int(len(data) * train_size_rate)

    for i in range(train_size, len(data)):
        # リターンデータの取得とGARCHモデルフィッティング
        returns = data["Return"].iloc[i - train_size : i] * 100
        model = fit_garch_model(returns)
        forecast = model.forecast(horizon=1)
        forecast_volatility = np.sqrt(forecast.variance.values[-1, :])[0]

        # ボラティリティに基づくポジション設定
        position = -100 if forecast_volatility > volatility_threshold else 100

        # 当日のリターンで資産更新
        daily_return = data["Return"].iloc[i] / 100
        balance += balance * position * daily_return
        balance_history.append(balance)

    return pd.Series(balance_history, index=data.index[train_size:])


def plot_performance(balance_history, file_name):
    """資産推移のプロットとシャープレシオ、最大ドローダウンの計算"""
    plt.figure(figsize=(10, 6))
    plt.plot(balance_history, label="Total Assets")
    plt.title("Algorithmic Trading Simulation")
    plt.xlabel("Date")
    plt.ylabel("Assets (JPY)")
    plt.legend()
    plt.savefig(f"/tmp/{file_name}.png")

    # シャープレシオ計算
    risk_free_rate = 0.01  # 年率リスクフリーレート
    excess_returns = balance_history.pct_change().dropna() - risk_free_rate / 252
    sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    print(f"シャープレシオ: {sharpe_ratio:.2f}")

    # 最大ドローダウン計算
    drawdown = (balance_history.cummax() - balance_history) / balance_history.cummax()
    max_drawdown = drawdown.max()
    print(f"最大ドローダウン: {max_drawdown:.2%}")

    # ドローダウンのプロット
    plt.figure(figsize=(10, 6))
    plt.plot(drawdown, label="Drawdown", color="red")
    plt.title("Drawdown Transition")
    plt.xlabel("Date")
    plt.ylabel("Drawdown Ratio")
    plt.legend()
    plt.savefig(f"/tmp/{file_name}_drawdown.png")
    plt.close()


def main():
    """メイン処理"""
    # データ取得
    data = download_data("^N225", "2015-01-01", "2024-01-01")
    print(data.head())

    # リターンとそのプロット
    bucket_name = "your-s3-bucket"
    plot_returns(data, "nikkei225")

    # シミュレーション実行
    for i in range(1, 10):
        balance_history = run_simulation(data, i / 10)
        file_name = f"simulation_balance_history_{i/10}"
        plot_performance(balance_history, file_name)
        upload_to_s3(f"/tmp/{file_name}.png", bucket_name, f"{file_name}.png")


if __name__ == "__main__":
    main()
