import argparse
import random
import re
import time

from loguru import logger
from schedule import every, repeat, run_pending

from daledou import (
    DAY,
    HEADERS,
    MONTH,
    PUSH_CONTENT,
    WEEK,
)
from daledou.utils import (
    create_qq_log,
    get_datetime_weekday,
    init_config,
    push,
    remove_none_and_join,
)


def run_serve():
    parser = argparse.ArgumentParser(description="处理命令行参数")

    parser.add_argument("mode", nargs="?", default="", help="运行模式")
    parser.add_argument("--extra", help="额外的参数")

    args, unknown = parser.parse_known_args()

    if args.mode in ["one", "two", "check"]:
        _run_job(args.mode)
    elif args.mode in ["", "timing"]:
        _run_job("check")
        logger.info("将在 13:10 和 20:01 定时运行...")
        while True:
            run_pending()
            time.sleep(1)
    elif args.mode == "dev":
        _dev_job(unknown)
    else:
        print(f"不存在 {args.mode} 参数")


@repeat(every(2).hours)
def job_timing():
    # 每隔 2 小时检测Cookie有效期
    _run_job("check")


@repeat(every().day.at("13:10"))
def job_one():
    # 每天 13:10 运行第一轮
    _run_job("one")


@repeat(every().day.at("20:01"))
def job_two():
    # 每天 20:01 运行第二轮
    _run_job("two")


def _init_data(data: dict) -> tuple:
    global QQ, YAML, SESSION

    start = time.time()
    PUSH_CONTENT.append(f"【开始时间】\n{get_datetime_weekday()}")

    QQ = data["QQ"]
    YAML = data["YAML"]
    SESSION = data["SESSION"]
    missions: dict[list] = data["MISSIONS"]

    trace: int = create_qq_log(QQ)
    return start, trace, missions


def _run_job(job: str):
    global MISSION_NAME

    for data in init_config():
        if job == "check":
            continue
        start, trace, missions = _init_data(data)

        for func in missions[job]:
            MISSION_NAME = func
            PUSH_CONTENT.append(f"\n【{func}】")
            globals()[func]()

        end = time.time()
        logger.remove(trace)
        PUSH_CONTENT.append(f"\n【运行时长】\n时长：{int(end - start)} s")
        push(f"{QQ} {job}", remove_none_and_join(PUSH_CONTENT))
        PUSH_CONTENT.clear()


def _dev_job(job: list[str]):
    global MISSION_NAME

    for data in init_config():
        start, trace, _ = _init_data(data)

        for func in job:
            MISSION_NAME = func
            PUSH_CONTENT.append(f"\n【{func}】")
            result = globals()[func]()

        end = time.time()
        logger.remove(trace)
        PUSH_CONTENT.append(f"\n【运行时长】\n时长：{int(end - start)} s")
        if result is None:
            print(f"\n------------模拟微信信息------------")
            print(remove_none_and_join(PUSH_CONTENT))
        PUSH_CONTENT.clear()


def get(params: str) -> str:
    """
    发送get请求获取响应内容
    """
    global HTML
    url = f"https://dld.qzapp.z.qq.com/qpet/cgi-bin/phonepk?{params}"
    for _ in range(3):
        res = SESSION.get(url, headers=HEADERS)
        res.encoding = "utf-8"
        HTML = res.text
        if "系统繁忙" not in HTML:
            break
        time.sleep(0.2)
    return HTML


def print_info(message: str, name: str | None = None) -> None:
    """
    打印信息
    """
    if name is None:
        name = MISSION_NAME
    logger.info(f"{QQ} | {name}：{message}")


def find(mode: str = r"<br />(.*?)<", name: str | None = None) -> str | None:
    """
    匹配成功返回首个结果，匹配失败返回None

    无论结果如何都会被打印并写入日志
    """
    match = re.search(mode, HTML, re.S)
    result = match.group(1) if match else None
    print_info(result, name)
    return result


def findall(mode: str) -> list:
    """
    查找大乐斗HTML字符串源码中所有匹配正则表达式的子串
    """
    return re.findall(mode, HTML, re.S)


def 邪神秘宝():
    """
    每天高级秘宝和极品秘宝免费一次或者抽奖一次
    """
    for i in [0, 1]:
        # 免费一次 or 抽奖一次
        get(f"cmd=tenlottery&op=2&type={i}")
        PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))


def 华山论剑():
    """
    每月1~25号每天免费挑战8次，侠士耐久为0时取消出战并更换侠士
    每月26号领取赛季段位奖励
    """

    def 战阵调整() -> bool:
        """
        选择侠士、0耐久侠士取消出战后更改侠士
        """
        # 点击第一战选择侠士/更改侠士
        get("cmd=knightarena&op=viewsetknightlist&pos=0")
        # 获取所有侠士id
        knightid = findall(r"knightid=(\d+)")
        if not knightid:
            PUSH_CONTENT.append(find(r"<p>(.*?)</p>"))
            return False

        # 点击战阵调整
        get("cmd=knightarena&op=viewteam")
        # 获取所有选择侠士pos(即第一、二、三战未出战的pos)
        choose_knight_pos = findall(r'pos=(\d+)">选择侠士')
        # 获取所有更改侠士的耐久、pos、id
        change_knight = findall(r'耐久：(\d+)/.*?pos=(\d+)">更改侠士.*?id=(\d+)')

        knight_durable_0_pos = []
        for d, p, _id in change_knight:
            # 移除更改侠士id
            knightid.remove(_id)
            if d == "0":
                # 筛选0耐久侠士pos
                knight_durable_0_pos.append(p)
                # 0耐久侠士取消出战
                get(f"cmd=knightarena&op=setknight&id={_id}&pos={p}&type=0")

        # 选择/更改侠士
        for p in choose_knight_pos + knight_durable_0_pos:
            # 判断还有没有可用的侠士
            if not knightid:
                print_info("没有可用的侠士")
                PUSH_CONTENT.append("没有可用的侠士")
                break
            _id: str = knightid.pop()
            # 出战
            get(f"cmd=knightarena&op=setknight&id={_id}&pos={p}&type=1")
        return True

    # 每月26号领取赛季段位奖励
    if DAY == 26:
        # 赛季段位奖励
        get(r"cmd=knightarena&op=drawranking")
        PUSH_CONTENT.append(find())
        return

    # 每月1~25号挑战
    for _ in range(10):
        # 华山论剑
        get("cmd=knightarena")
        if "免费挑战" not in HTML:
            print_info("免费挑战次数已用完")
            PUSH_CONTENT.append("免费挑战次数已用完")
            break
        # 免费挑战
        get("cmd=knightarena&op=challenge")
        PUSH_CONTENT.append(find())
        if "增加荣誉点数" in HTML:
            continue

        # 请先设置上阵侠士后再开始战斗
        # 耐久不足
        if not 战阵调整():
            break


def 斗豆月卡():
    """
    每天领取150斗豆:
    """
    # 领取150斗豆
    get("cmd=monthcard&sub=1")
    PUSH_CONTENT.append(find(r"<p>(.*?)<br />"))


def 分享():
    """
    每天一键分享，斗神塔每次挑战11层以增加一次分享次数
    周四领取奖励
    """
    _end = False
    # 达人等级对应斗神塔CD时间
    data = {
        "1": 7,
        "2": 6,
        "3": 5,
        "4": 4,
        "5": 3,
        "6": 2,
        "7": 1,
        "8": 1,
        "9": 1,
        "10": 1,
    }
    # 乐斗达人
    get("cmd=ledouvip")
    if grade := find(r"当前级别：(\d+)", "达人等级"):
        second = data[grade]
    else:
        # 还未成为达人
        second = 10

    for _ in range(9):
        # 一键分享
        get(f"cmd=sharegame&subtype=6")
        find(r"】</p>(.*?)<p>")
        if ("达到当日分享次数上限" in HTML) or _end:
            PUSH_CONTENT.append(find(r"</p><p>(.*?)<br />.*?开通达人"))
            break

        for _ in range(11):
            # 开始挑战 or 挑战下一层
            get("cmd=towerfight&type=0")
            find(name="斗神塔-挑战")
            time.sleep(second)
            if "您" in HTML:
                # 您败给了
                # 您战胜了
                continue

            # 系统繁忙
            # 已经到了塔顶
            # 已经没有剩余的周挑战数
            # 您需要消耗斗神符才能继续挑战斗神塔
            _end = True

    # 自动挑战
    get("cmd=towerfight&type=11")
    find(name="斗神塔-自动挑战")
    for _ in range(10):
        time.sleep(second)
        if "结束挑战" in HTML:
            # 结束挑战
            get("cmd=towerfight&type=7")
            find(name="斗神塔-结束挑战")
            break
        # 挑战下一层
        get("cmd=towerfight&type=0")
        find(name="斗神塔-挑战")

    if WEEK == 4:
        # 领取奖励
        get("cmd=sharegame&subtype=3")
        for s in findall(r"sharenums=(\d+)"):
            # 领取
            get(f"cmd=sharegame&subtype=4&sharenums={s}")
            PUSH_CONTENT.append(find(r"】</p>(.*?)<p>"))


def 乐斗():
    """
    每天开启自动使用体力药水、使用四次贡献药水
    每天乐斗好友BOSS、帮友BOSS以及侠侣页所有
    """
    # 乐斗助手
    get("cmd=view&type=6")
    if "开启自动使用体力药水" in HTML:
        #  开启自动使用体力药水
        get("cmd=set&type=0")
        print_info("开启自动使用体力药水")
        PUSH_CONTENT.append("开启自动使用体力药水")

    for _ in range(4):
        # 使用贡献药水*1
        get("cmd=use&id=3038&store_type=1&page=1")
        if "使用规则" in HTML:
            PUSH_CONTENT.append(find(r"】</p><p>(.*?)<br />"))
            break
        PUSH_CONTENT.append(find())

    # 好友BOSS
    get("cmd=friendlist&page=1")
    for u in findall(r"侠：.*?B_UID=(\d+)"):
        # 乐斗
        get(f"cmd=fight&B_UID={u}")
        PUSH_CONTENT.append(find(r"删</a><br />(.*?)，"))
        if "体力值不足" in HTML:
            break

    # 帮友BOSS
    get("cmd=viewmem&page=1")
    for u in findall(r"侠：.*?B_UID=(\d+)"):
        # 乐斗
        get(f"cmd=fight&B_UID={u}")
        PUSH_CONTENT.append(find(r"侠侣</a><br />(.*?)，"))
        if "体力值不足" in HTML:
            break

    # 侠侣
    get("cmd=viewxialv&page=1")
    uin = findall(r"：.*?B_UID=(\d+)")
    if not uin:
        print_info("侠侣未找到uin")
        PUSH_CONTENT.append("侠侣未找到uin")
        return
    for u in uin[1:]:
        # 乐斗
        get(f"cmd=fight&B_UID={u}")
        if "使用规则" in HTML:
            PUSH_CONTENT.append(find(r"】</p><p>(.*?)<br />"))
        elif "查看乐斗过程" in HTML:
            PUSH_CONTENT.append(find(r"删</a><br />(.*?)！"))
        if "体力值不足" in HTML:
            break


def 报名():
    """
    每天报名武林大会、笑傲群侠
    周二、五、日报名侠侣争霸
    """
    # 武林大会
    get("cmd=fastSignWulin&ifFirstSign=1")
    if "使用规则" in HTML:
        PUSH_CONTENT.append(find(r"】</p><p>(.*?)<br />"))
    else:
        PUSH_CONTENT.append(find(r"升级。<br />(.*?) "))

    # 侠侣争霸
    if WEEK in [2, 5, 7]:
        get("cmd=cfight&subtype=9")
        if "使用规则" in HTML:
            PUSH_CONTENT.append(find(r"】</p><p>(.*?)<br />"))
        else:
            PUSH_CONTENT.append(find(r"报名状态.*?<br />(.*?)<br />"))

    # 笑傲群侠
    get("cmd=knightfight&op=signup")
    PUSH_CONTENT.append(find(r"侠士侠号.*?<br />(.*?)<br />"))


