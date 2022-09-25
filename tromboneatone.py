'''
Guitar tuner script based on the Harmonic Product Spectrum (HPS)

MIT License
Copyright (c) 2021 chciken

Adapted into tromboneatone, a program to use your otamatone as a controller for Trombone Champ by Mcall
'''

import copy
import os
import numpy as np
import scipy.fftpack
import sounddevice as sd
import time
import mouse
import math

# General settings that can be changed by the user
SAMPLE_FREQ = 20000 # sample frequency in Hz
WINDOW_SIZE = 600 # window size of the DFT in samples
WINDOW_STEP = 300 #s step size of window
NUM_HPS = 10 # max number of harmonic product spectrums
POWER_THRESH = 1e-6 # tuning is activated if the signal power exceeds this threshold
CONCERT_PITCH = 440 # defining a1
WHITE_NOISE_THRESH = 0.2 # everything under WHITE_NOISE_THRESH*avg_energy_per_freq is cut off

WINDOW_T_LEN = WINDOW_SIZE / SAMPLE_FREQ # length of the window in seconds
SAMPLE_T_LENGTH = 1 / SAMPLE_FREQ # length between two samples in seconds
DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE # frequency step width of the interpolated DFT
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]


#USER CONFIG STUFF

mouseActive = True   #if true, mouse will move to the note
truePitch = False    #If true, the mouse will only respond to pitches that are within the range of the game's notes. You can change the octive it uses by changing the value for the middleOctive var
#If false, the mouse will respond and move according to pitches either defined by tuning or default values.
invertNotTruePitch = False    #Inverts the mouse movement when truePitch mode is not enabled.
tuneAtStart = True            #When the program starts there will be tuning prompts when truePitch is not enabled
middleTune = True             #When truePitch is enabled, the program will tune to the middle note of the note range to improve accuracy

#IGNORE IF USING TUNING. Values used if tuning is not enabled!
otamatoneBottomFreq = 170
otamatoneTopFreq = 860
otamatoneMiddleFreq = 290




tuneAtStart = tuneAtStart and not truePitch
tuning = tuneAtStart
tuningState = 0
tuningStateFirstPrint = True
tuningValues = []
toneStopped = False





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



def tuningfunc(frequency):
  global tuningStateFirstPrint
  if (tuningState == 0):
    if (tuningStateFirstPrint):
      print("Tuning... Play the Highest Note")
      tuningStateFirstPrint = False
  elif (tuningState == 1):
    if (tuningStateFirstPrint):
      print("Tuning... Play the Lowest Note")
      tuningStateFirstPrint = False
  elif (tuningState == 2 and middleTune):
    if (tuningStateFirstPrint):
      print("Tuning... Play the Middle Note")
      tuningStateFirstPrint = False
  global toneStopped
  toneStopped = True

