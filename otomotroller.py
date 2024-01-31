#Library for using your Otamatone as an input device for your computer.
#Calls a listning thread that will listen for input from the Otamatone and output pitch or if tuned, the position of the note played on the Otamatone's stem.
'''
Guitar tuner script based on the Harmonic Product Spectrum (HPS)

MIT License
Copyright (c) 2021 chciken

Adapted into otamatroller by Mcall
'''

import copy
import os
import numpy as np
import scipy.fftpack
import sounddevice as sd
import time

# General settings that can be changed by the user
SAMPLE_FREQ = 20000 # sample frequency in Hz
WINDOW_SIZE = 400 # window size of the DFT in samples
WINDOW_STEP = 300 #s step size of window
NUM_HPS = 7 # max number of harmonic product spectrums
POWER_THRESH = 1e-6 # tuning is activated if the signal power exceeds this threshold
CONCERT_PITCH = 440 # defining a1
WHITE_NOISE_THRESH = 0.4 # everything under WHITE_NOISE_THRESH*avg_energy_per_freq is cut off

WINDOW_T_LEN = WINDOW_SIZE / SAMPLE_FREQ # length of the window in seconds
SAMPLE_T_LENGTH = 1 / SAMPLE_FREQ # length between two samples in seconds
DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE # frequency step width of the interpolated DFT
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]

# Global variables
max_freq = 0
OutsideCallback = None

#Sometimes, random notes are detected, this is a buffer to make sure that the note is actually being played
previousNoteBufferSize = 3
previousNoteBuffer = list()
currentSustainedNote = 0
sustainedCounter = 0
skipFirstNotes = 0



#config dictionary
config = {
    "otamatoneBottomFreq": 0,
    "otamatoneTopFreq": 0,
    "otamatoneMiddleFreq": 0,
}