def 巅峰之战进行中():
    """
    周一、二随机加入及领奖
    周三、四、五、六、日征战
    """
    if WEEK in [1, 2]:
        # 随机加入
        get("cmd=gvg&sub=4&group=0&check=1")
        PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))
        # 领奖
        get("cmd=gvg&sub=1")
        PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))
        return

    for _ in range(14):
        # 征战
        get("cmd=gvg&sub=5")
        if "你在巅峰之战中" in HTML:
            if "战线告急" in HTML:
                PUSH_CONTENT.append(find(r"支援！<br />(.*?)。"))
            else:
                PUSH_CONTENT.append(find(r"】</p>(.*?)。"))
            continue

        # 冷却时间
        # 撒花祝贺
        # 请您先报名再挑战
        # 您今天已经用完复活次数了
        if "战线告急" in HTML:
            PUSH_CONTENT.append(find(r"支援！<br />(.*?)<br />"))
        else:
            PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))
        break


def 矿洞():
    """
    每天挑战三次
    领取通关领取
    开启副本
    """
    yaml: dict = YAML["矿洞"]
    f = yaml["floor"]
    m = yaml["mode"]

    # 矿洞
    get("cmd=factionmine")
    for _ in range(5):
        if "副本挑战中" in HTML:
            # 挑战
            get("cmd=factionmine&op=fight")
            PUSH_CONTENT.append(find())
            if "挑战次数不足" in HTML:
                break
        elif "开启副本" in HTML:
            # 确认开启
            get(f"cmd=factionmine&op=start&floor={f}&mode={m}")
            PUSH_CONTENT.append(find())
            if "当前不能开启此副本" in HTML:
                break
        elif "领取奖励" in HTML:
            get("cmd=factionmine&op=reward")
            PUSH_CONTENT.append(find())


def 掠夺():
    """
    周二掠夺一次（各粮仓中第一个最低战斗力的成员）、领奖
    周三领取胜负奖励、报名
    """
    if WEEK == 3:
        # 领取胜负奖励
        get("cmd=forage_war&subtype=6")
        PUSH_CONTENT.append(find())
        # 报名
        get("cmd=forage_war&subtype=1")
        PUSH_CONTENT.append(find())
        return

    # 掠夺
    get("cmd=forage_war")
    if "本轮轮空" in HTML:
        PUSH_CONTENT.append(find(r"本届战况：(.*?)<br />"))
        return
    elif "未报名" in HTML:
        PUSH_CONTENT.append(find(r"本届战况：(.*?)<br />"))
        return

    # 掠夺
    get("cmd=forage_war&subtype=3")
    data = []
    if gra_id := findall(r'gra_id=(\d+)">掠夺'):
        for _id in gra_id:
            get(f"cmd=forage_war&subtype=3&op=1&gra_id={_id}")
            if zhanli := find(r"<br />1.*? (\d+)\."):
                data.append((int(zhanli), _id))
        if data:
            _, _id = min(data)
            get(f"cmd=forage_war&subtype=4&gra_id={_id}")
            PUSH_CONTENT.append(find())
    else:
        print_info("已占领对方全部粮仓")
        PUSH_CONTENT.append("已占领对方全部粮仓")

    # 领奖
    get("cmd=forage_war&subtype=5")
    PUSH_CONTENT.append(find())


def 踢馆():
    """
    周五试炼5次、高倍转盘一次、挑战至多30次
    周六报名及领奖
    """
    if WEEK == 6:
        # 报名
        get("cmd=facchallenge&subtype=1")
        PUSH_CONTENT.append(find())
        # 领奖
        get("cmd=facchallenge&subtype=7")
        PUSH_CONTENT.append(find())
        return

    def generate_sequence():
        # 试炼、高倍转盘序列
        for t in [2, 2, 2, 2, 2, 4]:
            yield t
        # 挑战序列
        for _ in range(30):
            yield 3

    for t in generate_sequence():
        get(f"cmd=facchallenge&subtype={t}")
        PUSH_CONTENT.append(find())
        if "您的复活次数已耗尽" in HTML:
            break
        elif "您的挑战次数已用光" in HTML:
            break
        elif "你们帮没有报名参加这次比赛" in HTML:
            break


def 竞技场():
    """
    每月1~25号每天至多挑战10次、领取奖励、竞技点商店yaml配置默认不兑换
    """
    for _ in range(10):
        # 免费挑战 or 开始挑战
        get("cmd=arena&op=challenge")
        PUSH_CONTENT.append(find())
        if "免费挑战次数已用完" in HTML:
            break

    # 领取奖励
    get("cmd=arena&op=drawdaily")
    PUSH_CONTENT.append(find())

    if _id := YAML["竞技场"]:
        # 兑换10个
        get(f"cmd=arena&op=exchange&id={_id}&times=10")
        PUSH_CONTENT.append(find())


def 十二宫():
    """
    每天请猴王扫荡yaml配置的关卡
    """
    _id: int = YAML["十二宫"]
    # 请猴王扫荡
    get(f"cmd=zodiacdungeon&op=autofight&scene_id={_id}")
    if "恭喜你" in HTML:
        PUSH_CONTENT.append(find(r"恭喜你，(.*?)！"))
        return
    elif "是否复活再战" in HTML:
        PUSH_CONTENT.append(find(r"<br.*>(.*?)，"))
        return

    # 你已经不幸阵亡，请复活再战！
    # 挑战次数不足
    # 当前场景进度不足以使用自动挑战功能
    PUSH_CONTENT.append(find(r"<p>(.*?)<br />"))


def 许愿():
    """
    每天领取许愿奖励、上香许愿、领取魂珠碎片宝箱
    """
    for sub in [5, 1, 6]:
        get(f"cmd=wish&sub={sub}")
        PUSH_CONTENT.append(find())


def 抢地盘():
    """
    每天无限制区攻占一次第10位

    等级  30级以下 40级以下 ... 120级以下 无限制区
    type  1       2            10        11
    """
    get("cmd=recommendmanor&type=11&page=1")
    if manorid := findall(r'manorid=(\d+)">攻占</a>'):
        # 攻占
        get(f"cmd=manorfight&fighttype=1&manorid={manorid[-1]}")
        PUSH_CONTENT.append(find(r"</p><p>(.*?)。"))
    # 兑换武器
    get("cmd=manor&sub=0")
    PUSH_CONTENT.append(find(r"<br /><br />(.*?)<br /><br />"))


def 历练():
    """
    取消自动使用活力药水
    每天乐斗yaml配置指定的关卡BOSS3次
    """
    yaml: list = YAML["历练"]

    # 乐斗助手
    get("cmd=view&type=6")
    if "取消自动使用活力药水" in HTML:
        #  取消自动使用活力药水
        get("cmd=set&type=11")
        print_info("取消自动使用活力药水")
        PUSH_CONTENT.append("取消自动使用活力药水")

    for _id in yaml:
        for _ in range(3):
            get(f"cmd=mappush&subtype=3&mapid=6&npcid={_id}&pageid=2")
            if "您还没有打到该历练场景" in HTML:
                PUSH_CONTENT.append(find(r"介绍</a><br />(.*?)<br />"))
                break
            PUSH_CONTENT.append(find(r"阅历值：\d+<br />(.*?)<br />"))
            if "活力不足" in HTML:
                return
            elif "挑战次数已经达到上限了，请明天再来挑战吧" in HTML:
                break
            elif "还不能挑战" in HTML:
                break


def 镖行天下():
    """
    每天拦截3次、领取奖励、刷新押镖并启程护送
    """
    for op in [16, 8, 6]:
        # 领取奖励 》刷新押镖 》启程护送
        get(f"cmd=cargo&op={op}")
        PUSH_CONTENT.append(find())

    for _ in range(5):
        # 刷新
        get("cmd=cargo&op=3")
        for uin in findall(r'passerby_uin=(\d+)">拦截'):
            # 拦截
            get(f"cmd=cargo&op=14&passerby_uin={uin}")
            _msg = find()
            if "系统繁忙" in HTML:
                continue
            elif "这个镖车在保护期内" in HTML:
                continue
            elif "您今天已达拦截次数上限了" in HTML:
                return
            PUSH_CONTENT.append(_msg)


def 幻境():
    """
    每天乐斗yaml配置的关卡
    """
    stage_id: int = YAML["幻境"]
    get(f"cmd=misty&op=start&stage_id={stage_id}")
    for _ in range(5):
        # 乐斗
        get(f"cmd=misty&op=fight")
        PUSH_CONTENT.append(find(r"星数.*?<br />(.*?)<br />"))
        if "尔等之才" in HTML:
            break
    # 返回飘渺幻境
    get("cmd=misty&op=return")


def 群雄逐鹿():
    """
    周六报名、领奖
    """
    for op in ["signup", "drawreward"]:
        get(f"cmd=thronesbattle&op={op}")
        PUSH_CONTENT.append(find(r"届群雄逐鹿<br />(.*?)<br />"))


def 画卷迷踪():
    """
    每天至多挑战20次
    """
    for _ in range(20):
        # 准备完成进入战斗
        get("cmd=scroll_dungeon&op=fight&buff=0")
        PUSH_CONTENT.append(find(r"选择</a><br /><br />(.*?)<br />"))
        if "没有挑战次数" in HTML:
            break
        elif "征战书不足" in HTML:
            break


def 门派():
    """
    万年寺：点燃普通香炉 》点燃高香香炉
    八叶堂：进入木桩训练 》进入同门切磋
    五花堂：至多完成任务3次
    """
    # 点燃普通香炉 》点燃高香香炉
    for op in ["fumigatefreeincense", "fumigatepaidincense"]:
        get(f"cmd=sect&op={op}")
        PUSH_CONTENT.append(find(r"修行。<br />(.*?)<br />"))

    # 进入木桩训练 》进入同门切磋
    for op in ["trainingwithnpc", "trainingwithmember"]:
        get(f"cmd=sect&op={op}")
        PUSH_CONTENT.append(find())

    # 五花堂
    wuhuatang = get("cmd=sect_task")
    missions = {
        "进入华藏寺看一看": "cmd=sect_art",
        "进入伏虎寺看一看": "cmd=sect_trump",
        "进入金顶看一看": "cmd=sect&op=showcouncil",
        "进入八叶堂看一看": "cmd=sect&op=showtraining",
        "进入万年寺看一看": "cmd=sect&op=showfumigate",
        "与掌门人进行一次武艺切磋": "cmd=sect&op=trainingwithcouncil&rank=1&pos=1",
        "与首座进行一次武艺切磋": "cmd=sect&op=trainingwithcouncil&rank=2&pos=1",
        "与堂主进行一次武艺切磋": "cmd=sect&op=trainingwithcouncil&rank=3&pos=1",
    }
    for name, url in missions.items():
        if name in wuhuatang:
            print_info(name)
            get(url)
    if "查看一名" in wuhuatang:
        # 查看一名同门成员的资料 or 查看一名其他门派成员的资料
        print_info("查看好友第二页所有成员")
        # 好友第2页
        get(f"cmd=friendlist&page=2")
        for uin in findall(r"\d+：.*?B_UID=(\d+).*?级"):
            # 查看好友
            get(f"cmd=totalinfo&B_UID={uin}")
    if "进行一次心法修炼" in wuhuatang:
        """
        少林心法      峨眉心法    华山心法      丐帮心法    武当心法      明教心法
        101 法华经    104 斩情决  107 御剑术   110 醉拳    113 太极内力  116 圣火功
        102 金刚经    105 护心决  108 龟息术   111 烟雨行  114 绕指柔剑  117 五行阵
        103 达摩心经  106 观音咒  109 养心术   112 笑尘诀  115 金丹秘诀  118 日月凌天
        """
        for art_id in range(101, 119):
            get(f"cmd=sect_art&subtype=2&art_id={art_id}&times=1")
            find()
            if "你的心法已达顶级无需修炼" in HTML:
                continue
            # 修炼成功
            # 你的门派贡献不足无法修炼
            break

    # 五花堂
    get("cmd=sect_task")
    for task_id in findall(r'task_id=(\d+)">完成'):
        # 完成
        get(f"cmd=sect_task&subtype=2&task_id={task_id}")
        PUSH_CONTENT.append(find())


