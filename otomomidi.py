import rtmidi
import mido
import time
import otomotroller
import numpy as np
from time import sleep
# pick a midi device. Print the list of available devices with numbers to pick
playingNote = False

prevNote = ""

def callback(freq):
    global playingNote
    global prevNote
    if (freq == 0):
        if (playingNote):
            send_midi_message(prevNote, 0)
            playingNote = False
            prevNote    = ""

        return
    global current_freq
    current_freq = freq
    current_note, current_pitch , midinote= find_closest_note(freq)
    sendSustanedBasedOnIfNoteChanged(midinote)
    print (freq)


CONCERT_PITCH = 440
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
  midiNote = i + 69

  return closest_note, closest_pitch, midiNote

def send_midi_message(note, velocity, channel=0):
    # Create a Note On message
    message = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
    
    # Send the MIDI message
    virtual_port.send(message)



def sendSustanedBasedOnIfNoteChanged(note):
    global playingNote
    playingNote = True
    global prevNote
    if (note != prevNote):
        message = mido.Message('note_off', note=note, velocity=0, channel=0)
        virtual_port.send(message)
        send_midi_message(note, 127)
        prevNote = note
    prevNote = note  



print(mido.get_output_names())
port = input("Enter port number: ")
port = int(port)
virtual_device_name = mido.get_output_names()[port]
# Create a MIDI output port using mido backend
virtual_port = mido.open_output(virtual_device_name)

import threading
otamatoneThread = threading.Thread(target=otomotroller.startTuner, args=(callback,))
otamatoneThread.start()


while True:
    sleep(1)