def figureOutCallback():
    global OutsideCallback
    global max_freq
    global config

    otamatoneBottomFreq = config["otamatoneBottomFreq"]
    otamatoneTopFreq = config["otamatoneTopFreq"]
    otamatoneMiddleFreq = config["otamatoneMiddleFreq"]



    #No tuning, just return the freq
    if (otamatoneBottomFreq == 0 or otamatoneTopFreq == 0):
        return OutsideCallback(max_freq)
    
    #Tuning, return the position of the note
    #Non Middle Note
    if (otamatoneMiddleFreq == 0):
        if (max_freq < otamatoneBottomFreq):
            return OutsideCallback(0)
        elif (max_freq > otamatoneTopFreq):
            return OutsideCallback(1)
        else:
            return OutsideCallback((max_freq - otamatoneBottomFreq) / (otamatoneTopFreq - otamatoneBottomFreq))
    #Middle Note due to the way the otamatone is tuned, the middle note is not in the middle of the range, makes it a bit more accurate
    else:
        if (max_freq < otamatoneBottomFreq):
            return OutsideCallback(0)
        elif (max_freq > otamatoneTopFreq):
            return OutsideCallback(1)
        elif (max_freq < otamatoneMiddleFreq):
            return OutsideCallback((max_freq - otamatoneBottomFreq) / (otamatoneMiddleFreq - otamatoneBottomFreq) / 2)
        else:
            return OutsideCallback((max_freq - otamatoneMiddleFreq) / (otamatoneTopFreq - otamatoneMiddleFreq) / 2 + 0.5)
    

ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
def find_closest_note(pitch):
  """
  This function finds the closest note for a given pitch
  Parameters:
    pitch (float): pitch given in hertz
  Returns:
    closest_note (str): e.g. a, g#, ..
    closest_pitch (float): pitch of the closest note in hertz
  """
  i = int(np.round(np.log2(pitch/CONCERT_PITCH)*12))
  closest_note = ALL_NOTES[i%12] + str(4 + (i + 9) // 12)
  closest_pitch = CONCERT_PITCH*2**(i/12)
  return closest_note, closest_pitch

ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
def find_closest_note(pitch):
  """
  This function finds the closest note for a given pitch
  Parameters:
    pitch (float): pitch given in hertz
  Returns:
    closest_note (str): e.g. a, g#, ..
    closest_pitch (float): pitch of the closest note in hertz
  """
  i = int(np.round(np.log2(pitch/CONCERT_PITCH)*12))
  closest_note = ALL_NOTES[i%12] + str(4 + (i + 9) // 12)
  closest_pitch = CONCERT_PITCH*2**(i/12)
  return closest_note, closest_pitch


HANN_WINDOW = np.hanning(WINDOW_SIZE)
def callback(indata, frames, time, status):
  global previousNoteBuffer
  global previousNoteBufferSize
  global max_freq
  global sustainedCounter
  global skipFirstNotes
  global currentSustainedNote

  """
  Callback function of the InputStream method.
  That's where the magic happens ;)
  """
  # define static variables
  if not hasattr(callback, "window_samples"):
    callback.window_samples = [0 for _ in range(WINDOW_SIZE)]
  if not hasattr(callback, "noteBuffer"):
    callback.noteBuffer = ["1","2"]

  if status:
    print(status)
    return
  if any(indata):
    callback.window_samples = np.concatenate((callback.window_samples, indata[:, 0])) # append new samples
    callback.window_samples = callback.window_samples[len(indata[:, 0]):] # remove old samples

    # skip if signal power is too low
    signal_power = (np.linalg.norm(callback.window_samples, ord=2)**2) / len(callback.window_samples)
    if signal_power < POWER_THRESH:
      max_freq = 0
      figureOutCallback()
      previousNoteBuffer = list()
      sustainedCounter = 0
      return

    # avoid spectral leakage by multiplying the signal with a hann window
    hann_samples = callback.window_samples * HANN_WINDOW
    magnitude_spec = abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples)//2])

    # supress mains hum, set everything below 62Hz to zero
    for i in range(int(62/DELTA_FREQ)):
      magnitude_spec[i] = 0

    # calculate average energy per frequency for the octave bands
    # and suppress everything below it
    for j in range(len(OCTAVE_BANDS)-1):
      ind_start = int(OCTAVE_BANDS[j]/DELTA_FREQ)
      ind_end = int(OCTAVE_BANDS[j+1]/DELTA_FREQ)
      ind_end = ind_end if len(magnitude_spec) > ind_end else len(magnitude_spec)
      avg_energy_per_freq = (np.linalg.norm(magnitude_spec[ind_start:ind_end], ord=2)**2) / (ind_end-ind_start)
      avg_energy_per_freq = avg_energy_per_freq**0.5
      for i in range(ind_start, ind_end):
        magnitude_spec[i] = magnitude_spec[i] if magnitude_spec[i] > WHITE_NOISE_THRESH*avg_energy_per_freq else 0

    # interpolate spectrum
    mag_spec_ipol = np.interp(np.arange(0, len(magnitude_spec), 1/NUM_HPS), np.arange(0, len(magnitude_spec)),
                              magnitude_spec)
    mag_spec_ipol = mag_spec_ipol / np.linalg.norm(mag_spec_ipol, ord=2) #normalize it

    hps_spec = copy.deepcopy(mag_spec_ipol)

    # calculate the HPS
    for i in range(NUM_HPS):
      tmp_hps_spec = np.multiply(hps_spec[:int(np.ceil(len(mag_spec_ipol)/(i+1)))], mag_spec_ipol[::(i+1)])
      if not any(tmp_hps_spec):
        break
      hps_spec = tmp_hps_spec

    max_ind = np.argmax(hps_spec)
    if (max_ind * (SAMPLE_FREQ/WINDOW_SIZE) / NUM_HPS <120):
      max_freq = 0
      figureOutCallback()
      previousNoteBuffer = list()
      sustainedCounter = 0
      return


    if previousNoteBuffer == list() and sustainedCounter < skipFirstNotes:
        sustainedCounter += 1
        max_freq = 0
        figureOutCallback()
        return
    previousNoteBuffer.append(max_ind * (SAMPLE_FREQ/WINDOW_SIZE) / NUM_HPS)
    if (len(previousNoteBuffer) > previousNoteBufferSize):
        previousNoteBuffer.pop(0)


    noteBufferCheck = True
    for i in range(len(previousNoteBuffer)-1):
        diffrence = abs(previousNoteBuffer[i] - previousNoteBuffer[i + 1])
        print (diffrence)
        if diffrence > 2 :
            noteBufferCheck = False
          
    print (noteBufferCheck)
    if (noteBufferCheck):
      max_freq = max_ind * (SAMPLE_FREQ/WINDOW_SIZE) / NUM_HPS
      currentSustainedNote = max_freq
    else:
      #make max_freq the number that is the highest value in the buffer
      max_freq = max(previousNoteBuffer)

    print (previousNoteBuffer)
    
    
    if (max_freq == 0):
        figureOutCallback()
        return
    

    closest_note, closest_pitch = find_closest_note(max_freq)
    max_freq = round(max_freq, 1)
    closest_pitch = round(closest_pitch, 1)

    figureOutCallback()

    callback.noteBuffer.insert(0, closest_note) # note that this is a ringbuffer
    callback.noteBuffer.pop()

def startTuner(callbackOut, inputDevice = None):
    #clear the buffer


    global runningTuner
    runningTuner = True
    global OutsideCallback
    OutsideCallback = callbackOut
    with sd.InputStream(channels=1, callback=callback, blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
        while runningTuner:
            time.sleep(0.5)

def stopTuner():
    #stop the tuner in a way where it can be restarted
    global runningTuner
    runningTuner = False

    callback.window_samples = [0 for _ in range(WINDOW_SIZE)]
    callback.noteBuffer = ["1","2"]
    global max_freq
    max_freq = 0



def setConfig(key, value):
    global config
    config[key] = value
