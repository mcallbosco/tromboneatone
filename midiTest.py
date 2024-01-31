import time
import rtmidi

midiout = rtmidi.MidiOut()
available_ports = midiout.get_ports()

#pick a port
print(available_ports)
port = input("Enter port number: ")
port = int(port)
midiout.open_port(port)


with midiout:
    note_on = [0x90, 60, 112] # channel 1, middle C, velocity 112
    note_off = [0x80, 60, 0]
    midiout.send_message(note_on)
    time.sleep(0.5)
    midiout.send_message(note_off)
    time.sleep(0.1)

del midiout