def 门派邀请赛():
    """
    周一、二报名、领取奖励、兑换10个yaml配置的材料
    周三、四、五、六、日开始挑战至多10次
    """
    if WEEK in [1, 2]:
        # 组队报名
        get("cmd=secttournament&op=signup")
        PUSH_CONTENT.append(find())
        # 领取奖励
        get("cmd=secttournament&op=getrankandrankingreward")
        PUSH_CONTENT.append(find())
        if t := YAML["门派邀请赛"]:
            # 兑换10个
            get(f"cmd=exchange&subtype=2&type={t}&times=10&costtype=11")
            PUSH_CONTENT.append(find())
        return

    for _ in range(5):
        # 兑换门派战书*1
        get("cmd=exchange&subtype=2&type=1249&times=1&costtype=11")
        PUSH_CONTENT.append(find())
        if "积分不足" in HTML:
            break
    for _ in range(10):
        # 开始挑战
        get("cmd=secttournament&op=fight")
        PUSH_CONTENT.append(find())
        if "已达最大挑战上限" in HTML:
            break
        elif "门派战书不足" in HTML:
            break


def 会武():
    """
    周一、二、三初、中、高级试炼场挑战至多21次、yaml配置是否兑换试炼书*1
    周四助威丐帮
    周五兑换10个真黄金卷轴*10
    周六、日领奖
    """
    if WEEK == 4:
        # 冠军助威 丐帮
        get("cmd=sectmelee&op=cheer&sect=1003")
        # 冠军助威
        get("cmd=sectmelee&op=showcheer")
        PUSH_CONTENT.append(find())
    elif WEEK == 5:
        for _ in range(10):
            # 兑换 真黄金卷轴*10
            get("cmd=exchange&subtype=2&type=1263&times=10&costtype=13")
            PUSH_CONTENT.append(find())
            if "积分不足" in HTML:
                break
    elif WEEK in [6, 7]:
        # 领奖
        get("cmd=sectmelee&op=showreward")
        PUSH_CONTENT.append(find(r"<br />(.*?)。"))
        PUSH_CONTENT.append(find(r"。<br />(.*?)。"))
        # 领取
        get("cmd=sectmelee&op=drawreward")
        if "本届已领取奖励" in HTML:
            PUSH_CONTENT.append(find(r"规则</a><br />(.*?)<br />"))
        else:
            PUSH_CONTENT.append(find())

    if WEEK not in [1, 2, 3]:
        return

    _is_exchange: bool = YAML["会武"]
    for _ in range(21):
        # 挑战
        get("cmd=sectmelee&op=dotraining")
        if "试炼场】" in HTML:
            PUSH_CONTENT.append(find(r"最高伤害：\d+<br />(.*?)<br />"))
            continue
        PUSH_CONTENT.append(find(r"规则</a><br />(.*?)<br />"))
        if "你已达今日挑战上限" in HTML:
            break
        elif "你的试炼书不足" in HTML:
            if not _is_exchange:
                break
            # 兑换 试炼书*1
            get("cmd=exchange&subtype=2&type=1265&times=1&costtype=13")
            PUSH_CONTENT.append(find())
            if "积分不足" in HTML:
                break


def 梦想之旅():
    """
    每天一次普通旅行
    周四如果当前区域已去过至少7个目的地，那么消耗梦幻机票解锁剩下所有未去过的目的地
    周四领取区域礼包、超级礼包
    """
    # 普通旅行
    get("cmd=dreamtrip&sub=2")
    PUSH_CONTENT.append(find())

    if WEEK != 4:
        return

    if (count := HTML.count("已去过")) < 7:
        _msg = f"已去过 {count} （大于等于7才会消耗梦幻机票）"
        print_info(_msg)
        PUSH_CONTENT.append(_msg)
        return

    # 获取当前区域所有未去过的目的地
    place = findall(r"([\u4e00-\u9fa5\s\-]+)(?=\s未去过)")
    if not place:
        print_info("当前区域全部已去过")
        PUSH_CONTENT.append("当前区域全部已去过")
    else:
        bmapid = find(r'bmapid=(\d+)">梦幻旅行')
    for name in place:
        # 梦幻旅行
        get(f"cmd=dreamtrip&sub=3&bmapid={bmapid}")
        s = find(f"{name}.*?smapid=(\d+)")
        # 去这里
        get(f"cmd=dreamtrip&sub=2&smapid={s}")
        PUSH_CONTENT.append(find())

    # 领取礼包
    for _ in range(2):
        if b := findall(r"sub=4&amp;bmapid=(\d+)"):
            # 区域礼包 1 or 2 or 3 or 4
            # 超级礼包 0
            get(f"cmd=dreamtrip&sub=4&bmapid={b[0]}")
            PUSH_CONTENT.append(find())


def 问鼎天下():
    """
    周一领取奖励
    周一、二、三、四、五领取帮资或放弃资源点、东海攻占倒数第一个
    周六淘汰赛助威yaml配置的帮派
    周日排名赛助威yaml配置的帮派
    """
    if WEEK == 6:
        # 淘汰赛助威
        _id = YAML["问鼎天下"]["淘汰赛"]
        get(f"cmd=tbattle&op=cheerregionbattle&id={_id}")
        PUSH_CONTENT.append(find())
    elif WEEK == 7:
        # 排名赛助威
        _id = YAML["问鼎天下"]["排名赛"]
        get(f"cmd=tbattle&op=cheerchampionbattle&id={_id}")
        PUSH_CONTENT.append(find())

    if WEEK in [6, 7]:
        return

    if WEEK == 1:
        # 领取奖励
        get("cmd=tbattle&op=drawreward")
        PUSH_CONTENT.append(find())

    # 问鼎天下
    get("cmd=tbattle")
    if "你占领的领地已经枯竭" in HTML:
        # 领取
        get("cmd=tbattle&op=drawreleasereward")
        PUSH_CONTENT.append(find())
    elif "放弃" in HTML:
        # 放弃
        get("cmd=tbattle&op=abandon")
        PUSH_CONTENT.append(find())

    # 1东海 2南荒 3西泽 4北寒
    get("cmd=tbattle&op=showregion&region=1")
    # 攻占 倒数第一个
    if _id := findall(r"id=(\d+).*?攻占</a>"):
        get(f"cmd=tbattle&op=occupy&id={_id[-1]}&region=1")
        PUSH_CONTENT.append(find())


def 帮派商会():
    """
    每天帮派宝库领取礼包、交易会所交易物品、兑换商店兑换物品
    """
    yaml: dict = YAML["帮派商会"]
    jiaoyi = yaml["交易会所"]
    duihuan = yaml["兑换商店"]
    data_1 = []
    data_2 = []

    for _ in range(10):
        # 帮派宝库
        get("cmd=fac_corp&op=0")
        if mode := findall(r'gift_id=(\d+)&amp;type=(\d+)">点击领取'):
            for _id, t in mode:
                get(f"cmd=fac_corp&op=3&gift_id={_id}&type={t}")
                PUSH_CONTENT.append(find(r"</p>(.*?)<br />", "帮派商会-帮派宝库"))
        else:
            print_info("没有礼包领取", "帮派商会-帮派宝库")
            PUSH_CONTENT.append("没有礼包领取")
            break

    # 交易会所
    get("cmd=fac_corp&op=1")
    if "已交易" not in HTML:
        for mode in jiaoyi:
            data_1 += findall(f"{mode}.*?type=(\d+)&amp;goods_id=(\d+)")
        for t, _id in data_1:
            # 兑换
            get(f"cmd=fac_corp&op=4&type={t}&goods_id={_id}")
            PUSH_CONTENT.append(find(r"</p>(.*?)<br />", f"帮派商会-交易-{_id}"))

    # 兑换商店
    get("cmd=fac_corp&op=2")
    if "已兑换" not in HTML:
        for mode in duihuan:
            data_2 += findall(f"{mode}.*?type_id=(\d+)")
        for t in data_2:
            get(f"cmd=fac_corp&op=5&type_id={t}")
            PUSH_CONTENT.append(find(r"</p>(.*?)<br />", f"帮派商会-兑换-{t}"))


def 帮派远征军():
    """
    周一、二、三、四、五、六、日参战攻击
    周日领取奖励
    """

    def attack(p: str, u: str) -> bool:
        # 攻击
        get(f"cmd=factionarmy&op=fightWithUsr&point_id={p}&opp_uin={u}")
        if "【帮派远征军-征战结束】" in HTML:
            _msg = find()
            if "您未能战胜" in HTML:
                PUSH_CONTENT.append(_msg)
                return True
        elif "【帮派远征军】" in HTML:
            PUSH_CONTENT.append(find(r"<br /><br />(.*?)</p>"))
            if "您的血量不足" in HTML:
                return True
        return False

    _end = False
    while True:
        # 帮派远征军
        get("cmd=factionarmy&op=viewIndex&island_id=-1")
        point_id = findall(r'point_id=(\d+)">参战')
        if not point_id:
            print_info("已经全部通关了，周日领取奖励")
            PUSH_CONTENT.append("已经全部通关了，周日领取奖励")
            break
        for p in point_id:
            # 参战
            get(f"cmd=factionarmy&op=viewpoint&point_id={p}")
            for u in findall(r'opp_uin=(\d+)">攻击'):
                if attack(p, u):
                    _end = True
                    break
        if _end:
            break

    if WEEK != 7:
        return

    # 领取奖励
    for p_id in range(15):
        get(f"cmd=factionarmy&op=getPointAward&point_id={p_id}")
        if "【帮派远征军】" in HTML:
            PUSH_CONTENT.append(find(r"<br /><br />(.*?)</p>"))
            if "点尚未攻占下来" in HTML:
                break
            continue
        PUSH_CONTENT.append(find())

    # 领取岛屿宝箱
    for i_id in range(5):
        get(f"cmd=factionarmy&op=getIslandAward&island_id={i_id}")
        if "【帮派远征军】" in HTML:
            PUSH_CONTENT.append(find(r"<br /><br />(.*?)</p>"))
            if "岛尚未攻占下来" in HTML:
                break
            continue
        PUSH_CONTENT.append(find())


def 帮派黄金联赛():
    """
    领取奖励、领取帮派赛季奖励、参与防守、参战攻击
    """
    # 帮派黄金联赛
    get("cmd=factionleague&op=0")
    if "领取奖励" in HTML:
        # 领取轮次奖励
        get("cmd=factionleague&op=5")
        PUSH_CONTENT.append(find(r"<p>(.*?)<br /><br />"))
    elif "领取帮派赛季奖励" in HTML:
        # 领取帮派赛季奖励
        get("cmd=factionleague&op=7")
        PUSH_CONTENT.append(find(r"<p>(.*?)<br /><br />"))
    elif "已参与防守" not in HTML:
        # 参与防守
        get("cmd=factionleague&op=1")
        PUSH_CONTENT.append(find(r"<p>(.*?)<br /><br />"))
    elif "休赛期" in HTML:
        print_info("休赛期无任何操作")
        PUSH_CONTENT.append("休赛期无任何操作")

    if "op=2" not in HTML:
        return

    # 参战
    get("cmd=factionleague&op=2")
    if "opp_uin" not in HTML:
        print_info("没有可攻击的敌人")
        PUSH_CONTENT.append("没有可攻击的敌人")
        return

    uin = []
    if pages := find(r'pages=(\d+)">末页'):
        _pages = pages
    else:
        _pages = 1
    for p in range(1, int(_pages) + 1):
        get(f"cmd=factionleague&op=2&pages={p}")
        uin += findall(r"%&nbsp;&nbsp;(\d+).*?opp_uin=(\d+)")

    # 按战力从低到高排序
    uins = sorted(uin, key=lambda x: float(x[0]))
    for _, u in uins:
        # 攻击
        get(f"cmd=factionleague&op=4&opp_uin={u}")
        if "不幸战败" in HTML:
            PUSH_CONTENT.append(find())
            break
        elif "您已阵亡" in HTML:
            PUSH_CONTENT.append(find(r"<br /><br />(.*?)</p>"))
            break
        find()


