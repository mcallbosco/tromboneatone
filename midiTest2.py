import mido
import time

# pick a midi device. Print the list of available devices with numbers to pick
print(mido.get_output_names())
port = input("Enter port number: ")
port = int(port)
virtual_device_name = mido.get_output_names()[port]


# Create a MIDI output port using mido backend
virtual_port = mido.open_output(virtual_device_name)

def send_midi_message(note, velocity, channel=0):
    # Create a Note On message
    message = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
    
    # Send the MIDI message
    virtual_port.send(message)

    # Optional: Add a delay to simulate sustained notes
    time.sleep(0.5)

    # Create a Note Off message
    message = mido.Message('note_off', note=note, velocity=0, channel=channel)

    # Send the MIDI message
    virtual_port.send(message)

# Example: Send a C4 note with velocity 64 on channel 0
send_midi_message(note=60, velocity=64, channel=0)

# Close the virtual MIDI port when done
virtual_port.close()
