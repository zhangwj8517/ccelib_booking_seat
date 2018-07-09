import requests
import datetime
import time
import configparser

cf = configparser.ConfigParser()
cf.read('booking.conf')

START_TIME = cf.get("time", "START_TIME")
END_TIME = cf.get("time", "END_TIME")
goodSeatNo = cf.get("seatnos", "goodSeatNo")
userinfo1 = cf.get("users", "userinfo1")
userinfo2 = cf.get("users", "userinfo2")
IP = cf.get("IP_PORT", "IP")
PORT = cf.get("IP_PORT", "PORT")
url = 'http://' + IP + ':' + PORT

print(START_TIME)
print(END_TIME)
print(goodSeatNo)
print(userinfo1)
print(userinfo2)
print(url)


def check_position(user_info):
    try:
        # get 阅览室id :yls_id
        response = requests.post(url + "/seat/yuelanshi_list?mode=local")
        serial_no = response.json()["serialno"]
        response = requests.post(url + "/seat/get_task_status?serialno=" + serial_no)
        if response.json()["content"] == "没有可以预定的阅览室.":
            print(response.json()["content"])
            return False
        else:
            # 获取阅览室ID
            if "排队中请等待." in response.json()["content"]:
                print(response.json()["content"])
                return False

            yls_id = response.json()["content"][0]["id"]

            print("阅览室ID", yls_id)
            # 获取阅览室可订位置列表，并获取排队序号
            response = requests.get(url + '/seat/yuelanshi_seat?mode=local&yuelanshiId=' + yls_id)
            ser_no2 = response.json()["serialno"]
            print("排序号: ", ser_no2)

            # 根据当前的排队序号，查看还有多少可选的位置
            response = requests.get(url + '/seat/get_task_status?serialno=' + ser_no2)
            if (response.json()["content"]) == "没有座位.":
                print("没有座位.")
                return False
            else:
                print("remain seat nums: ", len(response.json()["content"]))
                # 空着的位置有哪些
                remain_seats = []
                for i in range(0, len(response.json()["content"])):
                    remain_seats.append(response.json()["content"][i]["seatno"])
                    # print("all seat no:", response.json()["content"][i]["seatno"])
                print("all seat no: ", str(remain_seats))
                seat_no = '0'
                # 最想要的几个位置还空着的话，就按先后顺序选最想要的位置
                for g in goodSeatNo:
                    if (str(g) in remain_seats) or (g in remain_seats):
                        seat_no = str(g)
                        break
                # 没有选上中意的位置时，取剩余的中间位置
                if seat_no == '0':
                    middle = int(len(response.json()["content"]) / 2)
                    seat_no = response.json()["content"][middle]["seatno"]

                # 根据阅览室id,选取的位置，帐户信息排队并预定位置
                my_data = {'yuelanshiId': yls_id, 'seatNo': seat_no}
                my_data.update(user_info)
                response1 = requests.post(url + '/seat/orderMySeat?mode=local', my_data)
                print(response1.json()["content"])

                # 排队成功后，验证结果，查看是否预定成功
                if "排队成功！" == response1.json()["content"]:
                    check_serialno = response1.json()["serialno"]
                    print("select seatNo: ", seat_no)
                    headers = {
                        "Referer": url + "/seat/XueShengloginByNo.jsp?yid=" + str(
                            yls_id) + "&seatno=" + str(
                            seat_no)}
                    print("headers info :  ", headers)
                    time.sleep(1)
                    response2 = requests.post(
                        url + '/seat/get_task_status?serialno=' + str(check_serialno),
                        headers=headers)

                    # 根据返回信息情况，判断本次是否预定上，或是之前已经预定上
                    print(response2.json()["content"])
                    booking_sd = response2.json()["content"]
                    if ("之前到终端机刷卡" in booking_sd) or ("不可以连续预定." in booking_sd):
                        return True
                    else:
                        return False
    except Exception as e:
        print("Exception: ", e)
        return False


def book_position(user_info):
    NOW_TIME = datetime.datetime.now().time().strftime("%H:%M:%S")
    while True:
        if END_TIME < NOW_TIME < START_TIME:
            print("booking time is not coming, waiting 30 s ...... ")
            time.sleep(30)
            NOW_TIME = datetime.datetime.now().time().strftime("%H:%M:%S")
        else:
            print("start booking ......")
            if check_position(user_info):
                print("Book success !")
                break
            else:
                # print("book fail, wait 10 s ......")
                time.sleep(5)


book_position(userinfo1)
print("next persion:........")
book_position(userinfo2)