def 任务派遣中心():
    """
    每天领取奖励、接受任务
    """
    # 任务派遣中心
    get("cmd=missionassign&subtype=0")
    for _id in findall(r'mission_id=(.*?)">查看'):
        # 领取奖励
        get(f"cmd=missionassign&subtype=5&mission_id={_id}")
        PUSH_CONTENT.append(find(r"\[任务派遣中心\](.*?)<br />"))

    # 接受任务
    missions_dict = {
        "少女天团": "2",
        "闺蜜情深": "17",
        "男女搭配": "9",
        "鼓舞士气": "5",
        "仙人降临": "6",
        "雇佣军团": "11",
        "调整状态": "12",
        "防御工事": "10",
        "护送长老": "1",
        "坚持不懈": "4",
        "降妖除魔": "3",
        "深山隐士": "7",
        "抓捕小偷": "8",
        "小队巡逻": "13",
        "武艺切磋": "14",
        "哥俩好啊": "15",
        "协助村长": "16",
        "打扫房间": "18",
        "货物运送": "19",
        "消除虫害": "20",
        "帮助邻居": "21",
        "上山挑水": "22",
        "房屋维修": "23",
        "清理蟑螂": "24",
        "收割作物": "25",
        "炊烟袅袅": "26",
        "湖边垂钓": "27",
        "勤劳园丁": "29",
    }
    # 任务派遣中心
    get("cmd=missionassign&subtype=0")
    for _ in range(3):
        mission_id = findall(r'mission_id=(\d+)">接受')
        for _, _id in missions_dict.items():
            if _id in mission_id:
                # 快速委派
                get(f"cmd=missionassign&subtype=7&mission_id={_id}")
                # 开始任务
                get(f"cmd=missionassign&subtype=8&mission_id={_id}")
                if "任务数已达上限" in HTML:
                    break
        # 任务派遣中心
        get("cmd=missionassign&subtype=0")
        if "今日已领取了全部任务哦" in HTML:
            break
        elif HTML.count("查看") == 3:
            break
        elif "50斗豆" not in HTML:
            # 刷新任务
            get("cmd=missionassign&subtype=3")

    # 任务派遣中心
    get("cmd=missionassign&subtype=0")
    for _msg in findall(r"<br />(.*?)&nbsp;<a.*?查看"):
        PUSH_CONTENT.append(_msg)


def 武林盟主():
    """
    周三、五、日领取排行奖励和竞猜奖励
    周一、三、五分站赛报名yaml配置的赛场
    周二、四、六竞猜
    """
    if WEEK in [3, 5, 7]:
        # 武林盟主
        get("cmd=wlmz&op=view_index")
        if data := findall(r'section_id=(\d+)&amp;round_id=(\d+)">'):
            for s, r in data:
                get(f"cmd=wlmz&op=get_award&section_id={s}&round_id={r}")
                PUSH_CONTENT.append(find(r"<br /><br />(.*?)</p>"))
        else:
            print_info("没有可领取的排行奖励和竞猜奖励")
            PUSH_CONTENT.append("没有可领取的排行奖励和竞猜奖励")

    if WEEK in [1, 3, 5]:
        g_id = YAML["武林盟主"]
        get(f"cmd=wlmz&op=signup&ground_id={g_id}")
        if "总决赛周不允许报名" in HTML:
            PUSH_CONTENT.append(find(r"战报</a><br />(.*?)<br />"))
            return
        PUSH_CONTENT.append(find(r"赛场】<br />(.*?)<br />"))
    elif WEEK in [2, 4, 6]:
        for index in range(8):
            # 选择
            get(f"cmd=wlmz&op=guess_up&index={index}")
            find(r"规则</a><br />(.*?)<br />")
        # 确定竞猜选择
        get("cmd=wlmz&op=comfirm")
        PUSH_CONTENT.append(find(r"战报</a><br />(.*?)<br />"))


def 全民乱斗():
    """
    乱斗竞技任务列表领取、乱斗任务领取
    """
    n = True
    for t in [2, 3, 4]:
        get(f"cmd=luandou&op=0&acttype={t}")
        for _id in findall(r'.*?id=(\d+)">领取</a>'):
            n = False
            # 领取
            get(f"cmd=luandou&op=8&id={_id}")
            PUSH_CONTENT.append(find(r"斗】<br /><br />(.*?)<br />"))
    if n:
        print_info("没有可领取的")
        PUSH_CONTENT.append("没有可领取的")


def 侠士客栈():
    """
    每天领取奖励3次、客栈奇遇
    """
    # 侠士客栈
    get("cmd=warriorinn")
    if t := find(r"type=(\d+).*?领取奖励</a>"):
        for n in range(1, 4):
            # 领取奖励
            get(f"cmd=warriorinn&op=getlobbyreward&type={t}&num={n}")
            PUSH_CONTENT.append(find(r"侠士客栈<br />(.*?)<br />"))

    # 奇遇
    for p in findall(r"pos=(\d+)"):
        get(f"cmd=warriorinn&op=showAdventure&pos={p}")
        if "前来捣乱的" in HTML:
            # 前来捣乱的xx -> 与TA理论 -> 确认
            get(f"cmd=warriorinn&op=exceptadventure&pos={p}")
            if "战斗" in HTML:
                PUSH_CONTENT.append(find(r"侠士客栈<br />(.*?) ，"))
                continue
            PUSH_CONTENT.append(find(r"侠士客栈<br />(.*?)<br />"))
        else:
            # 黑市商人、老乞丐 -> 你去别人家问问吧、拯救世界的任务还是交给别人把 -> 确认
            get(f"cmd=warriorinn&op=rejectadventure&pos={p}")


def 江湖长梦():
    """
    每天挑战柒承的忙碌日常（yaml配置挑战次数）、兑换玄铁令*1
    """
    _number: int = YAML["江湖长梦"]

    # 兑换 玄铁令*1
    get("cmd=longdreamexchange&op=exchange&key_id=5&page=1")
    if "兑换成功" in HTML:
        PUSH_CONTENT.append(find(r"侠士碎片</a><br />(.*?)<br />"))
    else:
        # 剩余兑换材料或者积分不足
        # 该物品兑换次数已达上限
        PUSH_CONTENT.append(find())

    if _number == 0:
        print_info("你设置不挑战柒承的忙碌日常")
        PUSH_CONTENT.append("你设置不挑战柒承的忙碌日常")
        return

    for _ in range(_number):
        # 开启副本
        get("cmd=jianghudream&op=beginInstance&ins_id=1")
        if "帮助" in HTML:
            # 开启副本所需追忆香炉不足
            # 您还未编辑副本队伍，无法开启副本
            PUSH_CONTENT.append(find())
            break

        for _ in range(8):
            if "进入下一天" in HTML:
                # 进入下一天
                get("cmd=jianghudream&op=goNextDay")
            if msg1 := findall(r'event_id=(\d+)">战斗\(等级1\)'):
                # 战斗
                get(f"cmd=jianghudream&op=chooseEvent&event_id={msg1[0]}")
                # FIGHT!
                get("cmd=jianghudream&op=doPveFight")
                find(r"<p>(.*?)<br />")
                if "战败" in HTML:
                    break
            elif msg2 := findall(r'event_id=(\d+)">奇遇\(等级1\)'):
                # 奇遇
                get(f"cmd=jianghudream&op=chooseEvent&event_id={msg2[0]}")
                # 视而不见
                get("cmd=jianghudream&op=chooseAdventure&adventure_id=2")
                find(r"获得金币：\d+<br />(.*?)<br />")
            elif msg3 := findall(r'event_id=(\d+)">商店\(等级1\)'):
                # 商店
                get(f"cmd=jianghudream&op=chooseEvent&event_id={msg3[0]}")

        # 结束回忆
        get("cmd=jianghudream&op=endInstance")
        PUSH_CONTENT.append(find())


def 增强经脉():
    """
    每天传功至多12次
    """
    # 关闭传功符不足用斗豆代替
    get("cmd=intfmerid&sub=21&doudou=0")
    if "关闭" in HTML:
        # 关闭合成两次确认
        get("cmd=intfmerid&sub=19")

    for _ in range(12):
        # 增强经脉
        get("cmd=intfmerid&sub=1")
        _id = find(r'master_id=(\d+)">传功</a>', "任务-增强经脉")
        # 传功
        get(f"cmd=intfmerid&sub=2&master_id={_id}")
        find(r"</p>(.*?)<p>", "任务-增强经脉")
        if "传功符不足!" in HTML:
            return

        # 一键拾取
        get("cmd=intfmerid&sub=5")
        find(r"</p>(.*?)<p>", "任务-增强经脉")
        # 一键合成
        get("cmd=intfmerid&sub=10&op=4")
        find(r"</p>(.*?)<p>", "任务-增强经脉")


def 助阵():
    """
    无字天书、河洛图书提升3次
    """
    _data = {
        1: [0],
        2: [0, 1],
        3: [0, 1, 2],
        9: [0, 1, 2],
        4: [0, 1, 2, 3],
        5: [0, 1, 2, 3],
        6: [0, 1, 2, 3],
        7: [0, 1, 2, 3],
        8: [0, 1, 2, 3, 4],
        10: [0, 1, 2, 3],
        11: [0, 1, 2, 3],
        12: [0, 1, 2, 3],
        13: [0, 1, 2, 3],
        14: [0, 1, 2, 3],
        15: [0, 1, 2, 3],
        16: [0, 1, 2, 3],
        17: [0, 1, 2, 3],
        18: [0, 1, 2, 3, 4],
    }

    def get_id_index():
        for f_id, index_list in _data.items():
            for index in index_list:
                yield (f_id, index)

    n = 0
    for _id, _index in get_id_index():
        if n == 3:
            break
        for _ in range(3):
            # 提升
            get(f"cmd=formation&type=4&formationid={_id}&attrindex={_index}&times=1")
            if "助阵组合所需佣兵不满足条件，不能提升助阵属性经验" in HTML:
                find(r"<br /><br />(.*?)。", "任务-助阵")
                return
            elif "阅历不足" in HTML:
                find(r"<br /><br />(.*?)，", "任务-助阵")
                return

            find(name="任务-助阵")
            if "提升成功" in HTML:
                n += 1
            elif "经验值已经达到最大" in HTML:
                break
            elif "你还没有激活该属性" in HTML:
                return


def 查看好友资料():
    """
    查看好友第二页
    """
    # 武林 》设置 》乐斗助手
    get("cmd=view&type=6")
    if "开启查看好友信息和收徒" in HTML:
        #  开启查看好友信息和收徒
        get("cmd=set&type=1")
    # 查看好友第2页
    get(f"cmd=friendlist&page=2")
    for uin in findall(r"\d+：.*?B_UID=(\d+).*?级"):
        get(f"cmd=totalinfo&B_UID={uin}")


def 徽章进阶():
    """
    勤劳徽章  1
    好友徽章  2
    等级徽章  3
    长者徽章  4
    时光徽章  5
    常胜徽章  6
    财富徽章  7
    达人徽章  8
    武林徽章  9
    分享徽章  10
    金秋徽章  11
    武器徽章  12
    金秋富豪  13
    佣兵徽章  14
    斗神徽章  15
    圣诞徽章  16
    春节徽章  17
    春节富豪  18
    技能徽章  19
    一掷千金  20
    劳动徽章  21
    周年富豪  22
    国旗徽章  23
    七周年徽章  24
    八周年徽章  25
    九周年徽章  26
    魅力徽章  27
    威望徽章  28
    十周年徽章  29
    十一周年徽章  30
    仙武徽章  31
    荣耀徽章  32
    十二周年徽章  33
    """
    for _id in range(1, 34):
        get(f"cmd=achievement&op=upgradelevel&achievement_id={_id}&times=1")
        find(r";<br />(.*?)<br />", "任务-徽章进阶")
        if "进阶失败" in HTML:
            break
        elif "进阶成功" in HTML:
            break
        elif "物品不足" in HTML:
            break


def 兵法研习():
    """
    兵法      消耗     id       功能
    金兰之泽  孙子兵法  2544     增加生命
    雷霆一击  孙子兵法  2570     增加伤害
    残暴攻势  武穆遗书  21001    增加暴击几率
    不屈意志  武穆遗书  21032    降低受到暴击几率
    """
    for _id in [21001, 2570, 21032, 2544]:
        get(f"cmd=brofight&subtype=12&op=practice&baseid={_id}")
        find(r"武穆遗书：\d+个<br />(.*?)<br />", "任务-兵法研习")
        if "研习成功" in HTML:
            break


def 挑战陌生人():
    """
    斗友乐斗四次
    """
    # 斗友
    get("cmd=friendlist&type=1")
    uin = findall(r"：.*?级.*?B_UID=(\d+).*?乐斗</a>")
    if not uin:
        print_info("未找到斗友")
        return

    for u in uin[:4]:
        # 乐斗
        get(f"cmd=fight&B_UID={u}&page=1&type=9")
        find(r"删</a><br />(.*?)！", "任务-挑战陌生人")