HANN_WINDOW = np.hanning(WINDOW_SIZE)
def callback(indata, frames, time, status):
  global otamatoneBottomFreq
  global otamatoneTopFreq
  global otamatoneMiddleFreq
  global tuning

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
      mouse.release()
      if not tuning:
        'print("Closest note: ...")'
      else:
        tuningfunc(0)
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
    max_freq = max_ind * (SAMPLE_FREQ/WINDOW_SIZE) / NUM_HPS
    

    closest_note, closest_pitch = find_closest_note(max_freq)
    max_freq = round(max_freq, 1)
    closest_pitch = round(closest_pitch, 1)

    callback.noteBuffer.insert(0, closest_note) # note that this is a ringbuffer
    callback.noteBuffer.pop()


    #get screen width and height
    screenWidth = 1920
    screenHeight = 1080
    cFreqTable= [33,65,131,262,523,1047,2093]
    middleOctive = 4
    freqLowerRange = cFreqTable[middleOctive-1]
    freqMidRange = cFreqTable[middleOctive]
    freqUpperRange = cFreqTable[middleOctive+1]
    bottomMarginSize = 135
    bottomMarginSizeC = 184
    topMarginSize = 140
    topMarginSizeC = 163
    gameHeightInputSizeC = screenHeight - bottomMarginSizeC - topMarginSizeC
    gameHeightInputSize = screenHeight - bottomMarginSize - topMarginSize



    if tuning:
      global tuningState
      global toneStopped
      global tuningValues
      global tuningStateFirstPrint
      if (toneStopped):
        if (max_freq != 0 and len(tuningValues) < 6):
          tuningValues.append(max_freq)
        else:
          if (len(tuningValues) == 6):
            "check to see if the tuning values are within a range of 5 of each other"
            if (tuningValues[0] > tuningValues[1] - 5 and tuningValues[0] < tuningValues[1] + 5 and tuningValues[1] > tuningValues[2] - 5 and tuningValues[1] < tuningValues[2] + 5 and tuningValues[2] > tuningValues[3] - 5 and tuningValues[2] < tuningValues[3] + 5 and tuningValues[3] > tuningValues[4] - 5 and tuningValues[3] < tuningValues[4] + 5 and tuningValues[4] > tuningValues[5] - 5 and tuningValues[4] < tuningValues[5] + 5):
              "get the average of the tuning values"
              if (tuningState == 0):
                otamatoneTopFreq = sum(tuningValues[0:6])/6
                toneStopped = False
                tuningStateFirstPrint = True
                tuningState = 1
                tuningValues = []
                print("Top freq: " + str(otamatoneTopFreq))
              elif (tuningState == 1):
                otamatoneBottomFreq = sum(tuningValues[0:6])/6
                toneStopped = False
                tuningStateFirstPrint = True
                global middleTune
                tuningValues = []
                print("Bottom freq: " + str(otamatoneBottomFreq))
                if (middleTune):
                  tuningState = 2
                else:
                  print("Tuning Complete!!!")
                  tuning=False  
              elif (tuningState == 2):
                otamatoneMiddleFreq = sum(tuningValues[0:6])/6
                tuningState = 3
                tuningStateFirstPrint = True
                print("Middle freq: " + str(otamatoneMiddleFreq))

              else: 
                print("Tuning Complete!!!")
                tuning=False    
            else:
              tuningValues = []
          
      
      

    else:
      if mouseActive and truePitch and mouseActive:
          if max_freq < freqUpperRange +20 and max_freq > freqLowerRange - 20:
              if max_freq > freqMidRange:
                  pitchPersentage = (math.log(max_freq) - math.log(freqMidRange)) / (math.log(freqUpperRange) - math.log(freqMidRange))
                  pitchPersentage = pitchPersentage * 0.5
                  pitchPersentage = pitchPersentage + 0.5
                  pitchPersentage = 1 - pitchPersentage
              else:
                  pitchPersentage = (math.log(max_freq) - math.log(freqLowerRange)) / (math.log(freqMidRange) - math.log(freqLowerRange))
                  pitchPersentage = pitchPersentage * 0.5
                  pitchPersentage = 1 - pitchPersentage
                  
              """ Less Accurate
              pitchPersentage = (math.log(67,max_freq) - math.log(67,freqLowerRange)) / (math.log(67,freqUpperRange) - math.log(67,freqLowerRange))
              pitchPersentage = 1 - pitchPersentage
              print (pitchPersentage)"""
              mousepointposH = int(gameHeightInputSizeC * pitchPersentage) + topMarginSizeC
              mouse.move(screenWidth/2+100, mousepointposH, absolute=True)
              mouse.press()
              
          else:
              mouse.release()


      if mouseActive and truePitch == False:
        if max_freq < otamatoneTopFreq+20 and max_freq > otamatoneBottomFreq-20:
          if (middleTune):
            if max_freq > otamatoneMiddleFreq:
              print("upper range math", str(max_freq), str(otamatoneMiddleFreq), str(otamatoneTopFreq))

              pitchPersentage = (math.log(max_freq) - math.log(otamatoneMiddleFreq)) / (math.log(otamatoneTopFreq) - math.log(otamatoneMiddleFreq))
              pitchPersentage = pitchPersentage * 0.5
              pitchPersentage = pitchPersentage + 0.5
            else:
              print("lower range math")
              pitchPersentage = (math.log(max_freq) - math.log(otamatoneBottomFreq)) / (math.log(otamatoneMiddleFreq) - math.log(otamatoneBottomFreq))
              pitchPersentage = pitchPersentage * 0.5
          else :
            pitchPersentage = (math.log(math.log(max_freq)) - math.log(math.log(otamatoneBottomFreq))) / (math.log(math.log(otamatoneTopFreq)) - math.log(math.log(otamatoneBottomFreq)))
          #pitchPersentage = (max_freq - otamatoneBottomFreq) / (otamatoneTopFreq - otamatoneBottomFreq)
          print(pitchPersentage)
          if invertNotTruePitch:
            pitchPersentage = 1 - pitchPersentage
          print (pitchPersentage)
          mousepointposH = int(gameHeightInputSize * pitchPersentage) + topMarginSize
          mouse.move(screenWidth/2+100, mousepointposH, absolute=True)
          mouse.press()


      if callback.noteBuffer.count(callback.noteBuffer[0]) == len(callback.noteBuffer):
        print(f"Closest note: {closest_note} {max_freq}/{closest_pitch}")

try:
  print("Starting HPS guitar tuner...")
  with sd.InputStream(channels=1, callback=callback, blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
    while True:
      time.sleep(0.5)
except Exception as exc:
  print(str(exc))
