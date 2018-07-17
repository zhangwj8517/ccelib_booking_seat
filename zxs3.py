import requests
import datetime
import time
import configparser
import logging
from multiprocessing import Pool

logger = logging.getLogger("booking seat")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
# 将相应的handler添加在logger对象中
logger.addHandler(ch)

cf = configparser.ConfigParser()
cf.read('booking.conf')

START_TIME = cf.get("time", "START_TIME")
END_TIME = cf.get("time", "END_TIME")
url = cf.get("HTTP_INFO", "url")

# 从配置中读取string类型的位置信息，转换成list类型并strip每个元素
str_goodSeatNo = cf.get("seatnos", "goodSeatNo")
goodSeatNo = []
for j in str_goodSeatNo.split(','):
    goodSeatNo.append(j.strip())

alluserinfo = []
for section in cf.sections():
    if "userinfo" in section:
        alluserinfo.append(dict(cf.items(section)))

logger.info("START_TIME: " + START_TIME)
logger.info("END_TIME: " + END_TIME)
logger.info("url: " + url)
logger.info("good SeatNo list: " + str(goodSeatNo))
logger.debug("all user info: " + str(alluserinfo))


# get 阅览室id :yls_id
def get_ysl_id():
    try:
        yls_id = ''
        response = requests.post(url + "/seat/yuelanshi_list?mode=local")
        if "排队成功" in response.json()["content"]:
            serial_no = response.json()["serialno"]
        else:
            logger.debug(str(response.json()["content"]))
            return yls_id

        response = requests.post(url + "/seat/get_task_status?serialno=" + serial_no)
        content = response.json()["content"]
        if ("没有可以预定的阅览室" in content) or ("排队中请等待" in content):
            logger.info(str(response.json()["content"]))
            return yls_id
        else:
            logger.debug("获取阅览室ID: " + str(response.json()["content"]))
            yls_id = response.json()["content"][0]["id"]
            logger.info("阅览室ID: " + str(yls_id))
            return yls_id
    except Exception as e:
        print("Exception: ", e)
        return yls_id


# 选定位置
def check_position(user_info, yls_id):
    try:
        # 获取阅览室可订位置列表，并获取排队序号
        response = requests.post(url + '/seat/yuelanshi_seat?mode=local&yuelanshiId=' + yls_id)
        ser_no2 = response.json()["serialno"]
        logger.debug("排序号: " + str(ser_no2))
        # 根据当前的排队序号，查看还有多少可选的位置
        # logger.info("查看可选位置......")
        response = requests.post(url + '/seat/get_task_status?serialno=' + ser_no2)
        logger.debug(str(response.json()["content"]))
        content = response.json()["content"]
        if ("没有座位" in content) or ("排队中" in content):
            logger.info(str(response.json()["content"]))
            return False

        logger.info("remain seat num: " + str(len(response.json()["content"])))
        logger.info("remain seat info: " + str(response.json()["content"]))
        # 空着的位置有哪些
        remain_seats = []
        for i in range(0, len(response.json()["content"])):
            remain_seats.append(response.json()["content"][i]["seatno"])

        logger.debug("type([0]seat_no): " + str(type(response.json()["content"][0]["seatno"])))
        logger.debug("all seat no: " + str(remain_seats))
        # 最想要的几个位置还空着的话，就按先后顺序选最想要的位置
        seat_no = '0'
        for g in goodSeatNo:
            if (g in remain_seats) or (int(g) in remain_seats):
                seat_no = g
                logger.debug("str(type(g)): " + str(type(g)))
                break
        # 没有选上中意的位置时，取剩余的中间位置
        if '0' == seat_no:
            middle = int(len(response.json()["content"]) / 2)
            seat_no = response.json()["content"][middle]["seatno"]

        # 根据阅览室id,选取的位置seat_no,帐户信息进行预定
        logger.info("select seatNo: " + str(seat_no))
        my_data = {'yuelanshiId': yls_id, 'seatNo': seat_no}
        my_data.update(user_info)
        logger.debug(url + '/seat/orderMySeat?mode=local' + str(my_data))
        response1 = requests.post(url + '/seat/orderMySeat?mode=local', my_data)

        # 排队成功后，验证结果，查看是否预定成功
        logger.debug(str(response1.json()["content"]))
        if "排队成功！" in response1.json()["content"]:
            check_serialno = response1.json()["serialno"]
            headers = {"Referer": url + "/seat/XueShengloginByNo.jsp?yid=" + str(
                yls_id) + "&seatno=" + str(seat_no)}
            logger.debug("headers info :  " + str(headers))

            # 1秒后，根据返回序列号及之前提交的位置信息，判断本次是否预定上，或是之前已经预定上
            time.sleep(1)
            response2 = requests.post(
                url + '/seat/get_task_status?serialno=' + str(check_serialno),
                headers=headers)
            logger.debug(str(response2.json()["content"]))
            booking_sd = response2.json()["content"]
            if ("之前到终端机刷卡" in booking_sd) or ("不可以连续预定." in booking_sd):
                return True
            else:
                return False
    except Exception as e:
        print("Exception: ", e)
        return False


def book_position():
    # 在指定时间内才开始预定
    now_time = datetime.datetime.now().time().strftime("%H:%M:%S")
    while END_TIME < now_time < START_TIME:
        logger.info("booking time is not coming, waiting 30 s ...... ")
        time.sleep(30)
        now_time = datetime.datetime.now().time().strftime("%H:%M:%S")

    logger.info("start booking ......")
    # get ysl id
    while True:
        ysl_id = get_ysl_id()
        if len(ysl_id) > 0:
            break

    # for every user book seat
    for user_info in alluserinfo:
        while True:
            if check_position(user_info, ysl_id):
                logger.info("Book success !")
                break
            else:
                pass


book_position()
# # main function
# p_cnt = 1
# if __name__ == '__main__':
#     p = Pool(p_cnt)
#     for i in range(p_cnt):
#         p.apply_async(book_position)
#     p.close()
#     p.join()