def 任务():
    """
    增强经脉、助阵每天必做
    """
    增强经脉()
    助阵()

    # 日常任务
    missions = get("cmd=task&sub=1")
    if "查看好友资料" in missions:
        查看好友资料()
    if "徽章进阶" in missions:
        徽章进阶()
    if "兵法研习" in missions:
        兵法研习()
    if "挑战陌生人" in missions:
        挑战陌生人()

    # 一键完成任务
    get("cmd=task&sub=7")
    for k, v in findall(r'id=\d+">(.*?)</a>.*?>(.*?)</a>'):
        PUSH_CONTENT.append(f"{k} {v}")


def 我的帮派():
    """
    每天供奉5次、帮派任务至多领取奖励3次
    周日领取奖励、报名帮派战争、激活祝福
    """
    # 我的帮派
    get("cmd=factionop&subtype=3&facid=0")
    if "你的职位" not in HTML:
        print_info("您还没有加入帮派")
        PUSH_CONTENT.append("您还没有加入帮派")
        return

    yaml: list = YAML["我的帮派"]
    for _id in yaml:
        for _ in range(5):
            # 供奉
            get(f"cmd=oblation&id={_id}&page=1")
            if "供奉成功" in HTML:
                PUSH_CONTENT.append(find())
                continue
            find(r"】</p><p>(.*?)<br />")
            break
        if "每天最多供奉5次" in HTML:
            break

    # 帮派任务
    faction_missions = get("cmd=factiontask&sub=1")
    missions = {
        "帮战冠军": "cmd=facwar&sub=4",
        "查看帮战": "cmd=facwar&sub=4",
        "查看帮贡": "cmd=factionhr&subtype=14",
        "查看祭坛": "cmd=altar",
        "查看踢馆": "cmd=facchallenge&subtype=0",
        "查看要闻": "cmd=factionop&subtype=8&pageno=1&type=2",
        # '加速贡献': 'cmd=use&id=3038&store_type=1&page=1',
        "粮草掠夺": "cmd=forage_war",
    }
    for name, url in missions.items():
        if name in faction_missions:
            print_info(name)
            get(url)
    if "帮派修炼" in faction_missions:
        n = 0
        for _id in [2727, 2758, 2505, 2536, 2437, 2442, 2377, 2399, 2429]:
            for _ in range(4):
                # 修炼
                get(f"cmd=factiontrain&type=2&id={_id}&num=1&i_p_w=num%7C")
                find(r"规则说明</a><br />(.*?)<br />")
                if "技能经验增加" in HTML:
                    n += 1
                    continue
                # 帮贡不足
                # 你今天获得技能升级经验已达到最大！
                # 你需要提升帮派等级来让你进行下一步的修炼
                break
            if n == 4:
                break
    # 帮派任务
    get("cmd=factiontask&sub=1")
    for _id in findall(r'id=(\d+)">领取奖励</a>'):
        # 领取奖励
        get(f"cmd=factiontask&sub=3&id={_id}")
        PUSH_CONTENT.append(find(r"日常任务</a><br />(.*?)<br />"))

    if WEEK != 7:
        return

    # 周日 领取奖励 》报名帮派战争 》激活祝福
    for sub in [4, 9, 6]:
        get(f"cmd=facwar&sub={sub}")
        PUSH_CONTENT.append(find(r"</p>(.*?)<br /><a.*?查看上届"))


def 帮派祭坛():
    """
    每天转动轮盘至多30次、领取通关奖励
    """
    # 帮派祭坛
    get("cmd=altar")
    for _ in range(30):
        if "【祭坛轮盘】" in HTML:
            # 转动轮盘
            get("cmd=altar&op=spinwheel")
            if "【祭坛轮盘】" in HTML:
                PUSH_CONTENT.append(find())
            if "转转券不足" in HTML:
                break
        if "【随机分配】" in HTML:
            for op, _id in findall(r"op=(.*?)&amp;id=(\d+)"):
                # 选择
                get(f"cmd=altar&op={op}&id={_id}")
                if "选择路线" in HTML:
                    # 选择路线
                    get(f"cmd=altar&op=dosteal&id={_id}")
                if "【随机分配】" in HTML:
                    # 该帮派已解散，无法操作！
                    # 系统繁忙
                    find(r"<br /><br />(.*?)<br />")
                    continue
                if "【祭坛轮盘】" in HTML:
                    PUSH_CONTENT.append(find())
                    break
        if "领取奖励" in HTML:
            get("cmd=altar&op=drawreward")
            PUSH_CONTENT.append(find())


def 飞升大作战():
    """
    每天兑换玄铁令*1、优先报名单排模式，玄铁令不足或者休赛期时选择匹配模式
    周四领取赛季结束奖励
    """
    # 兑换 玄铁令*1
    get("cmd=ascendheaven&op=exchange&id=2&times=1")
    PUSH_CONTENT.append(find())

    # 报名单排模式
    get("cmd=ascendheaven&op=signup&type=1")
    PUSH_CONTENT.append(find())
    if "时势造英雄" not in HTML:
        # 当前为休赛期，不在报名时间、还没有入场券玄铁令、你已经报名参赛
        # 报名匹配模式
        get("cmd=ascendheaven&op=signup&type=2")
        PUSH_CONTENT.append(find())

    if (WEEK != 4) or ("赛季结算中" not in HTML):
        return

    # 境界修为
    get("cmd=ascendheaven&op=showrealm")
    for s in findall(r"season=(\d+)"):
        # 领取奖励
        get(f"cmd=ascendheaven&op=getrealmgift&season={s}")
        PUSH_CONTENT.append(find())


def 深渊之潮():
    """
    每天帮派巡礼领取巡游赠礼、深渊秘境至多挑战3次，yaml配置关卡
    """
    _id: int = YAML["深渊之潮"]

    # 领取巡游赠礼
    get("cmd=abysstide&op=getfactiongift")
    PUSH_CONTENT.append(find())

    for _ in range(5):
        get(f"cmd=abysstide&op=enterabyss&id={_id}")
        if "开始挑战" not in HTML:
            # 暂无可用挑战次数
            # 该副本需要顺序通关解锁
            PUSH_CONTENT.append(find())
            break

        for _ in range(5):
            # 开始挑战
            get("cmd=abysstide&op=beginfight")
            find()
            if "憾负于" in HTML:
                break

        # 退出副本
        get("cmd=abysstide&op=endabyss")
        PUSH_CONTENT.append(find())


def 每日奖励():
    """
    每天领取4次
    """
    for key in ["login", "meridian", "daren", "wuzitianshu"]:
        # 每日奖励
        get(f"cmd=dailygift&op=draw&key={key}")
        PUSH_CONTENT.append(find())


def 领取徒弟经验():
    """
    每天一次
    """
    # 领取徒弟经验
    get("cmd=exp")
    PUSH_CONTENT.append(find(r"每日奖励</a><br />(.*?)<br />"))


def 今日活跃度():
    """
    每天领取活跃度礼包、帮派总活跃礼包
    """
    # 今日活跃度
    get("cmd=liveness")
    PUSH_CONTENT.append(find(r"【(.*?)】"))
    if "帮派总活跃" in HTML:
        PUSH_CONTENT.append(find(r"礼包</a><br />(.*?)<"))

    # 领取今日活跃度礼包
    for giftbag_id in range(1, 5):
        get(f"cmd=liveness_getgiftbag&giftbagid={giftbag_id}&action=1")
        PUSH_CONTENT.append(find(r"】<br />(.*?)<p>"))

    # 领取帮派总活跃奖励
    get("cmd=factionop&subtype=18")
    if "创建帮派" in HTML:
        PUSH_CONTENT.append(find(r"帮派</a><br />(.*?)<br />"))
    else:
        PUSH_CONTENT.append(find())


def 仙武修真():
    """
    每天领取3次任务、寻访长留山挑战至多5次
    """
    for task_id in range(1, 4):
        # 领取
        get(f"cmd=immortals&op=getreward&taskid={task_id}")
        PUSH_CONTENT.append(find(r"帮助</a><br />(.*?)<br />"))

    for _ in range(5):
        # 寻访 长留山
        get("cmd=immortals&op=visitimmortals&mountainId=1")
        _msg = find(r"帮助</a><br />(.*?)<br />")
        if "你的今日寻访挑战次数已用光" in HTML:
            PUSH_CONTENT.append(_msg)
            break
        # 挑战
        get("cmd=immortals&op=fightimmortals")
        PUSH_CONTENT.append(find(r"帮助</a><br />(.*?)<a"))


def 大侠回归三重好礼():
    """
    周四领取奖励
    """
    # 大侠回归三重好礼
    get("cmd=newAct&subtype=173&op=1")
    if _data := findall(r"subtype=(\d+).*?taskid=(\d+)"):
        for s, t in _data:
            # 领取
            get(f"cmd=newAct&subtype={s}&op=2&taskid={t}")
            PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))
    else:
        print_info("没有可领取的奖励")
        PUSH_CONTENT.append("没有可领取的奖励")


def 乐斗黄历():
    """
    每天占卜一次
    """
    # 乐斗黄历
    get("cmd=calender&op=0")
    PUSH_CONTENT.append(find(r"今日任务：(.*?)<br />"))
    # 领取
    get("cmd=calender&op=2")
    PUSH_CONTENT.append(find(r"<br /><br />(.*?)<br />"))
    if "任务未完成" in HTML:
        return
    # 占卜
    get("cmd=calender&op=4")
    PUSH_CONTENT.append(find(r"<br /><br />(.*?)<br />"))


def 器魂附魔():
    """
    附魔任务领取（50、80、115）
    """
    # 器魂附魔
    get("cmd=enchant")
    for task_id in range(1, 4):
        # 领取
        get(f"cmd=enchant&op=gettaskreward&task_id={task_id}")
        PUSH_CONTENT.append(find())


def 侠客岛():
    """
    侠客行接受任务、领取奖励至多3次，刷新至多4次（即免费次数为0时不再刷新）
    第一轮及第二轮均执行
    """
    count: str = "4"
    mission_success: bool = False
    # 侠客行
    get("cmd=knight_island&op=viewmissionindex")
    for _ in range(4):
        view_mission_detail_pos = findall(r"viewmissiondetail&amp;pos=(\d+)")
        if not view_mission_detail_pos:
            break
        for p in view_mission_detail_pos:
            # 接受
            get(f"cmd=knight_island&op=viewmissiondetail&pos={p}")
            mission_name = find(r"侠客行<br /><br />(.*?)（", "侠客行-任务名称")
            # 快速委派
            get(f"cmd=knight_island&op=autoassign&pos={p}")
            find(r"）<br />(.*?)<br />", f"侠客行-{mission_name}")
            if "快速委派成功" in HTML:
                mission_success = True
                # 开始任务
                get(f"cmd=knight_island&op=begin&pos={p}")
                _html = find(r"斗豆）<br />(.*?)<br />", f"侠客行-{mission_name}")
                PUSH_CONTENT.append(f"{mission_name}：{_html}")
            elif "符合条件侠士数量不足" in HTML:
                # 侠客行
                get("cmd=knight_island&op=viewmissionindex")
                # 免费刷新次数
                count = find(r"剩余：(\d+)次", "侠客行-免费刷新次数")
                if count != "0":
                    # 刷新
                    get(f"cmd=knight_island&op=refreshmission&pos={p}")
                    find(r"斗豆）<br />(.*?)<br />", f"侠客行-{mission_name}")
                else:
                    print_info("没有免费次数，取消刷新", f"侠客行-{mission_name}")

        if count == "0":
            break

    # 领取任务奖励
    for p2 in findall(r"getmissionreward&amp;pos=(\d+)"):
        mission_success = True
        # 领取
        get(f"cmd=knight_island&op=getmissionreward&pos={p2}")
        PUSH_CONTENT.append(find(r"斗豆）<br />(.*?)<br />"))

    if not mission_success:
        PUSH_CONTENT.append(
            "没有可接受或可领取的任务（符合条件侠士数量不足、执行中、已完成）"
        )


