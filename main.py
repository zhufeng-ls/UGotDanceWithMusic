import os
import time
import requests
import threading
import argparse

from src.time import Time as MyTime
from src.dance import DanceUtil
from src.dance import DanceType
from src.audio import Audio
from src.grpc_client import GrpcClient

import librosa
import librosa.display
import sounddevice as sd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # 或者选择其他支持图形窗口的后端


class AudioSegment:
    def __init__(self):
        self.num = 0
        self.last = 0
        self.high = 0
        self.dance_time = 0
        self.reset_time = 0.8
        self.data = []

    def reset(self):
        self.num = 0
        self.last = 0
        self.high = 0
        self.dance_time = 0
        self.reset_time = 0.8
        self.data = []


dance = None
audio = None
ws = None
grpc_client = None
ip = "10.10.67.74"
audio_file_name = 'resource/zhejiushiai.mp3' # zhejiushiai.mp3' # 4_fast_tante.mp3 # mereke.mp3
my = MyTime()

beat_times = None
beat_index = None
sr = None
y = None
energy = None
beat_mode = 1
beat_interval = 1
beat_start_time = 0


def upload_audio(audio_path):
    global ip

    url = "http://" + ip + ":7000" + "/ucode/audio"
    print("url: ", url, " audio_path: ", audio_path)
    file = {'file': open(audio_path, 'rb')}
    response = requests.post(url=url, files=file)
    print("response: ", response)


def analysis_audio():
    global dance
    global audio_file_name
    global beat_interval
    global energy
    global beat_times
    global beat_index
    global beat_start_time
    global sr
    global y

    sr = librosa.get_samplerate(audio_file_name)

    # 合成单声道
    y, sr = librosa.load(audio_file_name, sr=sr, mono=True)
    # print("y. size: ", y.size, " sr: ", sr)

    duration = librosa.get_duration(y=y, sr=sr)
    frame_count = int(duration * sr)

    print("frame_count: ", frame_count, ' duration: ', duration)

    # 提取节拍信息
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    # 提取脉冲信息
    energy = librosa.feature.rms(y=y)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    beat_index = (beat_times * sr).astype(int)
    beat_intervals = np.diff(beat_times)
    beat_interval = np.mean(beat_intervals)
    beat_start_time = beat_times[0]
    print("beat time start: ", beat_times[0], " beat_interval: ", beat_interval)


def analysis_beat():
    pass


def display():
    plt.figure(figsize=(12, 6))
    # 打印能量变化
    plt.plot(energy[0])
    plt.xlabel('Frame')
    plt.ylabel('Energy')
    plt.title('Energy Variation')
    plt.tight_layout()
    plt.savefig('energy.png')  # 可选：保存图谱为图片文件
    plt.show()


def dance_refer_to_music():
    last = 0
    # 最少运动时间为10毫秒
    last_time = -0.01
    for i in range(beat_index.size):
        print('once')
        my = MyTime()
        my.add_time_point()
        cur = y[int(beat_index[i])]
        cur_time = beat_times[i]
        tm_f = cur_time - last_time
        tm = tm_f / 2

        if cur < 0:
            if last >= 0:
                dance.set_action(DanceType.LEFT_LEAN, tm, True, tm)
            else:
                if cur < last:
                    dance.set_action(DanceType.FORWARD_LEAN, tm, True, tm)
                else:
                    dance.set_action(DanceType.BACK_LEAN, tm, True, tm)
        else:
            if last < 0:
                dance.set_action(DanceType.RIGHT_LEAN, tm, True, tm)
            else:
                if cur < last:
                    dance.set_action(DanceType.LEFT_LEAN, tm, True, tm)
                else:
                    dance.set_action(DanceType.RIGHT_LEAN, tm, True, tm)
        my.add_time_point()
        real_time = my.print()
        print("脉冲: ", cur, " cur: ", cur_time, " plan tm: ", tm_f, ' real tm', real_time)

        last = cur
        last_time = cur_time

    dance.set_action(DanceType.NO_LEAN)


# 定义按键事件处理函数
def on_key(event):
    if event.key == 'Enter' or event.key == 'q':
        plt.close()


def dance_by_beat_diff(audio_segment):
    # 播放音乐
    # sd.play(audio_segment.data)
    # sd.wait()

    # 画音频图
    # duration = audio_segment.dance_time + audio_segment.reset_time
    # tm = np.linspace(0, duration, len(audio_segment.data))
    # print('duration: ', duration)
    # fig, ax = plt.subplots(figsize=(10, 4))
    # line, = ax.plot(tm, audio_segment.data)
    # ax.set_xlabel('Time (s)')
    # ax.set_ylabel('Amplitude')
    # ax.set_title('Audio Waveform')
    # fig.canvas.mpl_connect('key_press_event', on_key)
    # plt.show()

    # 跳舞
    if audio_segment.high >= 0.20:
        dance.set_action(DanceType.FORWARD_LEAN,
                         audio_segment.dance_time,
                         True,
                         audio_segment.reset_time)
    elif audio_segment.high >= 0.10:
        dance.set_action(DanceType.LEFT_LEAN,
                         audio_segment.dance_time,
                         True,
                         audio_segment.reset_time)
    elif audio_segment.high >= 0.01:
        dance.set_action(DanceType.RIGHT_LEAN,
                         audio_segment.dance_time,
                         True,
                         audio_segment.reset_time)
    else:
        dance.set_action(DanceType.BACK_LEAN,
                         audio_segment.dance_time,
                         True,
                         audio_segment.reset_time)

    my.add_time_point()
    print("diff time: ", my.print(),
          ' dance: ', audio_segment.dance_time,
          ' reset: ', audio_segment.reset_time)
    my.add_time_point()


