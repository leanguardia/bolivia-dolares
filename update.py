#!/usr/bin/env python3

import json
import statistics
import time
from urllib import request, error
import socket
from datetime import datetime
from zoneinfo import ZoneInfo
import csv

timezone = "America/La_Paz"
fiat = "BOB"
asset = "USDT"


def checkPrices(fiat, asset, tradeType, rows=20, max_retries=3, timeout=10):
    def makeParameters(fiat, asset, tradeType, page, rows):
        return {
            "fiat": fiat,
            "page": page,
            "rows": rows,
            "tradeType": tradeType,
            "asset": asset,
            "countries": [],
            "proMerchantAds": False,
            "shieldMerchantAds": False,
            "filterType": "all",
            "periods": [],
            "additionalKycVerifyFilter": 0,
            "publisherType": None,
            "payTypes": [],
            "classifies": [
                "mass",
                "profession",
                "fiat_trade",
            ],
        }

    def makeRequest(url, data, retry_count=0):
        try:
            req = request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with request.urlopen(req, timeout=timeout) as response:
                if response.getcode() == 200:
                    return json.loads(response.read().decode())
                else:
                    raise Exception(f"HTTP error {response.getcode()}")
        except (error.URLError, socket.timeout) as e:
            if retry_count < max_retries:
                wait_time = 2**retry_count
                print(f"Request failed. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return make_request(url, data, retry_count + 1)
            else:
                raise Exception(f"Max retries reached. Last error: {str(e)}")

    def mode(prices):
        counts = {}
        for i in prices:
            counts[i] = counts.get(i, 0) + 1
        return max(counts, key=counts.get)

    page = 1
    prices = []
    tradable = []

    while True:
        params = makeParameters(fiat, asset, tradeType, page, rows)
        data = json.dumps(params).encode("utf-8")

        response_data = makeRequest(
            "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search", data
        )

        prices.extend([float(entry["adv"]["price"]) for entry in response_data["data"]])
        tradable.extend(
            [float(entry["adv"]["tradableQuantity"]) for entry in response_data["data"]]
        )

        if len(prices) == response_data["total"]:
            break
        else:
            page += 1

    return dict(
        low=min(prices),
        high=max(prices),
        median=statistics.median(prices),
        vwap=sum([price * quantity for price, quantity in zip(prices, tradable)]) / sum(tradable), # volume weighted aveage price
        naive=mode(prices[:len(prices)//10]) # the mode among the bottom (BUY) or top (SELL) decile
    )


def appendPrices(prices, filename, timestamp):

    row = {**{"timestamp": timestamp}, **{i[0]: round(i[1], 2) for i in prices.items()}}

    file_exists = True
    try:
        with open(filename, "r") as f:
            pass
    except FileNotFoundError:
        file_exists = False

    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=row.keys()
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


for tradeType in ["BUY", "SELL"]:
    try:
        start = time.time()
        timestamp = datetime.now(ZoneInfo(timezone)).isoformat(timespec="minutes")
        prices = checkPrices(fiat=fiat, asset=asset, tradeType=tradeType)
        appendPrices(prices, f"{tradeType.lower()}.csv", timestamp)

        print(
            f"{tradeType}: {time.time() - start:.2f} seconds"
        )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