def 时空遗迹():
    """
    八卦迷阵根据首通提示通关并领取奖励
    """
    _data = {
        "离": 1,
        "坤": 2,
        "兑": 3,
        "乾": 4,
        "坎": 5,
        "艮": 6,
        "震": 7,
        "巽": 8,
    }
    # 八卦迷阵
    get("cmd=spacerelic&op=goosip")
    result = find(r"([乾坤震巽坎离艮兑]{4})")
    if not result:
        print_info("首通没有八卦提示")
        PUSH_CONTENT.append("首通没有八卦提示")
        return

    for i in result:
        # 点击八卦
        get(f"cmd=spacerelic&op=goosip&id={_data[i]}")
        PUSH_CONTENT.append(find(r"分钟<br /><br />(.*?)<br />"))
        if "恭喜您" not in HTML:
            # 你被迷阵xx击败，停留在了本层
            # 耐力不足，无法闯关
            # 你被此门上附着的阵法传送回了第一层
            # 请遵循迷阵规则进行闯关
            break
        # 恭喜您进入到下一层
        # 恭喜您已通关迷阵，快去领取奖励吧

    if "恭喜您已通关迷阵" in HTML:
        # 领取通关奖励
        get("cmd=spacerelic&op=goosipgift")
        PUSH_CONTENT.append(find(r"分钟<br /><br />(.*?)<br />"))


def 兵法():
    """
    周四随机助威
    周六领奖、领取斗币
    """
    if WEEK == 4:
        # 助威
        get("cmd=brofight&subtype=13")
        if teamid := findall(r".*?teamid=(\d+).*?助威</a>"):
            t = random.choice(teamid)
            # 确定
            get(f"cmd=brofight&subtype=13&teamid={t}&type=5&op=cheer")
            PUSH_CONTENT.append(find(r"领奖</a><br />(.*?)<br />"))

    if WEEK != 6:
        return

    # 兵法 -> 助威 -> 领奖
    get("cmd=brofight&subtype=13&op=draw")
    PUSH_CONTENT.append(find(r"领奖</a><br />(.*?)<br />"))

    for t in range(1, 6):
        get(f"cmd=brofight&subtype=10&type={t}")
        for n, u in findall(r"50000.*?(\d+).*?champion_uin=(\d+)"):
            if n == "0":
                continue
            # 领斗币
            get(f"cmd=brofight&subtype=10&op=draw&champion_uin={u}&type={t}")
            PUSH_CONTENT.append(find(r"排行</a><br />(.*?)<br />"))
            return


def 背包():
    """
    背包物品使用，yaml配置选择物品
    """
    global HTML
    yaml: list = YAML["背包"]
    data = []

    # 背包
    get("cmd=store&store_type=0")
    page = find(r"第1/(\d+)")
    if page is None:
        print_info("背包未找到页码")
        PUSH_CONTENT.append("背包未找到页码")
        return

    for p in range(1, int(page) + 1):
        print_info(f"查找第 {p} 页id")
        # 下页
        get(f"cmd=store&store_type=0&page={p}")
        if "使用规则" in HTML:
            find(r"】</p><p>(.*?)<br />")
            continue
        _, HTML = HTML.split("清理")
        HTML, _ = HTML.split("商店")
        for _m in yaml:
            # 查找物品id
            data += findall(f"{_m}.*?</a>数量：.*?id=(\d+)")

    id_number = []
    for _id in data:
        # 物品详情
        get(f"cmd=owngoods&id={_id}")
        if "很抱歉" in HTML:
            find(r"】</p><p>(.*?)<br />", f"背包-{_id}-不存在")
        else:
            number = find(r"数量：(\d+)", f"背包-{_id}-数量")
            id_number.append((str(_id), int(number)))

    for _id, number in set(id_number):
        if _id in ["3023", "3024", "3025"]:
            # xx洗刷刷，3103生命洗刷刷除外
            print_info("只能生命洗刷刷，其它洗刷刷不支持")
            PUSH_CONTENT.append("只能生命洗刷刷，其它洗刷刷不支持")
            continue
        for _ in range(number):
            # 使用
            get(f"cmd=use&id={_id}")
            if "使用规则" in HTML:
                # 该物品不能被使用
                # 该物品今天已经不能再使用了
                find(r"】</p><p>(.*?)<br />", f"背包-{_id}-使用")
                break
            # 您使用了
            # 你打开
            PUSH_CONTENT.append(find())


def 镶嵌():
    """
    周四镶嵌魂珠升级（碎 -> 1 -> 2 -> 3 -> 4）
    """

    def get_p():
        for p_1 in range(4001, 4062, 10):
            # 魂珠1级
            yield p_1
        for p_2 in range(4002, 4063, 10):
            # 魂珠2级
            yield p_2
        for p_3 in range(4003, 4064, 10):
            # 魂珠3级
            yield p_3

    for e in range(2000, 2007):
        for _ in range(50):
            # 魂珠碎片 -> 1
            get(f"cmd=upgradepearl&type=6&exchangetype={e}")
            _msg = find(r"魂珠升级</p><p>(.*?)</p>")
            if "不能合成该物品" in HTML:
                # 抱歉，您的xx魂珠碎片不足，不能合成该物品！
                break
            PUSH_CONTENT.append(_msg)

    for p in get_p():
        for _ in range(50):
            # 1 -> 2 -> 3 -> 4
            get(f"cmd=upgradepearl&type=3&pearl_id={p}")
            _msg = find(r"魂珠升级</p><p>(.*?)<")
            if "您拥有的魂珠数量不够" in HTML:
                break
            PUSH_CONTENT.append(_msg)


def 神匠坊():
    """
    周四普通合成、符石分解（默认仅I类）、符石打造
    """
    yaml: list[int] = YAML["神匠坊"]
    data_1 = []
    data_2 = []

    # 背包
    for p in range(1, 20):
        print_info(f"背包第 {p} 页")
        # 下一页
        get(f"cmd=weapongod&sub=12&stone_type=0&quality=0&page={p}")
        data_1 += findall(r"拥有：(\d+)/(\d+).*?stone_id=(\d+)")
        if "下一页" not in HTML:
            break
    for possess, number, _id in data_1:
        if int(possess) < int(number):
            # 符石碎片不足
            continue
        count = int(int(possess) / int(number))
        for _ in range(count):
            # 普通合成
            get(f"cmd=weapongod&sub=13&stone_id={_id}")
            PUSH_CONTENT.append(find(r"背包<br /></p>(.*?)!"))

    # 符石分解
    for p in range(1, 10):
        print_info(f"符石分解第 {p} 页")
        # 下一页
        get(f"cmd=weapongod&sub=9&stone_type=0&page={p}")
        data_2 += findall(r"数量:(\d+).*?stone_id=(\d+)")
        if "下一页" not in HTML:
            break
    for num, _id in data_2:
        if int(_id) not in yaml:
            continue
        # 分解
        get(f"cmd=weapongod&sub=11&stone_id={_id}&num={num}&i_p_w=num%7C")
        PUSH_CONTENT.append(find(r"背包</a><br /></p>(.*?)<"))

    # 符石打造
    # 符石
    get("cmd=weapongod&sub=7")
    if data_3 := find(r"符石水晶：(\d+)"):
        number = int(data_3)
        ten = int(number / 60)
        one = int((number - (ten * 60)) / 6)
        for _ in range(ten):
            # 打造十次
            get("cmd=weapongod&sub=8&produce_type=1&times=10")
            PUSH_CONTENT.append(find(r"背包</a><br /></p>(.*?)<"))
        for _ in range(one):
            # 打造一次
            get("cmd=weapongod&sub=8&produce_type=1&times=1")
            PUSH_CONTENT.append(find(r"背包</a><br /></p>(.*?)<"))


def 每日宝箱():
    """
    每月20号打开所有的铜质、银质、金质宝箱
    """
    # 每日宝箱
    get("cmd=dailychest")
    while t := find(r'type=(\d+)">打开'):
        # 打开
        get(f"cmd=dailychest&op=open&type={t}")
        PUSH_CONTENT.append(find(r"说明</a><br />(.*?)<"))
        if "今日开宝箱次数已达上限" in HTML:
            break


def 商店():
    """
    每天查询商店积分，比如矿石商店、粮票商店、功勋商店等积分
    """
    urls = [
        "cmd=longdreamexchange",  # 江湖长梦
        "cmd=wlmz&op=view_exchange",  # 武林盟主
        "cmd=arena&op=queryexchange",  # 竞技场
        "cmd=ascendheaven&op=viewshop",  # 飞升大作战
        "cmd=abysstide&op=viewabyssshop",  # 深渊之潮
        "cmd=exchange&subtype=10&costtype=1",  # 踢馆
        "cmd=exchange&subtype=10&costtype=2",  # 掠夺
        "cmd=exchange&subtype=10&costtype=3",  # 矿洞
        "cmd=exchange&subtype=10&costtype=4",  # 镖行天下
        "cmd=exchange&subtype=10&costtype=9",  # 幻境
        "cmd=exchange&subtype=10&costtype=10",  # 群雄逐鹿
        "cmd=exchange&subtype=10&costtype=11",  # 门派邀请赛
        "cmd=exchange&subtype=10&costtype=12",  # 帮派祭坛
        "cmd=exchange&subtype=10&costtype=13",  # 会武
        "cmd=exchange&subtype=10&costtype=14",  # 问鼎天下
    ]
    for url in urls:
        get(url)
        PUSH_CONTENT.append(find())


def 猜单双():
    """
    随机单数、双数
    """
    # 猜单双
    get("cmd=oddeven")
    for _ in range(5):
        value = findall(r'value=(\d+)">.*?数')
        if not value:
            print_info("猜单双已经做过了")
            PUSH_CONTENT.append("猜单双已经做过了")
            break

        value = random.choice(value)
        # 单数1 双数2
        get(f"cmd=oddeven&value={value}")
        PUSH_CONTENT.append(find())


def 煮元宵():
    """
    成熟度>=96时赶紧出锅
    """
    # 煮元宵
    get("cmd=yuanxiao2014")
    for _ in range(4):
        # 开始烹饪
        get("cmd=yuanxiao2014&op=1")
        if "领取烹饪次数" in HTML:
            print_info("没有烹饪次数了")
            PUSH_CONTENT.append("没有烹饪次数了")
            break

        for _ in range(20):
            maturity = find(r"当前元宵成熟度：(\d+)")
            if int(maturity) < 96:
                # 继续加柴
                get("cmd=yuanxiao2014&op=2")
                continue
            # 赶紧出锅
            get("cmd=yuanxiao2014&op=3")
            PUSH_CONTENT.append(find(r"活动规则</a><br /><br />(.*?)。"))
            break


def 万圣节():
    """
    点亮南瓜灯
    活动截止日的前一天优先兑换礼包B，最后兑换礼包A
    """
    # 点亮南瓜灯
    get("cmd=hallowmas&gb_id=1")
    while True:
        if cushaw_id := findall(r"cushaw_id=(\d+)"):
            c_id = random.choice(cushaw_id)
            # 南瓜
            get(f"cmd=hallowmas&gb_id=4&cushaw_id={c_id}")
            PUSH_CONTENT.append(find())
        # 恭喜您获得10体力和南瓜灯一个！
        # 恭喜您获得20体力和南瓜灯一个！南瓜灯已刷新
        # 请领取今日的活跃度礼包来获得蜡烛吧！
        if "请领取今日的活跃度礼包来获得蜡烛吧" in HTML:
            break

    # 兑换奖励
    get("cmd=hallowmas&gb_id=0")
    day: str = find(r"至\d+月(\d+)日")
    if DAY != (int(day) - 1):
        return

    num: str = find(r"南瓜灯：(\d+)个")
    b = int(num) / 40
    a = (int(num) - int(b) * 40) / 20
    for _ in range(int(a)):
        # 兑换礼包B 消耗40个南瓜灯
        get("cmd=hallowmas&gb_id=6")
        PUSH_CONTENT.append(find())
    for _ in range(int(a)):
        # 兑换礼包A 消耗20个南瓜灯
        get("cmd=hallowmas&gb_id=5")
        PUSH_CONTENT.append(find())


def 元宵节():
    """
    周四领取、领取月桂兔
    """
    # 领取
    get("cmd=newAct&subtype=101&op=1")
    PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))
    # 领取月桂兔
    get("cmd=newAct&subtype=101&op=2&index=0")
    PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))


def 神魔转盘():
    """
    幸运抽奖免费抽奖一次
    """
    # 神魔转盘
    get("cmd=newAct&subtype=88&op=0")
    if "免费抽奖一次" not in HTML:
        print_info("没有免费抽奖次数")
        PUSH_CONTENT.append("没有免费抽奖次数")
        return

    get("cmd=newAct&subtype=88&op=1")
    PUSH_CONTENT.append(find())


