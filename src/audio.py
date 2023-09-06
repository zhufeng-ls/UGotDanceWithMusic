import time

from pydub import AudioSegment
from pydub.playback import play
import librosa
import numpy as np
import sounddevice as sd

from src.grpc_client import GrpcClient

# ugot音频类,一帧一帧的播放音乐,播放音乐的同时,控制机器人的运动.


class Audio:
    def __init__(self, grpc_client):
        self.grpc = grpc_client

        self.frame_duration = 0 # 计算每帧的持续时间
        self.index = 0
        self.path = ""
        self.frame_count = 0
        self.frame_rate = 0
        self.channels = 0

        self.audio = None
        self.beats = None
        self.pulse = None
        self.beat_times = None
        self.one_set_env = None
        self.samples = None

    def open(self, path):
        self.path = path
        self.audio = AudioSegment.from_file(path, format='mp3')
        # 转换为单声道
        if self.audio.channels == 2:
            music = self.audio.set_channels(1)
        self.frame_count = int(self.audio.frame_count())
        self.frame_rate = self.audio.frame_rate
        self.frame_duration = 1000 / self.frame_rate
        self.channels = self.audio.channels

        music = self.audio

        y1 = np.array(music.get_array_of_samples(), dtype=np.float32) / 32768.0
        tempo, self.beats = librosa.beat.beat_track(y=y1, sr=music.frame_rate)
        self.one_set_env = librosa.onset.onset_strength(y=y1, sr=music.frame_rate)
        self.pulse = librosa.beat.plp(onset_envelope=self.one_set_env, sr=music.frame_rate)
        self.beat_times = librosa.frames_to_time(self.beats, sr=music.frame_rate)
        print("onset size: ", self.one_set_env.size)
        print("beats size: ", self.beat_times.size)
        print("pulse size: ", self.pulse.size)
        print("frame rate: ", self.frame_rate, " frame_duration: ", self.frame_duration)

    def close(self):
        self.audio.close()

    # onset 表示强度,执行更激烈或更柔和的动作,动作幅度更大
    # pulse 表示脉冲,执行更快速或更慢的动作,即震动频率更快.
    # beats 表示节拍,根据节拍来调整动作.根据节拍动做不同的动作.
    def play(self, frame_duration=5):
        frame_size = int(self.frame_rate * frame_duration / 1000)
        # segment = self.audio[5000, 10000]
        # play(self.audio)
        # return
        for frame in self.samples:
            print("once play")
            sd.play(frame, samplerate=self.frame_rate, device='HDA Intel PCH')
            sd.wait()

    def play_by_ugot(self, path):
        resp = self.grpc.play_music(path)
        # print("code: ", resp.code, " msg: ", resp.msg)

    def stop_music(self):
        resp = self.grpc.stop_music()

    def stop(self):
        self.audio.stop()


