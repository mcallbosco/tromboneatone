#Utility to turn your otamatone into a midi controller using the otomamidi.py script

import otamatroller
import time
from PyQt5 import QtWidgets

#config dictionary
config = {
    "otamatoneBottomFreq": 0,
    "otamatoneTopFreq": 0,
    "otamatoneMiddleFreq": 0,
}

#Global variables
current_freq = 0
tuning = False





def callback(freq):
    global current_freq
    current_freq = freq

def getFreq():
    otamatroller.startTuner(callback)
    while current_freq ==0:
        pass
    otamatroller.stopTuner()
    return current_freq

def spawnTuningWindow():
    #3 lablels with corisponding buttons to set the bottom, middle, and top notes
    #change the button text to show the frequency
    #save the values to the config dictionary

    #Implimentation using pyqt5
    #code goes here

    top_freq = 0
    middle_freq = 0
    bottom_freq = 0

    app = QtWidgets.QApplication([])
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()
    window.setLayout(layout)

    top_label = QtWidgets.QLabel("Top Note: " + str(top_freq))
    middle_label = QtWidgets.QLabel("Middle Note: " + str(middle_freq))
    bottom_label = QtWidgets.QLabel("Bottom Note: " + str(bottom_freq))

    top_button = QtWidgets.QPushButton("Set Top Note")
    middle_button = QtWidgets.QPushButton("Set Middle Note")
    bottom_button = QtWidgets.QPushButton("Set Bottom Note")

    def setTop():
        global top_freq
        top_label.setText("Play a note")
        QtWidgets.QApplication.processEvents()
        top_freq = getFreq()
        top_label.setText("Top Note: " + str(top_freq))
    def setMiddle():
        global middle_freq
        middle_label.setText("Play a note")
        middle_freq = getFreq()
        middle_label.setText("Middle Note: " + str(middle_freq))
    def setBottom():
        global bottom_freq
        bottom_label.setText("Play a note")
        bottom_freq = getFreq()
        bottom_label.setText("Bottom Note: " + str(bottom_freq))

    top_button.clicked.connect(setTop)
    middle_button.clicked.connect(setMiddle)
    bottom_button.clicked.connect(setBottom)

    layout.addWidget(top_label)
    layout.addWidget(top_button)
    layout.addWidget(middle_label)
    layout.addWidget(middle_button)
    layout.addWidget(bottom_label)
    layout.addWidget(bottom_button)

    

    window.show()
    app.exec_()
    
    

spawnTuningWindow()