def 乐斗驿站():
    """
    免费领取淬火结晶*1
    """
    get("cmd=newAct&subtype=167&op=2")
    PUSH_CONTENT.append(find())


def 浩劫宝箱():
    """
    领取一次
    """
    get("cmd=newAct&subtype=152")
    PUSH_CONTENT.append(find(r"浩劫宝箱<br />(.*?)<br />"))


def 幸运转盘():
    """
    转动轮盘一次
    """
    get("cmd=newAct&subtype=57&op=roll")
    PUSH_CONTENT.append(find(r"0<br /><br />(.*?)<br />"))


def 冰雪企缘():
    """
    至多领取两次
    """
    # 冰雪企缘
    get("cmd=newAct&subtype=158&op=0")
    gift = findall(r"gift_type=(\d+)")
    if not gift:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")
        return

    for g in gift:
        # 领取
        get(f"cmd=newAct&subtype=158&op=2&gift_type={g}")
        PUSH_CONTENT.append(find())


def 甜蜜夫妻():
    """
    夫妻甜蜜好礼      至多领取3次
    单身鹅鼓励好礼    至多领取3次
    """
    # 甜蜜夫妻
    get("cmd=newAct&subtype=129")
    flag = findall(r"flag=(\d+)")
    if not flag:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")
        return

    for f in flag:
        # 领取
        get(f"cmd=newAct&subtype=129&op=1&flag={f}")
        PUSH_CONTENT.append(find(r"】</p>(.*?)<br />"))


def 乐斗菜单():
    """
    点单
    """
    # 乐斗菜单
    get("cmd=menuact")
    if gift := find(r"套餐.*?gift=(\d+).*?点单</a>"):
        # 点单
        get(f"cmd=menuact&sub=1&gift={gift}")
        PUSH_CONTENT.append(find(r"哦！<br /></p>(.*?)<br />"))
    else:
        print_info("没有可点单")
        PUSH_CONTENT.append("没有可点单")


def 客栈同福():
    """
    献酒三次
    """
    for _ in range(3):
        # 献酒
        get("cmd=newAct&subtype=155")
        PUSH_CONTENT.append(find(r"】<br /><p>(.*?)<br />"))
        if "黄酒不足" in HTML:
            break


def 周周礼包():
    """
    领取一次
    """
    # 周周礼包
    get("cmd=weekgiftbag&sub=0")
    if _id := find(r';id=(\d+)">领取'):
        # 领取
        get(f"cmd=weekgiftbag&sub=1&id={_id}")
        PUSH_CONTENT.append(find())
    else:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")


def 登录有礼():
    """
    领取登录奖励一次
    """
    # 登录有礼
    get("cmd=newAct&subtype=56")
    index = find(r"gift_index=(\d+)")
    if index is None:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")
        return

    # 领取
    get(f"cmd=newAct&subtype=56&op=draw&gift_type=1&gift_index={index}")
    PUSH_CONTENT.append(find())


def 活跃礼包():
    """
    领取两次
    """
    for p in ["1", "2"]:
        get(f"cmd=newAct&subtype=94&op={p}")
        PUSH_CONTENT.append(find(r"】.*?<br />(.*?)<br />"))


def 上香活动():
    """
    领取檀木香、龙涎香各两次
    """
    for _ in range(2):
        # 檀木香
        get("cmd=newAct&subtype=142&op=1&id=1")
        PUSH_CONTENT.append(find())
        # 龙涎香
        get("cmd=newAct&subtype=142&op=1&id=2")
        PUSH_CONTENT.append(find())


def 徽章战令():
    """
    领取每日礼包
    """
    # 每日礼包
    get("cmd=badge&op=1")
    PUSH_CONTENT.append(find())


def 生肖福卡():
    """
    集卡：
        好友赠卡：领取好友赠卡
        分享：向好友分享一次福卡（选择数量最多的，如果数量最大值为1则不分享）
        领取：领取
    兑奖：
        周四合成周年福卡、分斗豆
    抽奖：
        周四抽奖：
            已合成周年福卡则抽奖
            已过合卡时间则继续抽奖
    """
    # 好友赠卡
    get("cmd=newAct&subtype=174&op=4")
    for name, qq, card_id in findall(r"送您(.*?)\*.*?oppuin=(\d+).*?id=(\d+)"):
        # 领取
        get(f"cmd=newAct&subtype=174&op=6&oppuin={qq}&card_id={card_id}")
        find(name=f"生肖福卡-{name}")
        PUSH_CONTENT.append(f"好友赠卡：{name}")

    # 分享福卡
    # 生肖福卡
    get("cmd=newAct&subtype=174")
    if qq := YAML["生肖福卡"]:
        pattern = "[子丑寅卯辰巳午未申酉戌亥][鼠牛虎兔龙蛇马羊猴鸡狗猪]"
        data = findall(f"({pattern})\s+(\d+).*?id=(\d+)")
        name, max_number, card_id = max(data, key=lambda x: int(x[1]))
        if int(max_number) >= 2:
            # 分享福卡
            get(f"cmd=newAct&subtype=174&op=5&oppuin={qq}&card_id={card_id}&confirm=1")
            PUSH_CONTENT.append(
                find(r"~<br /><br />(.*?)<br />", f"生肖福卡-{name}福卡")
            )
        else:
            print_info("你的福卡数量不足2", "生肖福卡-取消分享")
            PUSH_CONTENT.append("你的福卡数量不足2")

    # 领取
    # 生肖福卡
    get("cmd=newAct&subtype=174")
    for task_id in findall(r"task_id=(\d+)"):
        # 领取
        get(f"cmd=newAct&subtype=174&op=7&task_id={task_id}")
        PUSH_CONTENT.append(find(r"~<br /><br />(.*?)<br />", f"生肖福卡-集卡"))

    if WEEK != 4:
        return

    # 兑奖及抽奖
    # 合成周年福卡
    get("cmd=newAct&subtype=174&op=8")
    PUSH_CONTENT.append(find(r"。<br /><br />(.*?)<br />", "生肖福卡-兑奖"))
    # 分斗豆
    get("cmd=newAct&subtype=174&op=9")
    PUSH_CONTENT.append(find(r"。<br /><br />(.*?)<br />", "生肖福卡-兑奖"))

    # 合卡结束日期
    date = findall(r"合卡时间：.*?至(\d+)月(\d+)日")
    month, day = date[0]

    # 抽奖
    get("cmd=newAct&subtype=174&op=2")
    for _id, data in findall(r"id=(\d+).*?<br />(.*?)<br />"):
        numbers = re.findall(r"\d+", data)
        min_number = min(numbers, key=lambda x: int(x))
        for _ in range(int(min_number)):
            # 春/夏/秋/冬宵抽奖
            get(f"cmd=newAct&subtype=174&op=10&id={_id}&confirm=1")
            if "您还未合成周年福卡" in HTML:
                if (MONTH == int(month)) and (DAY > int(day)):
                    # 合卡时间已结束
                    # 继续抽奖
                    get(f"cmd=newAct&subtype=174&op=10&id={_id}")
                else:
                    print_info("合卡期间需先合成周年福卡才能抽奖", "生肖福卡-抽奖")
                    PUSH_CONTENT.append("合卡期间需先合成周年福卡才能抽奖")
                    return
            PUSH_CONTENT.append(
                find(r"幸运抽奖<br /><br />(.*?)<br />", "生肖福卡-抽奖")
            )


def 长安盛会():
    """
    盛会豪礼：点击领取  id  1
    签到宝箱：点击领取  id  2
    全民挑战：点击参与  id  3，4，5
    """
    s_id = YAML["长安盛会"]
    # 选择黄金卷轴类别
    get(f"cmd=newAct&subtype=118&op=2&select_id={s_id}")

    for _id in findall(r"op=1&amp;id=(\d+)"):
        if _id in ["1", "2"]:
            # 点击领取
            get(f"cmd=newAct&subtype=118&op=1&id={_id}")
            PUSH_CONTENT.append(find(name="长安盛会-点击领取"))
        else:
            turn_count = find(r"剩余转动次数：(\d+)", "长安盛会-转动次数")
            for _ in range(int(turn_count)):
                # 点击参与
                get(f"cmd=newAct&subtype=118&op=1&id={_id}")
                PUSH_CONTENT.append(find(name="长安盛会-点击参与"))


def 深渊秘宝():
    """
    三魂秘宝、七魄秘宝各免费抽奖一次
    """
    # 深渊秘宝
    get("cmd=newAct&subtype=175")
    t_list = findall(r'type=(\d+)&amp;times=1">免费抽奖')
    if not t_list:
        print_info("没有免费抽奖次数")
        PUSH_CONTENT.append("没有免费抽奖次数")
        return

    for t in t_list:
        get(f"cmd=newAct&subtype=175&op=1&type={t}&times=1")
        PUSH_CONTENT.append(find())


def 中秋礼盒():
    """
    领取
    """
    # 中秋礼盒
    get("cmd=midautumngiftbag&sub=0")
    ids = findall(r"amp;id=(\d+)")
    if not ids:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")
        return

    for _id in ids:
        # 领取
        get(f"cmd=midautumngiftbag&sub=1&id={_id}")
        PUSH_CONTENT.append(find())
        if "已领取完该系列任务所有奖励" in HTML:
            continue


def 双节签到():
    """
    领取签到奖励
    活动截止日的前一天领取奖励金
    """
    # 双节签到
    get("cmd=newAct&subtype=144")
    day: str = find(r"至\d+月(\d+)日")
    if "op=1" in HTML:
        # 领取
        get("cmd=newAct&subtype=144&op=1")
        PUSH_CONTENT.append(find())
    if DAY == (int(day) - 1):
        # 奖励金
        get("cmd=newAct&subtype=144&op=3")
        PUSH_CONTENT.append(find())


def 乐斗游记():
    """
    每天领取积分
    每周四一键领取、兑换十次、兑换一次
    """
    # 乐斗游记
    get("cmd=newAct&subtype=176")

    # 今日游记任务
    for _id in findall(r"task_id=(\d+)"):
        # 领取
        get(f"cmd=newAct&subtype=176&op=1&task_id={_id}")
        PUSH_CONTENT.append(find(r"积分。<br /><br />(.*?)<br />"))

    if WEEK != 4:
        return

    # 一键领取
    get("cmd=newAct&subtype=176&op=5")
    PUSH_CONTENT.append(find(r"积分。<br /><br />(.*?)<br />"))
    PUSH_CONTENT.append(find(r"十次</a><br />(.*?)<br />乐斗"))

    # 兑换
    if num := find(r"溢出积分：(\d+)"):
        num_10 = int(int(num) / 10)
        num_1 = int(num) - (num_10 * 10)
        for _ in range(num_10):
            # 兑换十次
            get("cmd=newAct&subtype=176&op=2&num=10")
            PUSH_CONTENT.append(find(r"积分。<br /><br />(.*?)<br />"))
        for _ in range(num_1):
            # 兑换一次
            get("cmd=newAct&subtype=176&op=2&num=1")
            PUSH_CONTENT.append(find(r"积分。<br /><br />(.*?)<br />"))


def 斗境探秘():
    """
    领取每日探秘奖励、累计探秘奖励
    """
    # 斗境探秘
    get("cmd=newAct&subtype=177")
    # 领取每日探秘奖励
    for _id in findall(r"id=(\d+)&amp;type=2"):
        # 领取
        get(f"cmd=newAct&subtype=177&op=2&id={_id}&type=2")
        PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))

    # 领取累计探秘奖励
    for _id in findall(r"id=(\d+)&amp;type=1"):
        # 领取
        get(f"cmd=newAct&subtype=177&op=2&id={_id}&type=1")
        PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))


def 幸运金蛋():
    """
    砸金蛋
    """
    # 幸运金蛋
    get("cmd=newAct&subtype=110&op=0")
    if index := find(r"index=(\d+)"):
        # 砸金蛋
        get(f"cmd=newAct&subtype=110&op=1&index={index}")
        PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))
    else:
        print_info("没有可砸蛋")
        PUSH_CONTENT.append("没有可砸蛋")