def handle_audio_segment(audio_segment, audio_segment_temp, last, high):
    audio_segment.high = (audio_segment.high + high) / 2
    audio_segment.data += list(audio_segment_temp)
    audio_segment.last = last
    audio_segment.num = audio_segment.num + 1


def dance_by_huge_change_beats():
    """
    根据节拍的变化来判断当前应该做的动作,一个动作的周期最小的节拍周期,要么是2,要么是4,看哪个更接近1s.
    :return:
    """

    # 每次间隔4拍播放
    high_threshold = 0.3
    low_threshold = 0.10
    size = beat_index.size
    last_high_beat = False
    audio_segment = AudioSegment()
    my.add_time_point()

    for i in range(size):
        # 获取两个节拍之间的数据
        current_time = MyTime.now()
        audio_segment_temp = y[audio_segment.last:beat_index[i]]
        audio_segment_abs = np.abs(audio_segment_temp)
        low_mean = np.mean(audio_segment_abs < low_threshold)
        high_mean = np.mean(audio_segment_abs > high_threshold)
        # print('low_mean: ', low_mean, ' high_mean:', high_mean)
        beat_time = (beat_index[i] - audio_segment.last) / sr
        print('beat_time: ', beat_time)
        current_time_1 = MyTime.now()
        # 判断是不是高音
        if high_mean >= 0.2:
            # 如果上个节拍不是高音,那么就开始跳舞
            if not last_high_beat:
                audio_segment.dance_time = audio_segment.dance_time / 2
                audio_segment.reset_time = audio_segment.dance_time
                dance_by_beat_diff(audio_segment)
                # 跳完舞要重置数据
                audio_segment.reset()
                print('>>low beat<<')
                last_high_beat = False
            last_high_beat = True
        else:
            if audio_segment.num >= beat_mode:
                audio_segment.dance_time = audio_segment.dance_time / 2
                audio_segment.reset_time = audio_segment.dance_time
                dance_by_beat_diff(audio_segment)
                # 跳完舞要重置数据
                audio_segment.reset()
                if audio_segment.num > beat_time:
                    print('>>high beat<<')
                print('>>full beat<<')
        current_time_2 = MyTime.now()
        audio_segment.dance_time += beat_time
        handle_audio_segment(audio_segment, audio_segment_temp, beat_index[i], high_mean)
        my.add_time_point()

        current_time_3 = MyTime.now()

        print('[current] ', current_time, ' ',
              current_time_1, ' ',
              current_time_2, ' ', current_time_3)


def init_audio():
    global audio
    global grpc_client

    audio = Audio(grpc_client)
    audio_name = os.path.basename(audio_file_name)
    print('audio_file_path: ', audio_file_name, " audio_file_name: ", audio_name)
    time.sleep(beat_start_time)
    audio.play_by_ugot(audio_name)


def init_dance():
    global dance
    global grpc_client

    dance = DanceUtil(ip, grpc_client)
    dance.open()


def init_grpc():
    global grpc_client

    url = ip + ':50051'
    grpc_client = GrpcClient(url)
    grpc_client.connect()


def parse_cmdline_params():
    parser = argparse.ArgumentParser(description='命令行解析参数')
    parser.add_argument('--upload', help='上传音频文件')
    parser.add_argument('--audio', help='音频文件名')
    parser.add_argument('--dance', help='机器人跳舞')
    parser.add_argument('--beat_mode', help='节拍类型,4拍或8拍')
    parser.add_argument('--play', action='store_true', help='播放音频文件') # 不接后缀
    parser.add_argument('--display', action='store_true', help='显示音频图')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_cmdline_params()
    upload = args.upload
    _audio = args.audio
    played = args.play
    danced = args.dance
    _display = args.display
    _beat_mode = args.beat_mode

    init_grpc()
    analysis_audio()
    init_dance()

    if _audio:
        audio_file_name = _audio

    if _beat_mode:
        beat_mode = _beat_mode

    if upload:
        upload_audio(upload)

    if _display:
        display()

    if played:
        thread = threading.Thread(target=init_audio)
        thread.daemon = True
        thread.start()

    if danced:
        if danced == '1':
            print("mode 1")
            dance_refer_to_music()
        if danced == '2':
            dance_by_huge_change_beats()
        else:
            print('default mode')

    if played:
        thread.join(10)
