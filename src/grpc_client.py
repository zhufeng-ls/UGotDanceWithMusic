import time as tm
import grpc

from ugot.grpc_pb import model_pb2
from ugot.grpc_pb import model_pb2_grpc
from ugot.grpc_pb import servo_pb2
from ugot.grpc_pb import servo_pb2_grpc
from ugot.grpc_pb import device_pb2
from ugot.grpc_pb import device_pb2_grpc
from ugot.grpc_pb import audio_pb2
from ugot.grpc_pb import audio_pb2_grpc


class Joint:
    def __init__(self, device_id, angle, time):
        self.device_id = device_id
        self.angle = angle
        self.time = time


class GrpcClient:
    def __init__(self, url):
        self.channel = None
        self.url = url

    def connect(self):
        self.channel = grpc.insecure_channel(self.url)

    def forward(self):
        pass

    def set_joint_position(self, position, time):
        stub = model_pb2_grpc.ModelServiceGrpcStub(channel=self.channel)
        transform_arms_control_param = model_pb2.TransformArmsControlParam(joint=1, position=position, time=int(time/20))
        req = model_pb2.TransformArmsControlRequest(type="transform", params=transform_arms_control_param)
        resp = stub.transformArmsControl(req)

        transform_arms_control_param.joint = 2
        transform_arms_control_param.position = -position
        req = model_pb2.TransformArmsControlRequest(type="transform", params=transform_arms_control_param)
        resp = stub.transformArmsControl(req)

        transform_arms_control_param.joint = 3
        transform_arms_control_param.position = position
        req = model_pb2.TransformArmsControlRequest(type="transform", params=transform_arms_control_param)
        resp = stub.transformArmsControl(req)

        transform_arms_control_param.joint = 4
        transform_arms_control_param.position = -position
        req = model_pb2.TransformArmsControlRequest(type="transform", params=transform_arms_control_param)
        resp = stub.transformArmsControl(req)

        tm.sleep(time / 1000)

    def get_joint(self):
        stub = servo_pb2_grpc.ServoServiceGrpcStub(channel=self.channel)
        req = servo_pb2.RoboticArmGetJointsRequest()
        resp = stub.roboticArmGetJoints(req)
        print(resp.msg)
        print(len(resp.joints))

    def set_action(self, lf_joint, lb_joint, rb_point, rf_joint) -> servo_pb2.ServoRotateResponse:
        """
        lf: 左前关节
        lb: 左后关节
        rb: 右后关节
        rf: 右前关节
        """
        stub = servo_pb2_grpc.ServoServiceGrpcStub(channel=self.channel)
        req = servo_pb2.ServoRotateByAngleRequest()

        left_forward_joint = servo_pb2.ServoAngleInfo()
        left_forward_joint.deviceId = lf_joint.device_id
        left_forward_joint.angle = lf_joint.angle
        left_forward_joint.duration = lf_joint.time
        req.servo_rotate.append(left_forward_joint)

        left_back_joint = servo_pb2.ServoAngleInfo()
        left_back_joint.deviceId = lb_joint.device_id
        left_back_joint.angle = lb_joint.angle
        left_back_joint.duration = lb_joint.time
        req.servo_rotate.append(left_back_joint)

        right_back_joint = servo_pb2.ServoAngleInfo()
        right_back_joint.deviceId = rb_point.device_id
        right_back_joint.angle = rb_point.angle
        right_back_joint.duration = rb_point.time
        req.servo_rotate.append(right_back_joint)

        right_forward_joint = servo_pb2.ServoAngleInfo()
        right_forward_joint.deviceId = rf_joint.device_id
        right_forward_joint.angle = rf_joint.angle
        right_forward_joint.duration = rf_joint.time
        req.servo_rotate.append(right_forward_joint)

        resp = stub.setServoRotateByAngle(req)
        return resp

    def get_device_list(self) -> device_pb2.DeviceListResponse:
        stub = device_pb2_grpc.DeviceServiceGrpcStub(channel=self.channel)
        req = device_pb2.DeviceListRequest()
        resp = stub.getDeviceList(req)
        tm.sleep(1)
        return resp

    def init_joint_info(self):
        resp = self.get_device_list()
        pass

    def reset_joint(self):
        pass

    def move_joint_position(self):
        pass

    def play_music(self, path) -> audio_pb2.AudioCommonResponse:
        stub = audio_pb2_grpc.AudioServiceGrpcStub(channel=self.channel)
        # 先添加音频文件到数据库
        req = audio_pb2.AudioFileRequest(audio_name=path, audio_type=0)
        resp = stub.insertAudioFile(req)
        print("code: ", resp.code, " msg: ", resp.msg)
        # 获取音频文件列表
        req = audio_pb2.AudioFileListRequest(audio_type=0)
        resp = stub.getAudioFileList(req)
        print("code: ", resp.code, " msg: ", resp.msg)
        for file in resp.files:
            print("file: ", file.file, " len: ", file.len)
        # 播放音频文件
        req = audio_pb2.AudioPlayRequest(audio_type=0, audio_file=path)
        resp = stub.playAudioFile(req)
        print("code: ", resp.code, " msg: ", resp.msg)
        return resp

    def stop_music(self) -> audio_pb2.AudioCommonResponse:
        stub = audio_pb2_grpc.AudioServiceGrpcStub(channel=self.channel)
        resp = stub.insertAudioFile(audio_pb2.AudioEmptyRequest())
        print("code: ", resp.code, " msg: ", resp.msg)

    def close(self):
        pass
