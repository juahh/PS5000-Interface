import ctypes
import numpy as np
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import time

class picoConnection:
    def __init__ (self):
        self.channel = []
        self.chRange = []
        self.resolution =ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
        self.chandle = ctypes.c_int16()
        self.status = {}
        self.channels = ["A", "B", "C", "D"]
        self.bufferMin =[]
        self.bufferMax = [] 
        self.preTriggerSamples = 2500
        self.postTriggerSamples = 2500
        self.measuring = False
        self.ContinueMeasurement = True

        pass
    
    def makeConnection(self):
        self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, self.resolution)
        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:

            self.powerStatus = self.status["openunit"]

            if self.powerStatus == 286:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, self.powerStatus)
            elif self.powerStatus == 282:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, self.powerStatus)
            else:
                raise

            assert_pico_ok(self.status["changePowerSource"])

    def connectChannels(self, numberOfChannels):
        self.channel = []
        
        self.chRange = []
        self.coupling_type = []
        self.numberOfChannels = numberOfChannels
        self.channels = ["A", "B", "C", "D"]
        for index in range(0,numberOfChannels):
            self.channel.append( (ps.PS5000A_CHANNEL["PS5000A_CHANNEL_{0}".format(self.channels[index])]))

            # enabled = 1
            self.coupling_type.append(ps.PS5000A_COUPLING["PS5000A_DC"])
            self.chRange.append( ps.PS5000A_RANGE["PS5000A_20V"])
            # analogue offset = 0 V
            self.status["setCh{0}".format(self.channels[index])] = ps.ps5000aSetChannel(self.chandle, self.channel[index], 1, self.coupling_type[index], self.chRange[index], 0)
            assert_pico_ok(self.status["setCh{0}".format(self.channels[index])])
        
    

    def connect(self, numberOfChannels = 1):      
        self.makeConnection()
        #seuraavaksi channel asetukset omiin funktioihinsa. Mahdollisesti 4 kanavalle.
        self.connectChannels(numberOfChannels)

        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        self.maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))
        assert_pico_ok(self.status["maximumValue"])
        self.setTrigger(ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"],int(mV2adc(500,self.chRange[0], self.maxADC)),1000)
        
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        #print(self.maxSamples)
        self.returnData = np.zeros((self.numberOfChannels, self.maxSamples))

        
        self.clearDatabuffers()
        for index in range(0, self.numberOfChannels):
            self.setDatabuffer(index)
        self.setTimebase(8)
        self.overflow = ctypes.c_int16()
        # create converted type maxSamples
        self.cmaxSamples = ctypes.c_int32(self.maxSamples)

    def clearDatabuffers(self):
        self.bufferMax = []
        self.bufferMin = []
        del self.returnData
        

    def setDatabuffer(self, channelIndex):
        
        self.bufferMax.append( (ctypes.c_int16 * self.maxSamples)())
        self.bufferMin.append( (ctypes.c_int16 * self.maxSamples)()) # used for downsampling which isn't in the scope of this example
         # used for downsampling which isn't in the scope of this example

        # Set data buffer location for data collection from channel A
        # handle = chandle
        self.source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_{0}".format(self.channels[channelIndex])]
        # pointer to buffer max = ctypes.byref(bufferAMax)
        # pointer to buffer min = ctypes.byref(bufferAMin)
        # buffer length = maxSamples
        # segment index = 0
        # ratio mode = PS5000A_RATIO_MODE_NONE = 0
        self.status["setDataBuffers{0}".format(self.channels[channelIndex])] = ps.ps5000aSetDataBuffers(self.chandle, self.source, ctypes.byref(self.bufferMax[channelIndex]), ctypes.byref(self.bufferMin[channelIndex]), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffers{0}".format(self.channels[channelIndex])])
        self.returnData = np.zeros((self.numberOfChannels, self.maxSamples))


    def runTestBlock(self):
        self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, None, 0, None, None)
        assert_pico_ok(self.status["runBlock"])

        # Check for data collection to finish using ps5000aIsReady
        self.ready = ctypes.c_int16(0)
        self.check = ctypes.c_int16(0)
        while self.ready.value == self.check.value:
            self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(self.ready))
        # create overflow loaction
        
        # Retried data from scope to buffers assigned above
        # handle = chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(cmaxSamples)
        # downsample ratio = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))
        self.status["getValues"] = ps.ps5000aGetValues(self.chandle, 0, ctypes.byref(self.cmaxSamples), 0, 0, 0, ctypes.byref(self.overflow))
        assert_pico_ok(self.status["getValues"])
        for index in range(0, self.numberOfChannels):
            self.returnData[index,:] = adc2mV( self.bufferMax[index], self.chRange[index], self.maxADC)
       
        self.time = np.linspace(0, (self.cmaxSamples.value) * self.timeIntervalns.value, self.cmaxSamples.value)
        return self.returnData, self.time
           
    def printAll(self):
        print("chandle: ",self.chandle)
        print("channelA: ",self.channel)
        
        print("chRange: ",self.chRange)
       
        print("coupling_type: ",self.coupling_type)
        print("maxADC: ",self.maxADC)
        print("maxSamples: ",self.maxSamples)
        print("postTriggerSamples: ",self.postTriggerSamples)
        print("preTriggerSamples: ",self.preTriggerSamples)
        print("Resolution: ",self.resolution)
        print("returnedMaxSamples: ",self.returnedMaxSamples)
        print("source: ",self.source)
        print("status: ",self.status)
        print("treshold: ",self.threshold)
        print("timebase: ",self.timebase)
        print("timeIntervalns: ",self.timeIntervalns)

    def disconnect(self):
        self.status["stop"] = ps.ps5000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])

        # Closes the unit
        # Handle = chandle
        self.status["close"] = ps.ps5000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])
        print("\n----------------- \nConnection closed \n-----------------")

    def setResolution(self, reso):
        if(reso >= 8 and reso <= 16):
            command = "PS5000A_DR_{0}BIT".format(reso)
        self.resolution =ps.PS5000A_DEVICE_RESOLUTION[command]
        self.status["resolution"] = ps.ps5000aSetDeviceResolution(self.chandle, self.resolution)
       # self.disconnect()
       # self.connect(self.numberOfChannels)
    
    def setSamples(self, pre, post):
        self.preTriggerSamples = pre
        self.postTriggerSamples = post
        self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
        self.cmaxSamples = ctypes.c_int32(self.maxSamples)
       # self.disconnect()
       # self.connect(self.numberOfChannels)
        self.setTimebase(self.timebase)


    def setTimebase(self, index):
        self.clearDatabuffers()
        for jindex in range(0, self.numberOfChannels):
            self.setDatabuffer(jindex)
        # Get timebase information
        # handle = chandle
        self.timebase = index
        # noSamples = maxSamples
        # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
        # pointer to maxSamples = ctypes.byref(returnedMaxSamples)
        # segment index = 0
        self.timeIntervalns = ctypes.c_float()
        self.returnedMaxSamples = ctypes.c_int32()
        self.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.chandle, self.timebase, self.maxSamples, ctypes.byref(self.timeIntervalns), ctypes.byref(self.returnedMaxSamples), 0)
        assert_pico_ok(self.status["getTimebase2"])
    
    def setTrigger(self, source, threshold, autotrig):
        # Set up single trigger
        # handle = chandle
        # enabled = 1
        #self.source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        #self.threshold = int(mV2adc(500,self.chARange, self.maxADC))
        # direction = PS5000A_RISING = 2
        # delay = 0 s
        # auto Trigger = 1000 ms
        self.autotrig = autotrig
        self.source = source
        self.threshold = threshold
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, 1, self.source, self.threshold, 2, 0, self.autotrig)
        assert_pico_ok(self.status["trigger"])
        # Set number of pre and post trigger samples to be collected
    
    def setTriggervoltage(self,threshold):
        self.threshold = threshold
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, 1, self.source, self.threshold, 2, 0, self.autotrig)
        assert_pico_ok(self.status["trigger"])
    
    def setTriggerSource(self,source):
        self.source = source
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, 1, self.source, self.threshold, 2, 0, self.autotrig)
        assert_pico_ok(self.status["trigger"])

    def setTriggerAutotrig(self,autotrig):
        self.autotrig = autotrig
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, 1, self.source, self.threshold, 2, 0, self.autotrig)
        assert_pico_ok(self.status["trigger"])
    





        