# 机器人跳舞

> 将音乐的节奏变化通过机器人展现出来.需要分析的音乐类型有两种. 一种是快节奏的音乐,每个节拍之间都要做一个动作; 一种是慢节奏的音乐,需要分析高音,低音,高低起伏等各种音乐节奏.这种更为复杂.需要通过音乐的能量图谱,节拍变化,及高音的比例.

## 一. 分析

1. 通过分析音乐振幅,让机器人上下有节奏的律动.
2. 通过分析音乐高音所占的比例,来判断是高音还是低音
3. 通过观察音乐样本数据,发现了音乐样本的数据是高低起伏的,包含了大量的负值和0值.
4. 如果需要更准确的识别音乐图谱,辨别音乐节奏是快还是慢,音调是高还是低,需要用到深度学习.使用大量的音乐数据进行训练.

## 二. 实现

下面是代码中可供调节的参数
```py
# 节拍模式,即间隔多少拍做一个动作,每拍的时间大约为0.5s.
beat_mode = 1
# ugot主控的ip地址,通过 <<设置>> -> <<系统信息>> -> <<本机IP>> 获取.
ip = "10.10.67.74"
# 本地的音频文件路径,上传音频或播放音频需要用到这个路径
audio_file_name = 'resource/zhejiushiai.mp3'
```

### 2.1 上传音乐

```py
def upload_audio(audio_path):
    global ip

    url = "http://" + ip + ":7000" + "/ucode/audio"
    print("url: ", url, " audio_path: ", audio_path)
    file = {'file': open(audio_path, 'rb')}
    response = requests.post(url=url, files=file)
    print("response: ", response)
```
注意,只能上传比特率为**128k/s**的音频,可以通过ffmpeg查看音乐的比特率.
```bash
ffprobe resource/zhejiushiai.mp3
```

### 2.2 获取音乐数据信息
```py
def analysis_audio():
    global dance
    global audio_file_name
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
    # 提取能量信息
    energy = librosa.feature.rms(y=y)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    beat_index = (beat_times * sr).astype(int)
    beat_start_time = beat_times[0]
    print("beat time start: ", beat_times[0])
```
这里面提取了节拍,脉冲信息,每个节拍对应的帧序号和时间点,以及能量信息(没有用到).

### 2.3 播放上传的音乐
```py
def play_audio():
    global audio
    global grpc_client

    audio = Audio(grpc_client)
    audio_name = os.path.basename(audio_file_name)
    print('audio_file_path: ', audio_file_name, " audio_file_name: ", audio_name)
    time.sleep(beat_start_time)
    audio.play_by_ugot(audio_name)
```
注意,播放音乐是阻塞的,所以需要放在线程中运行,这样我们就可以在播放音乐的同时,控制ugot机器人的运动.
```py
if played:
    thread = threading.Thread(target=play_audio)
    thread.daemon = True
    thread.start()
```

### 2.4 分析音乐.

分析音乐是快节奏还是慢节奏,音频是高音还是低音.有多种方式,这里我使用了两种方式.分别是分析节拍样本值和分析高音占比.

#### 2.4.1 分析节拍样本值
```py
def dance_refer_to_music():
    last = 0
    # 最少运动时间为10毫秒
    last_time = -0.01
    for i in range(beat_index.size):
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
```
通过比较当前节拍和上次节拍的样本值的大小,来判断下一步执行的动作.这种判断方法不是很准确,且只适合快节奏的音乐.它每个节拍都会执行一次动作,运动频率太快.

#### 2.4.2 分析高音占比
```py
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
    my_time.add_time_point()

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
        my_time.add_time_point()

        current_time_3 = MyTime.now()

        print('[current] ', current_time, ' ',
              current_time_1, ' ',
              current_time_2, ' ', current_time_3)
```
通过设置高音和低音的阈值,来分析大于或小于该阈值的数据在一段音频数据中的占比,判断该音频是高音还是低音.
阈值是可以自己调节的,且占比也是需要自己反复观察调节的.这种方式只适合针对某一种音乐来调节,没有太大的通用性.


### 2.5 控制机器人跳舞
```py
def dance_by_beat_diff(audio_segment):
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

    my_time.add_time_point()
    print("diff time: ", my_time.print(),
          ' dance: ', audio_segment.dance_time,
          ' reset: ', audio_segment.reset_time)
    my_time.add_time_point()
```
动作目前只设置了4种.即前倾,后倾,左倾,右倾,还可以添加上升和下降.

通过分析音乐高音的占比,来做不同的动作,这样很容易做重复的动作,这个动作策略需要优化,且判断参数不应该只有一个.

## 三. 控制机器人运动

### 3.1 前期准备
1. 一个可用的wifi环境,ugot需要和电脑保持在同一个局域网内.
2. 拼好变形车.
3. ugot运动模型需要选择变形车.
4. 获取变形车ip地址.
5. 将变形车放在1x1米的空旷平整地带.
6. 安装好python的依赖包.librosa的版本不能太高,否则会报错,我的版本为0.10.1.

### 3.2 启动设备
1. 更改main.py中的ip参数,将其设置上述从ugot中获取到的地址.
2. 运行命令`python main.py --upload resource/zhejiushiai.mp3 --play --dance 2`, 此时机器人开始播放音乐并跳舞.


## 四. 完善点
1. 机器人做动作的指令发出去后,代码会分两次休眠, 一次休眠等待做动作,一次休眠等待机器人复位,两次休眠的延迟会很高,还不包含grpc请求的耗时.所以要力求更准确,必须手动补偿这两个地方的延时.
2. ugot升高,降低,或者左倾,右倾,如果节奏过快,都会导致机器人偏移.
3. 可以通过傅里叶变换获取音谱数据, 然后通过每段音频内的能量总和,来分析这段音频是高音和低音.


## 五. 扩展

[仓库代码的源地址](https://github.com/zhufeng-ls/UGotDanceWithMusic.git),有需要的可以拉取.
