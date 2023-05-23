'''
functions 
{   
  fetch order book 
  input -> coin_name
  output -> orderbook

  fetch best bid and best ask
  input -> coin_name
  output -> best bid and ask

  generate signature
  input ->  body
  output -> signature

  placing buy/sell limit order
  input -> price/bid, coin_name, quantity, type, secret key, key
  output -> id, orders

  modify price
  input -> id, price, key, secret key
  ouput -> null

  cancel order
  input -> id, key, secret key
  output -> null

  user coin balance

  price of bid ask to be placed
  input-> best_bid,best_ask
  output-> bid price,ask price

  active orders:
  id,price,rem_qty,total_qty
}
Strategy 1: Discard open orders after long time. place buy sell order in qty with proportion to the inventory.
'''
import hmac
import hashlib
import base64
import json
import time
import requests
import math

dict_update = {}
key_file=open("api_key.txt", "r+")
secret_file=open("secret_key.txt", "r+")
key = key_file.read()
secret = secret_file.read()
buy_sell_id ={}
sell_buy_id ={}
ideal_inventory = 0.00227
ideal_qty = 0.00005
init_time=0
last_id =0
min_qty=0.00004
def fetch_order_book(coin_name):
    url = "https://public.coindcx.com/market_data/orderbook?pair="+coin_name
    data=None
    while data==None:
        try:
            response = requests.get(url)
            data = response.json()
        except:
            print("order book ki BT :(")
            time.sleep(1)
            pass
    return data

def best_bid_ask(coin_name):
    url = "https://api.coindcx.com/exchange/ticker"
    response = requests.get(url)
    data = response.json()
    coin_data=[a for a in data if a['market']==coin_name][0]
    best_bid=coin_data["bid"]
    best_ask=coin_data["ask"]
    return {best_bid,best_ask}
    # return data

def generate_signature(body):
    secret_file=open("secret_key.txt", "r+")
    secret = secret_file.read()

    secret_bytes = bytes(secret, encoding='utf-8')
    json_body = json.dumps(body, separators = (',', ':'))

    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    return signature

def placing_order(orders,coin_name):
    body_orders = []
    timeStamp = int(round(time.time() * 1000))
    for i in orders:
        print(i[0])
        # print(round((float)(i[1]),2))
        temp = {
            "side": i[0],  #Toggle between 'buy' or 'sell'.
            "order_type": "limit_order", #Toggle between a 'market_order' or 'limit_order'.
            "market": coin_name, #Replace 'SNTBTC' with your desired market pair.
            "price_per_unit": round((float)(i[1]),2), #This parameter is only required for a 'limit_order'
            "total_quantity": (float)(i[2]), #Replace this with the quantity you want
            "timestamp": timeStamp,
            "ecode": "I"

        }
        body_orders.append(temp)
    body = {
      "orders":body_orders
    }
    
    signature = generate_signature(body)
    json_body = json.dumps(body, separators = (',', ':'))
    key_file=open("api_key.txt", "r+")
    key = key_file.read()

    
    url = "https://api.coindcx.com/exchange/v1/orders/create_multiple"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    response_list=None
    while response_list==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            response_list = response.json()
        except:
            print("place order api ki BT :(")
            time.sleep(1)
            pass
    print(response_list)
    temp=[]
    for i in range(len(orders)):
        temp.append("-1")
    if ("message" in response_list):
        if (response_list["message"]=="Insufficient funds"):
            clear_all_active_orders()
            inventory = user_coin_balance("BTC")["balance"]
            diff = (ideal_inventory-(float)(inventory))
            qty = abs(diff)
            order_book  = fetch_order_book("B-BTC_INR")
            weighted_best_ask= get_weighted_best_ask(qty,order_book)
            weighted_best_bid= get_weighted_best_bid(qty,order_book)
            thoeretical_price=(weighted_best_ask+weighted_best_bid)/2
            order = []
            thoeretical_price = round(thoeretical_price,2)
            temp_order = []
            if(diff>0):
                temp_order = ["buy",str(thoeretical_price),str(qty)]
            else:
                temp_order = ["sell",str(thoeretical_price),str(qty)]
            order.append(temp_order)
            placing_order(order,"BTCINR")

            print(response_list)
            print("funds kam hai")
            return placing_order(orders, coin_name)
        print("clear hone chala")
        # clear_all_active_orders()
        print("clear ho gaya")
        # placing_order(orders, coin_name)
        return temp
    for i in range(len(orders)):
        temp[i]= response_list["orders"][i]["id"]
    return temp

