import librosa
import numpy as np

def detect_beats(wavfilePath):
    musicArray, sampleRate = librosa.load(wavfilePath, sr=None, mono=True)
    sampleSize = 1024
    numSamples = len(musicArray) // sampleSize
    print("音乐数组大小：", len(musicArray))
    print("样本数：", numSamples)

    energyArray = []
    for i in range(0, numSamples):
        sample = musicArray[i * sampleSize: (i + 1) * sampleSize]
        sampleEnergy = np.sum(sample ** 2)
        energyArray.append(sampleEnergy)

    energyArray = librosa.util.normalize(energyArray)

    avgEnrg = np.mean(energyArray[:43])
    var = np.var(energyArray[:43])
    cValue = (-0.0025714 * var) + 1.5142857

    beats = []
    for energy in energyArray[:43]:
        if energy > (avgEnrg / 43) * cValue:
            beats.append(1)
        else:
            beats.append(0)

    for i in range(43, len(energyArray)):
        avgEnrg = avgEnrg - energyArray[i - 43] + energyArray[i]
        var = np.var(energyArray[i - 43: i])
        cValue = (-0.0025714 * var) + 1.5142857
        if energyArray[i] > (avgEnrg / 43) * cValue:
            beats.append(1)
        else:
            beats.append(0)

    beatArray = []
    minBeatRepeat = 6
    i = 0
    while i < len(beats):
        if beats[i] == 1:
            beatArray.append(i)
            i = i + minBeatRepeat
        else:
            i = i + 1

    finalBeatArray = np.zeros(len(beats))
    finalBeatArray[beatArray] = 1

    beatPosition = librosa.samples_to_time(beatArray, sr=sampleRate)
    print(beatPosition*1000)
    return musicArray, energyArray, finalBeatArray, beatArray, beatPosition


def detectPeriod(musicArray, energyArray, finalBeatArray, beatArray):
    maxBeatsPerPeriod = 10
    periodThreshold = 50
    numBeats = np.sum(finalBeatArray)

    stdev = np.zeros(maxBeatsPerPeriod)
    for i in range(0, maxBeatsPerPeriod):
        sqSum = 0
        s = 0
        for j in range(0, numBeats - maxBeatsPerPeriod):
            sqSum = sqSum + ((beatArray[j + i + 1] - beatArray[j]) * (beatArray[j + i + 1] - beatArray[j]))
            s = s + (beatArray[j + i + 1] - beatArray[j])
        s = s / (numBeats - maxBeatsPerPeriod)
        sqSum = sqSum / (numBeats - maxBeatsPerPeriod)
        stdev[i] = sqSum - (s * s)

    print(stdev)
    numBeatsInPeriod = np.argmin(stdev) + 1
    return numBeatsInPeriod