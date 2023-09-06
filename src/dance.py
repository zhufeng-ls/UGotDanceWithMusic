import time

from ugot import ugot
from enum import Enum
from src.grpc_client import Joint


class DanceType(Enum):
    """
    LEFT_LEAN: 左倾
    FORWARD_LEAN: 正前倾
    RIGHT_LEAN: 右倾
    BACK_LEAN: 后倾
    NO_LEAN: 复位成不倾斜
    MIXED: 混合
    """
    LEFT_LEAN = 1
    FORWARD_LEAN = 2
    RIGHT_LEAN = 3
    BACK_LEAN = 4
    UP = 5
    DOWN = 6
    MIXED = 7
    NO_LEAN = 10


class DanceUtil:
    def __init__(self, ip, grpc_client):
        self.grpc = grpc_client
        self.ugot_url = ip + ':8800'
        self.ugot = ugot.UGOT()
        self.left_forward_joint_id = '11'
        self.left_back_joint_id = '31'
        self.right_back_joint_id = '41'
        self.right_forward_joint_id = '61'

    def __del__(self):
        del self.ugot

    def init(self):
        resp = self.grpc.get_device_list()
        print("code: ", resp.code, " msg: ", resp.msg)
        datas = resp.data
        for key, values in datas.items():
            print("key: ", key)
            port = int(key[-1])
            for value in values.device_list:
                print("id: ", value.deviceId, " type: ", value.type, " sn: ", value.serial)

    def init_default(self):
        pass

    def open(self):
        # self.ugot.initialize(self.ugot_url)
        # self.init_default()
        pass

    def set_height(self, height):
        self.ugot.transform_set_chassis_height(height)

    def walk(self, direction, speed, tm):
        self.ugot.transform_move_speed_times(direction, speed, tm, 0)

    def reset_joint_action(self):
        tm = 234
        self.grpc.set_joint_position(-30, tm)

    def set_action_detail(self, lf, lb, rb, rf, tm_f=0.234):
        tm = int(tm_f * 1000 / 20)
        self.grpc.set_action(Joint(self.left_forward_joint_id
                                   , lf, tm),
                             Joint(self.left_back_joint_id
                                   , lb, tm),
                             Joint(self.right_back_joint_id
                                   , rb, tm),
                             Joint(self.right_forward_joint_id
                                   , rf, tm))
        # 运动时必须手动睡眠,不然会覆盖上一条运动指令
        time.sleep(tm_f)

    def set_action(self, dance_type, dance_time=0.234, reset=True, reset_time=0.234):
        ret = isinstance(dance_type, DanceType)
        if ret:
            """
            下面的值都是关节的绝对坐标值.
            * 参数1: 左前腿,必须为负值
            * 参数2: 左后腿,必须为正值
            * 参数3: 右后腿,必须为负值
            * 参数4: 右前腿,必须为正值
            * 参数5: 运动时间,单位毫秒
            """
            if dance_type == DanceType.LEFT_LEAN:
                self.set_action_detail(-7, 7, -36, 42, dance_time)
            elif dance_type == DanceType.FORWARD_LEAN:
                self.set_action_detail(-53, 11, -9, 55, dance_time)
            elif dance_type == DanceType.RIGHT_LEAN:
                self.set_action_detail(-53, 54, -14, 18, dance_time)
            elif dance_type == DanceType.BACK_LEAN:
                self.set_action_detail(-5, 55, -53, 8, dance_time)
            elif dance_type == DanceType.UP:
                self.set_action_detail(-72, 80, -75, 76, dance_time)
            elif dance_type == DanceType.DOWN:
                self.set_action_detail(-1, 8, -7, 4, dance_time)
            elif dance_type == DanceType.MIXED:
                self.set_action(DanceType.DOWN, dance_time, False)
                self.set_action(DanceType.NO_LEAN, dance_time, False)
                self.set_action(DanceType.FORWARD_LEAN, dance_time, False)
                self.set_action(DanceType.BACK_LEAN, dance_time, False)
                self.set_action(DanceType.RIGHT_LEAN, dance_time * 2, False)
                self.set_action(DanceType.NO_LEAN, dance_time * 2, False)
                self.set_action(DanceType.LEFT_LEAN, dance_time * 2, False)
                self.set_action(DanceType.NO_LEAN, dance_time * 2, False)
            elif dance_type == DanceType.NO_LEAN:
                self.set_action_detail(-40, 38, -37, 44, dance_time)

            if reset and dance_type != DanceType.NO_LEAN:
                self.set_action(DanceType.NO_LEAN, reset_time)

    def stop(self):
        self.ugot.transform_stop()
