from picoConnection import picoConnection
import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import time
import threading
import scipy.io as sio
import serial

class terminalInterface():

    def __init__(self):
        self.running = False
        self.pico = picoConnection()
        self.scanRunning = False
        self.changingValues = False
        self.newCommand = False
        self.newData = False
        self.notQuit = True
        self.noNewCommandNow = False
        self.numberOfSignals = 100
        self.fileName = "defaultFileName"
        self.arduinport = 'COM3'
         
    def askForCommand(self):
        while(self.notQuit):
            time.sleep(1)
            if(self.newCommand == False):
                if(self.noNewCommandNow):
                    break
                self.command = input("Please input a command: ")
                self.newCommand = True

    def setSaveType(self, filetype):
        if(filetype == 'mat'):
            self.saveType = 'mat'
        elif(filetype == 'dat'):
            self.saveType = 'dat'
        
        else:
            print("Filetype not {0} supported: please choose from mat and dat.".format(filetype))
    
    def start(self):
        
        self.running = True
        print("This is a program to setup and measure a 5000 series Picoscope \n ")
        self.printCommands()
        self.y = threading.Thread(target=self.askForCommand)
        self.y.start()
        plt.axis('auto')
        plt.ion()
        plt.show()
        while(self.running):
            if(self.newCommand):
                self.newCommand = False
                self.handleCommand(self.command)
            
            if(self.newData):
                self.newData = False
                plt.plot(self.t, np.squeeze(self.data))
                plt.draw()
                plt.pause(0.01)
                plt.clf()
                

                
                time.sleep(0.1)
                      

    def handleCommand(self,command):
        try:
            commandSplit = command.split(" ")
            #print(commandSplit)
            print(commandSplit[0].casefold())
            com = commandSplit[0].casefold()
            if(com == "connect"):
                if(len(commandSplit) > 1):
                    self.pico.connect(int(commandSplit[1]))
                    self.numberOfChannels = int(commandSplit[1])
                else:
                    self.pico.connect()
                    self.numberOfChannels = 1

            elif(com == ("disconnect")):
                self.pico.disconnect()
            elif(com== ("run")):
                if(self.scanRunning == False):
                    self.scanRunning = True
                    self.x = threading.Thread(target=self.startTestScan)
                    self.x.start()
                    #self.startTestScan()
                #self.startTestScan()
            elif(com == ("stop")):
                self.stopTestScan()
            elif(com == "scan"):
                self.noNewCommandNow = True
                self.z = threading.Thread(target=self.actualScan)
                self.z.start()
                
                #self.actualScan()
            elif(com ==("quit")):
                self.quitInterface()
            elif(com == "settimebase" ):
                self.changingValues = True
                time.sleep(0.1)
                self.pico.setTimebase(int(commandSplit[1]))
                self.changingValues = False                
            elif(com == "setautotrigger"):
                self.changingValues = True
                time.sleep(0.1)
                self.pico.setTriggerAutotrig(int(commandSplit[1]))
                self.changingValues = False
            elif(com== "setresolution"):
                self.changingValues = True
                time.sleep(0.1)
                self.pico.setResolution(int(commandSplit[1]))
                self.changingValues = False
            elif(com == "setsamples"):
                self.setSamples(int(commandSplit[1]),int(commandSplit[2]))

            elif(com == "commands"):
                self.printCommands()
            elif(com == "setsavetype"):
                self.setSaveType(commandSplit[1])
            else:
                print("Command not recognized, please check the list of commands")
        except Exception as e:
            print(e)
        
    def startTestScan(self):
        self.data1 = np.zeros((self.numberOfChannels,self.pico.maxSamples))
        if(self.numberOfChannels > 1):
            print("Please note that only the channel 1 is plotted in this mode.")
        while(self.scanRunning):
            time.sleep(0.1)
            try:
                if(self.changingValues == False):
                    self.data1,self.t = self.pico.runTestBlock()
                    self.data = self.data1[0,:]
                    #print((np.shape(self.data)))
                    self.newData = True
                    time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(e)
                del self.data
                del self.data1
                del self.t
           
            
    def actualScan(self):
        self.numberOfSignals = int(input("How many steps?: "))
        filetype = input("Please enter file type (dat or mat ): ")
        filename = input("Please enter filename:______{0}: ".format(filetype))
        self.scanRunning = True
       
        if(filetype == 'dat'):
            f = open(filename + filetype,"a")
            
            for index in range(0,self.numberOfSignals):
                print("{0}/{1}".format(index,self.numberOfSignals))
                data,t = self.pico.runTestBlock()
                f.write(data)
                if(self.scanRunning == False):
                    print("Scan stopped.  The time-vector is saved to the end of the data file.")
                    break
            if(index == self.numberOfSignals- 1):
                print("Scan finished. The time-vector is saved to the end of the data file.")
            f.write(t)
            f.close()


        elif(filetype == 'mat'):
            if(self.numberOfChannels == 1):
                data = np.zeros((self.pico.maxSamples, self.numberOfSignals))
            else:
                data = np.zeros((self.numberOfChannels,self.pico.maxSamples, self.numberOfSignals))
           
            for index in range(0, self.numberOfSignals):
                print("{0}/{1}".format(index,self.numberOfSignals))
                if(self.numberOfChannels == 1):
                    data[:,index],t = self.pico.runTestBlock()
                else:
                   data[:,:,index],t = self.pico.runTestBlock()

                if(self.scanRunning == False):
                    print("Scan stopped. Saving")
                    break
            if(index == self.numberOfSignals- 1):
                print("Scan finished. Saving")
            sio.savemat(filename+'.mat', {'Data':data, 't':t})


        else:
           print("Filetype not {0} supported: please choose from mat or dat.".format(filetype))
        
    def setSamples(self,pre,post):
        self.changingValues = True
        time.sleep(0.1)
        self.pico.setSamples(pre,post)
        self.changingValues = False

    def stopTestScan(self):
        self.scanRunning = False
        #self.x._stop()
        print("Stopped")
    

    def quitInterface(self):
        command = input("Are you sure?")
        if(command == "" or command == "y" or command == "Y" or command == "yes"):
            print("Quitting")
            self.running = False
            self.notQuit = False
            self.x._delete
            self.y._delete
        else:
            pass
    def printCommands(self):
        print("- Connect [number of channels] - Creates a connection to the Picoscope with selected number of channels")
        print("- Disconnect - Disconnects the Picoscope")
        print("- Run - Starts measuring blocks and displaying their results. This is used to setup the oscilloscope parameters before actual scan")
        print("- SetTrigger [source] [treshold]")
        print("- Setsamples [preTrigger] [postTrigger] - This sets the pre- and postrigger samples. Total sample amount is the sum of these two.")
        print("- SetAutoTrigger [delay in ms] - sets the device")
        print("- SetTimebase [Value] - Sets the device timebase (1-8). Please check the resolution limitations of the timebase")
        print("- SetResolution [Value] - Sets the bit resolution of the device (8, 10, 12,14,15,16). Please check the timebase limitations of the resolution")
        print("- Scan [value] - Performs amount value of measurements and returns them as a (value x timePoints) - matrix")
        print("- Quit - exits the program")
        print("- Commands - Prints all commands")
def main():
    measurement = terminalInterface()
    measurement.start()
    
main()