def clear_all_active_orders():
    sell_list=(active_orders("sell"))["orders"]
    buy_list=(active_orders("buy"))["orders"]
    # while(len(sell_list)>0 or len(buy_list)>0):
        # update_active_orders()
    for i in sell_list:
        cancel_order(i["id"])
    for i in buy_list:
        cancel_order(i["id"])
        # sell_list=(active_orders("sell"))["orders"]
        # buy_list=(active_orders("buy"))["orders"]

def modify_price(id,price):
    timeStamp = int(round(time.time() * 1000))
    body = {
      "id": id, # Enter your Order ID here.
      "timestamp": timeStamp,
      "price_per_unit": price # Enter the new-price here
    }
    key_file=open("api_key.txt", "r+")
    key = key_file.read()

    json_body = json.dumps(body, separators = (',', ':'))
    signature=generate_signature(body)
    url = "https://api.coindcx.com/exchange/v1/orders/edit"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    data=None
    while data==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            data = response.json()
        except:
            print("modify order ki BT :(")
            time.sleep(1)
            pass
    return data
    # print(data)

def cancel_order(id):
    timeStamp = int(round(time.time() * 1000))
    body = {
        "id": id, # Enter your Order ID here.
        "timestamp": timeStamp
    }
    key_file=open("api_key.txt", "r+")
    key = key_file.read()
    json_body = json.dumps(body, separators = (',', ':'))

    signature = generate_signature(body)

    url = "https://api.coindcx.com/exchange/v1/orders/cancel"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    data=None
    while data==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            data = response.json()
        except:
            print("order book ki BT :(")
            time.sleep(1)
            pass
    return data