def 春联大赛():
    """
    选择、领取斗币各三次
    """
    # 开始答题
    get("cmd=newAct&subtype=146&op=1")
    if "您的活跃度不足" in HTML:
        print_info("您的活跃度不足50")
        PUSH_CONTENT.append("您的活跃度不足50")
        return
    elif "今日答题已结束" in HTML:
        print_info("今日答题已结束")
        PUSH_CONTENT.append("今日答题已结束")
        return

    _data = {
        "虎年腾大步": "兔岁展宏图",
        "虎辟长安道": "兔开大吉春",
        "虎跃前程去": "兔携好运来",
        "虎去雄风在": "兔来喜气浓",
        "虎带祥云去": "兔铺锦绣来",
        "虎蹄留胜迹": "兔角搏青云",
        "虎留英雄气": "兔会世纪风",
        "金虎辞旧岁": "银兔贺新春",
        "虎威惊盛世": "兔翰绘新春",
        "虎驰金世界": "兔唤玉乾坤",
        "虎声传捷报": "兔影抖春晖",
        "虎嘶飞雪里": "兔舞画图中",
        "兔归皓月亮": "花绽春光妍",
        "兔俊千山秀": "春暖万水清",
        "兔毫抒壮志": "燕梭织春光",
        "玉兔迎春至": "黄莺报喜来",
        "玉兔迎春到": "红梅祝福来",
        "玉兔蟾宫笑": "红梅五岭香",
        "卯时春入户": "兔岁喜盈门",
        "卯门生紫气": "兔岁报新春",
        "卯来四季美": "兔献百家福",
        "红梅迎春笑": "玉兔出月欢",
        "红梅赠虎岁": "彩烛耀兔年",
        "红梅迎雪放": "玉兔踏春来",
        "丁年歌盛世": "卯兔耀中华",
        "寅年春锦绣": "卯序业辉煌",
        "燕舞春光丽": "兔奔曙光新",
        "笙歌辞旧岁": "兔酒庆新春",
        "瑞雪兆丰年": "迎得玉兔归",
        "雪消狮子瘦": "月满兔儿肥",
    }
    for _ in range(3):
        for s in findall(r"上联：(.*?) 下联："):
            if x := _data.get(s):
                xialian = find(f"{x}<a.*?index=(\d+)")
            else:
                # 上联在字库中不存在，将随机选择
                xialian = [random.choice(range(3))]

            # 选择
            # index 0 1 2
            get(f"cmd=newAct&subtype=146&op=3&index={xialian[0]}")
            PUSH_CONTENT.append(find(r"剩余\d+题<br />(.*?)<br />"))
            # 确定选择
            get("cmd=newAct&subtype=146&op=2")
            PUSH_CONTENT.append(find())

    for _id in range(1, 4):
        # 领取
        get(f"cmd=newAct&subtype=146&op=4&id={_id}")
        PUSH_CONTENT.append(find())


def 新春拜年():
    """
    第一轮赠礼三个随机礼物
    第二轮收取礼物
    """
    # 新春拜年
    get("cmd=newAct&subtype=147")
    if "op=1" in HTML:
        for index in random.sample(range(5), 3):
            # 选中
            get(f"cmd=newAct&subtype=147&op=1&index={index}")
        # 赠礼
        get("cmd=newAct&subtype=147&op=2")
        PUSH_CONTENT.append("已赠礼")
    elif "op=3" in HTML:
        # 收取礼物
        get("cmd=newAct&subtype=147&op=3")
        PUSH_CONTENT.append(find(r"祝您：.*?<br /><br />(.*?)<br />"))


def 喜从天降():
    """
    每天至多点燃烟花10次，活动时间20.00-22.00
    """
    for _ in range(10):
        get("cmd=newAct&subtype=137&op=1")
        PUSH_CONTENT.append(find())
        if "燃放烟花次数不足" in HTML:
            break


def 五一礼包():
    """
    周四领取三次劳动节礼包
    """
    for _id in range(3):
        get(f"cmd=newAct&subtype=113&op=1&id={_id}")
        PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<"))


def 端午有礼():
    """
    周四兑换礼包：2次礼包4、1次礼包3
    活动期间最多可以得到 4x7=28 个粽子

    index
    3       礼包4：消耗10粽子得到 淬火结晶*5+真黄金卷轴*5+徽章符文石*5+修为丹*5+境界丹*5+元婴飞仙果*5
    2       礼包3：消耗8粽子得到 2级日曜石*1+2级玛瑙石*1+2级迅捷石*1+2级月光石*1+2级紫黑玉*1
    1       礼包2：消耗6粽子得到 阅历羊皮卷*5+无字天书*5+河图洛书*5+还童天书*1
    0       礼包1：消耗4粽子得到 中体力*2+挑战书*2+斗神符*2
    """
    for _ in range(2):
        # 礼包4
        get("cmd=newAct&subtype=121&op=1&index=3")
        PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))
        if "您的端午香粽不足" in HTML:
            break

    # 礼包3
    get("cmd=newAct&subtype=121&op=1&index=2")
    PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))


def 圣诞有礼():
    """
    周四领取点亮奖励和连线奖励
    """
    # 圣诞有礼
    get("cmd=newAct&subtype=145")
    for _id in findall(r"task_id=(\d+)"):
        # 任务描述：领取奖励
        get(f"cmd=newAct&subtype=145&op=1&task_id={_id}")
        PUSH_CONTENT.append(find())

    # 连线奖励
    for i in findall(r"index=(\d+)"):
        get(f"cmd=newAct&subtype=145&op=2&index={i}")
        PUSH_CONTENT.append(find())


def 新春礼包():
    """
    周四领取礼包
    """
    for _id in [280, 281, 282]:
        # 领取
        get(f"cmd=xinChunGift&subtype=2&giftid={_id}")
        PUSH_CONTENT.append(find())


def 登录商店():
    """
    周四兑换材料
    """
    t: int = YAML["登录商店"]
    for _ in range(5):
        # 兑换5次
        get(f"cmd=newAct&op=exchange&subtype=52&type={t}&times=5")
        PUSH_CONTENT.append(find(r"<br /><br />(.*?)<br /><br />"))
    for _ in range(3):
        # 兑换1次
        get(f"cmd=newAct&op=exchange&subtype=52&type={t}&times=1")
        PUSH_CONTENT.append(find(r"<br /><br />(.*?)<br /><br />"))


def 盛世巡礼():
    """
    周四收下礼物
    """
    for s in range(1, 8):
        # 点击进入
        get(f"cmd=newAct&subtype=150&op=2&sceneId={s}")
        if "他已经给过你礼物了" in HTML:
            print_info(f"礼物已领取", f"盛世巡礼-地点{s}")
            PUSH_CONTENT.append(f"地点{s}礼物已领取")
        elif s == 7 and ("点击继续" not in HTML):
            print_info(f"礼物已领取", f"盛世巡礼-地点{s}")
            PUSH_CONTENT.append(f"地点{s}礼物已领取")
        elif item := find(r"itemId=(\d+)", f"盛世巡礼-地点{s}-itemId"):
            # 收下礼物
            get(f"cmd=newAct&subtype=150&op=5&itemId={item}")
            _msg = find(r"礼物<br />(.*?)<br />", f"盛世巡礼-地点{s}-收下礼物")
            PUSH_CONTENT.append(f"地点{s}领取{_msg}")


def 新春登录礼():
    """
    每天至多领取七次
    """
    # 新春登录礼
    get("cmd=newAct&subtype=99&op=0")
    day = findall(r"day=(\d+)")
    if not day:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")
        return

    for d in day:
        # 领取
        get(f"cmd=newAct&subtype=99&op=1&day={d}")
        PUSH_CONTENT.append(find())


def 年兽大作战():
    """
    随机武技库免费一次
    自选武技库从大、中、小、投、技各随机选择一个补位
    挑战3次
    """
    # 年兽大作战
    get("cmd=newAct&subtype=170&op=0")
    if "等级不够" in HTML:
        print_info("等级不够，还未开启年兽大作战哦！")
        PUSH_CONTENT.append("等级不够，还未开启年兽大作战哦！")
        return

    for _ in find(r"剩余免费随机次数：(\d+)"):
        # 随机武技库 免费一次
        get("cmd=newAct&subtype=170&op=6")
        PUSH_CONTENT.append(find(r"帮助</a><br />(.*?)<br />"))

    # 自选武技库
    # 从大、中、小、投、技各随机选择一个
    if "暂未选择" in HTML:
        for t in range(5):
            get(f"cmd=newAct&subtype=170&op=4&type={t}")
            if "取消选择" in HTML:
                continue
            if ids := findall(r'id=(\d+)">选择'):
                # 选择
                get(f"cmd=newAct&subtype=170&op=7&id={random.choice(ids)}")
                if "自选武技列表已满" in HTML:
                    break

    for _ in range(3):
        # 挑战
        get("cmd=newAct&subtype=170&op=8")
        PUSH_CONTENT.append(find(r"帮助</a><br />(.*?)。"))


def 惊喜刮刮卡():
    """
    每天至多领取三次、点击刮卡二十次
    """
    # 领取
    for _id in range(3):
        get(f"cmd=newAct&subtype=148&op=2&id={_id}")
        PUSH_CONTENT.append(find(r"奖池预览</a><br /><br />(.*?)<br />"))

    # 刮卡
    for _ in range(20):
        get("cmd=newAct&subtype=148&op=1")
        PUSH_CONTENT.append(find(r"奖池预览</a><br /><br />(.*?)<br />"))
        if "您没有刮刮卡了" in HTML:
            break
        elif "不在刮奖时间不能刮奖" in HTML:
            break


def 开心娃娃机():
    """
    每天免费抓取一次
    """
    # 开心娃娃机
    get("cmd=newAct&subtype=124&op=0")
    if "1/1" not in HTML:
        print_info("没有免费抓取次数")
        PUSH_CONTENT.append("没有免费抓取次数")
        return

    # 抓取一次
    get("cmd=newAct&subtype=124&op=1")
    PUSH_CONTENT.append(find())


def 好礼步步升():
    """
    每天领取一次
    """
    get("cmd=newAct&subtype=43&op=get")
    PUSH_CONTENT.append(find())


def 企鹅吉利兑():
    """
    每天领取、活动截止日的前一天兑换材料（每种至多兑换100次）
    """
    # 企鹅吉利兑
    get("cmd=geelyexchange")
    _data = findall(r'id=(\d+)">领取</a>')
    if not _data:
        print_info("没有礼包领取")
        PUSH_CONTENT.append("没有礼包领取")

    for _id in _data:
        # 领取
        get(f"cmd=geelyexchange&op=GetTaskReward&id={_id}")
        PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br /><br />"))

    day: str = find(r"至\d+月(\d+)日")
    if DAY != (int(day) - 1):
        return

    yaml: list = YAML["企鹅吉利兑"]
    for _id in yaml:
        for _ in range(100):
            get(f"cmd=geelyexchange&op=ExchangeProps&id={_id}")
            if "你的精魄不足，快去完成任务吧~" in HTML:
                break
            elif "该物品已达兑换上限~" in HTML:
                break
            PUSH_CONTENT.append(find(r"】<br /><br />(.*?)<br />"))
        if "当前精魄：0" in HTML:
            break


def 乐斗大笨钟():
    """
    领取一次
    """
    # 领取
    get("cmd=newAct&subtype=18")
    PUSH_CONTENT.append(find(r"<br /><br /><br />(.*?)<br />"))


def 乐斗回忆录():
    """
    周四领取回忆礼包
    """
    for _id in [1, 3, 5, 7, 9]:
        # 回忆礼包
        get(f"cmd=newAct&subtype=171&op=3&id={_id}")
        PUSH_CONTENT.append(find(r"6点<br />(.*?)<br />"))


def 爱的同心结():
    """
    依次兑换礼包5、4、3、2、1
    """
    _data = {
        4016: 20,
        4015: 16,
        4014: 10,
        4013: 4,
        4012: 2,
    }
    for _id, count in _data.items():
        for _ in range(count):
            # 兑换
            get(f"cmd=loveknot&sub=2&id={_id}")
            PUSH_CONTENT.append(find())
            if "恭喜您兑换成功" not in HTML:
                break


def 周年生日祝福():
    """
    周四领取
    """
    for day in range(1, 8):
        get(f"cmd=newAct&subtype=165&op=3&day={day}")
        PUSH_CONTENT.append(find())