def user_coin_balance(coin_name):
    key_file=open("api_key.txt", "r+")
    key = key_file.read()
    # Generating a timestamp
    timeStamp = int(round(time.time() * 1000))

    body = {
        "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    
    signature = generate_signature(body)

    url = "https://api.coindcx.com/exchange/v1/users/balances"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    data=None
    while data==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            data = response.json()
        except:
            print("user_coin ki BT :(")
            time.sleep(1)
            pass
    # print(data)
    X = [a for a in data if a['currency']==coin_name][0]
    # print(X)
    # print(len(X))
    # print(X)
    # return data["balances"]
    return X

def price_of_new_bid_ask(best_bid,best_ask,coin_name):
    #(spread+20000)*bid/(20000-spread) = ask 
    spread = (20000*(best_ask-best_bid))/(best_bid+best_ask)
    bid = best_bid+1;
    ask = ((bracket_size+20000)*bid)/(20000-bracket_size)
    curr_balance = user_coin_balance(coin_name)
    if(curr_balance>upper_threshold):
        ask=0.996*best_ask
        bid=(ask*(20000-bracket_size))/(bracket_size+20000)
        #formula to move the bracket
    elif(curr_balance<=lower_threshold):
        bid=1.004*best_bid
        ask=ask = ((bracket_size+20000)*bid)/(20000-bracket_size)
    return {bid,ask}

def active_orders(type_):
    key_file=open("api_key.txt", "r+")
    key = key_file.read()
    # Generating a timestamp
    timeStamp = int(round(time.time() * 1000))

    body = {
        "side": type_, # Toggle between a 'buy' or 'sell' order.
        "market": "BTCINR", # Replace 'SNTBTC' with your desired market pair.
        "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    
    signature = generate_signature(body)

    url = "https://api.coindcx.com/exchange/v1/orders/active_orders"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    data=None
    while data==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            data = response.json()
        except:
            print("modify order ki BT :(")
            time.sleep(1)
            pass
    #print(data)
    # X = [a for a in data if a['id']]
    return data

def get_weighted_best_bid(quant,order_book):
    bid_list = order_book['bids']
    weighted_best_bid=0
    avg_price = 0
    qty_encountered=0
    for i in bid_list:
        new_qty_encountered=min(qty_encountered+(float)(bid_list[i]),quant)
        avg_price+=(new_qty_encountered-qty_encountered)*(float)(i)
        qty_encountered=new_qty_encountered
        if(qty_encountered==quant):
            break
    weighted_best_bid = avg_price/quant
    return weighted_best_bid

def get_weighted_best_ask(quant,order_book):
    ask_list = order_book['asks']
    ask_list = dict(reversed(list(ask_list.items())))
    weighted_best_ask=0
    avg_price = 0
    qty_encountered=0
    for i in ask_list:
        new_qty_encountered=min(qty_encountered+(float)(ask_list[i]),quant)
        avg_price+=(new_qty_encountered-qty_encountered)*(float)(i)
        qty_encountered=new_qty_encountered
        if(qty_encountered==quant):
            break
    weighted_best_ask = avg_price/quant
    weighted_best_ask=round(weighted_best_ask, 2)
    return weighted_best_ask

def bracket_shift(curr_theoretical_price,coin_name,buy_val):
    up = curr_theoretical_price-buy_val
    sell_val = curr_theoretical_price+up
    inventory = user_coin_balance("BTC")["balance"]
    diff = abs(ideal_inventory-(float)(inventory))
    diff/=ideal_qty
    frac = min(105.263, ((1.5)**diff) - 1)
    epsilon = (frac*(1.9)*up)/100
    if(ideal_inventory>=(float)(inventory)):
        return epsilon
    else:
        return -epsilon

def order_history():
    url = 'https://api.coindcx.com/exchange/v1/orders/trade_history'
    global last_id
    body = {
        "timestamp": int(round(time.time() * 1000)),
        "limit" : 5000,
        "from_id": 44619738
    }
    print(last_id)
    json_body = json.dumps(body, separators = (',', ':'))
    
    signature = generate_signature(body)
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    data=None
    while data==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            data = response.json()
        except:
            print("order_history ki BT :(")
            time.sleep(1)
            pass
    
    # print(data)
    buy_sum=0
    buy_list=[a for a in data if a['side']=='buy']    # X = [a for a in data if a['id']]
    buy_quant=0
    b=0
    for i in buy_list:
        if (float)(i['quantity'])<=ideal_qty:
            buy_sum+=(float)(i["price"])*(float)(i["quantity"])
            buy_quant+=(float)(i["quantity"])
            b+=1
            # print((float)(i["quantity"]))
    # print(buy_sum)
    sell_sum=0
    sell_list=[a for a in data if a['side']=='sell']
    sell_qty=0
    a=0
    for i in sell_list:
        if (float)(i['quantity'])<=ideal_qty:
            sell_sum+=(float)(i["price"])*(float)(i["quantity"])
            sell_qty+=(float)(i["quantity"])
            a+=1
    # print(sell_sum)
    print(sell_qty, buy_quant)
    avg_buy_price=buy_sum/buy_quant
    avg_sell_price=sell_sum/sell_qty
    # print(avg_buy_price, avg_sell_price)
    thoeretical_price=(avg_sell_price+avg_buy_price)/2
    basis_points=(avg_sell_price-avg_buy_price)*10000/thoeretical_price
    # print(b, a)
    volume=buy_sum+sell_sum
    now=time.time()
    diff_tim=now- init_time
    volpersec=volume/diff_tim
    print("Buy trades are :", b)
    print("Sell trades are:", a)
    print("Average Spread in basis points is :", basis_points)
    print("Average Volume in INR per second is :", volpersec)
    # print(len(sell_list))
    return buy_list[-1]
    
def cancel_multiple_orders(l):
    timeStamp = int(round(time.time() * 1000))
    body = {
        "ids": l # Enter your Order ID here.
    }
    key_file=open("api_key.txt", "r+")
    key = key_file.read()
    json_body = json.dumps(body, separators = (',', ':'))

    signature = generate_signature(body)

    url = "https://api.coindcx.com/exchange/v1/orders/cancel_by_ids"

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    data=None
    while data==None:
        try:
            response = requests.post(url, data = json_body, headers = headers)
            data = response.json()
        except:
            print("cancel multiple orders ki BT :(")
            time.sleep(1)
            pass
    print(data)
    return data

def update_active_orders():
    sell_list=(active_orders("sell"))["orders"]
    # print(sell_list)
    buy_list=(active_orders("buy"))["orders"]
    # print(buy_list)
    order_book = fetch_order_book("B-BTC_INR")
    orders_to_be_placed=[]
    orders_to_be_cancelled=[]
    placed_orders_id=[]
    for i in sell_list:
        corr_buy="0"
        if (i['id'] in sell_buy_id) and (sell_buy_id[i["id"]][1]>=3):
            orders_to_be_cancelled.append(i["id"])
            print("to be cancelled")
        if (i['id'] in sell_buy_id):
            corr_buy=sell_buy_id[i['id']][0]
        # corr_buy = 'ed507bce-8b62-11ec-831f-73da359e7ff3'
        # Case 1: both active
        # print("here1")
        if len([a for a in buy_list if a['id']==corr_buy]) > 0:
            print("updating...")
            # print("here")
            sell_qty = i["remaining_quantity"]
            buy_qty = [a for a in buy_list if a['id']==corr_buy][0]["remaining_quantity"]
            weighted_best_ask= get_weighted_best_ask(sell_qty,order_book)
            weighted_best_bid= get_weighted_best_bid(buy_qty,order_book)
            thoeretical_price=(weighted_best_ask+weighted_best_bid)/2
            spread=weighted_best_ask-weighted_best_bid
            basis_points=spread*10000/thoeretical_price
            our_basis_points=max(11, basis_points-1)
            up=our_basis_points/2
            buy_val=(float)(thoeretical_price*(1-up/10000))
            sell_val=(float)(thoeretical_price*(1+up/10000))
            # inventory based epislon 
            epsilon = bracket_shift(thoeretical_price,"BTCINR",buy_val)
            thoeretical_price+=epsilon
            buy_val+=epsilon
            sell_val+=epsilon
            buy_val=round(buy_val, 2)
            sell_val=round(sell_val, 2)
            orders_to_be_cancelled.append(i["id"])
            orders_to_be_cancelled.append(corr_buy)
            if buy_qty >= min_qty:
                orders_to_be_placed.append(["buy",str(buy_val),str(buy_qty)])
                placed_orders_id.append(corr_buy)
            if sell_qty >=min_qty:
                orders_to_be_placed.append(["sell",str(sell_val),str(sell_qty)])
                placed_orders_id.append(i["id"])
            # modify_price(i["id"],sell_val)
            # modify_price(corr_buy,buy_val)
            buy_sell_id[corr_buy][1]+=1
            sell_buy_id[i["id"]][1]+=1

            # print(buy_val)
            # print(sell_val)
        else:
            print("updating...")
            sell_qty = i["remaining_quantity"]
            weighted_best_ask= get_weighted_best_ask(sell_qty,order_book)
            weighted_best_bid= get_weighted_best_bid(sell_qty,order_book)
            thoeretical_price = (weighted_best_ask+weighted_best_bid)/2
            curr_price = i["price_per_unit"]
            diff = curr_price - weighted_best_bid
            if(diff<=0):
                continue
            a=2
            if (i['id'] in sell_buy_id):
                sell_buy_id[i["id"]][1]+=1
                a=(float)(sell_buy_id[i["id"]][1])
            sell_val = curr_price - 0.3*a*diff
            # print(weighted_best_bid)
            # print(curr_price)
            # print(i["id"])
            # print(sell_val)
            sell_val=round(sell_val, 2)
            orders_to_be_cancelled.append(i["id"])
            if sell_qty >= min_qty:
                orders_to_be_placed.append(["sell",str(sell_val),str(sell_qty)])
                placed_orders_id.append(i["id"])
            # modify_price(i["id"],sell_val)

    for i in buy_list:
        corr_sell="0"
        if (i['id'] in buy_sell_id) and (buy_sell_id[i["id"]][1]>=3):
            orders_to_be_cancelled.append(i["id"])
            print("to be cancelled")
        if (i['id'] in buy_sell_id):
            corr_sell=buy_sell_id[i['id']][0]
        if len([a for a in sell_list if a['id']==corr_sell]) == 0:
            print("updating...")
            buy_qty = i["remaining_quantity"]
            weighted_best_ask= get_weighted_best_ask(buy_qty,order_book)
            weighted_best_bid= get_weighted_best_bid(buy_qty,order_book)
            thoeretical_price = (weighted_best_ask+weighted_best_bid)/2
            curr_price = i["price_per_unit"]
            diff = weighted_best_ask - curr_price
            if(diff<=0):
                continue
            a=2
            if (i['id'] in buy_sell_id):
                buy_sell_id[i["id"]][1]+=1
                a=(float)(buy_sell_id[i["id"]][1])
            buy_val = curr_price + 0.3*a*diff
            buy_val=round(buy_val, 2)
            orders_to_be_cancelled.append(i["id"])
            if buy_qty >= min_qty:
                orders_to_be_placed.append(["buy",str(buy_val),str(buy_qty)])
                placed_orders_id.append(i["id"])
            # modify_price(i["id"],buy_val)
    
    cancel_multiple_orders(orders_to_be_cancelled)
    for j in range(0, len(orders_to_be_placed), 10):
        temp_orders = orders_to_be_placed[j:min(j+10,len(orders_to_be_placed))]
        temp_ids = placing_order(temp_orders,"BTCINR")    
        for i in range(j,min(j+10,len(orders_to_be_placed))):
            if orders_to_be_placed[i][0]=="buy":
                if(placed_orders_id[i] in buy_sell_id):
                    buy_sell_id[temp_ids[i-j]]=buy_sell_id[placed_orders_id[i]]
            else:
                if(placed_orders_id[i] in sell_buy_id):
                    sell_buy_id[temp_ids[i-j]]=sell_buy_id[placed_orders_id[i]]    

def main(coin_name):
    i=0
    while(1==1):
        i+=1
        order_book =fetch_order_book("B-BTC_INR")
        weighted_best_ask= get_weighted_best_ask(ideal_qty,order_book)
        weighted_best_bid= get_weighted_best_bid(ideal_qty,order_book)
        thoeretical_price=(weighted_best_ask+weighted_best_bid)/2
        spread=weighted_best_ask-weighted_best_bid
        basis_points=spread*10000/thoeretical_price
        thoeretical_price=(float)(thoeretical_price)
        # print(thoeretical_price)
        # print(spread)
        # print(basis_points)
        our_basis_points=max(11, basis_points-1)
        up=our_basis_points/2
        # print(up)
        buy_val=(float)(thoeretical_price*(1-up/10000))
        sell_val=(float)(thoeretical_price*(1+up/10000))
        # print(buy_val,sell_val)
        # inventory based epislon 
        epsilon = bracket_shift(thoeretical_price,coin_name,buy_val)
        thoeretical_price+=epsilon
        buy_val+=epsilon
        sell_val+=epsilon
        # print(epsilon)
        buy_val=round(buy_val, 2)
        sell_val=round(sell_val, 2)
        # print(buy_val)
        # print(sell_val)
        print(basis_points)
        # if(i%6==0 and basis_points<6):
        #     update_active_orders()
        # if(i%15==0):
        #     order_history()
        # return
        if basis_points>6:
            print("placing...")
            # print(buy_val)
            temp_l = [["buy",str(buy_val),str(ideal_qty)],["sell",str(sell_val),str(ideal_qty)]]
            [buy_id,sell_id] = placing_order(temp_l,coin_name)
            # buy_id=placing_order(buy_val,"BTCINR",ideal_qty,"buy")
            # sell_id=placing_order(sell_val,"BTCINR",ideal_qty,"sell")
            buy_sell_id[buy_id]=[sell_id,0]
            sell_buy_id[sell_id]=[buy_id,0]
            # print(sell_buy_id)
            # print(buy_sell_id)


# last_id=0            
# clear_all_active_orders()
# init_time=time.time()
main("BTCINR")
# sell_list=(active_orders("sell"))["orders"]
# init=time.time()
# buy_list=(active_orders("buy"))["orders"]
# print(len(buy_list))
# lit=[]
# for i in buy_list:
#     lit.append(i["id"])
# for i in sell_list:
#     lit.append(i["id"])
# for i in lit:
    # modify_price(i, 2400000)
# cancel_multiple_orders(lit)
# tep=[]
# buy=[]
# sell=[]
# te=[]
# tep=["sell", "4000000", "0.00004"]
# te=["buy", "2500000", "0.00004"]
# for i in range(1):
#     buy.append(te)
    # sell.append(tep)
# placing_order(buy, "BTCINR")
# final=time.time()
# print(final-init)
# placing_order(sell, "BTCINR")
# order_history()
# print(sell_list)
# print(buy_list)
# for i in buy_list:
#     cancel_order(i["id"])
# print(sell_list)
# for i in sell_list:
#     cancel_order(i["id"])            
# modify_price(x,3000000)
# print(cancel_order('866b0632-850d-11ec-9274-0b0d2811b786'))
# placing_order(3373000,"BTCINR",ideal_qty,"buy")
# placing_order(4000000,"BTCINR",2,"sell")

# print(user_coin_balance("INR")["balance"])
