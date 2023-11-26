#!/usr/bin/env python3
"""
Govee Local Network Polyglot v3 node server
Copyright (C) 2023 Matt Burke

MIT License
"""
import udi_interface
import sys
import time
import string
import re

# Standard Library
from typing import Optional, Any, TYPE_CHECKING

import math,datetime,urllib.parse,http.client,base64

from nodes import govee_local_device

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom
ISY = udi_interface.ISY

'''
Controller
'''
class Controller(udi_interface.Node):
    id = 'goveeLocalController'
    drivers = [
            {'driver': 'ST', 'value': -1, 'uom': 2},
            {'driver': 'GV0', 'value': -1, 'uom': 56},
            {'driver': 'GPV', 'value': -1, 'uom': 56, 'text': 'NodeServer STARTING'}
            ]

    def __init__(self, polyglot, parent, address, name):
        super(Controller, self).__init__(polyglot, parent, address, name)
        
        # set a flag to short circuit setDriver() until the node has been fully
        # setup in the Polyglot DB and the ISY (as indicated by START event)
        self._initialized: bool = False

        self._fullyCreated: bool = False
        
        self.poly = polyglot
        self.n_queue = []

        self.Parameters = Custom(polyglot, 'customparams')

        self.ISY = ISY(self.poly)
        self.parent = parent

        # subscribe to the events we want
        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        polyglot.subscribe(polyglot.STOP, self.stop)
        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.ADDNODEDONE, self.node_queue)
        polyglot.subscribe(polyglot.POLL, self.poll)

        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self)

    '''
    node_queue() and wait_for_node_event() create a simple way to wait
    for a node to be created.  The nodeAdd() API call is asynchronous and
    will return before the node is fully created. Using this, we can wait
    until it is fully created before we try to use it.
    '''
    def node_queue(self, data):
        if self.address == data['address']:
            self.n_queue.append(data['address'])
            self._fullyCreated = True
            self.setDriver('ST', -1, True, True)   
            self.setDriver('GV0', -1, True, True)   
            self.setDriver('GPV', -1, True, True)        
            self.pushTextToDriver('GPV','NodeServer Running')

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    '''
    Read the user entered custom parameters.  Here is where the user will
    configure the number of child nodes that they want created.
    '''
    def parameterHandler(self, params):
        self.Parameters.load(params)
        
        validIP_Addresses = False
        validDevice_Names = False
        ioxErrorMessage = ''

        if self.Parameters['IP_Addresses'] is not None:
            if len(self.Parameters['IP_Addresses']) > 6:
                validIP_Addresses = True
            else:
                LOGGER.warning('\n\tCONFIGURATION INCOMPLETE OR INVALID: Invalid values for IP_Addresses parameter.')
                ioxErrorMessage = 'INVALID IP_Addresses Parameter'
        else:
            LOGGER.warning('\n\tCONFIGURATION MISSING: Missing IP_Addresses parameter.')
            ioxErrorMessage = 'MISSING IP_Addresses Parameter'

        if self.Parameters['Device_Names'] is not None:
            if len(self.Parameters['Device_Names']) > 0:
                validDevice_Names = True
            else:
                LOGGER.warning('\n\tCONFIGURATION INCOMPLETE OR INVALID: Invalid values for Device_Names parameter.')
                if len(ioxErrorMessage) > 0:
                    ioxErroMessage = ioxErrorMessage + '; '
                ioxErrorMessage = ioxErrorMessage + 'INVALID Device_Names Parameter'
        else:
            LOGGER.warning('\n\tCONFIGURATION MISSING: Missing Device_Names parameter.')
            if len(ioxErrorMessage) > 0:
                ioxErroMessage = ioxErrorMessage + '; '
            ioxErrorMessage = ioxErrorMessage + 'MISSING Device_Names Parameter'

        
        if validIP_Addresses and validDevice_Names:
            self.createChildren()
            self.poly.Notices.clear()
            self.pg3ParameterErrors = False
        else:
            if not(validIP_Addresses):
                self.poly.Notices['IP_Addresses'] = 'Please populate the IP_Addresses parameter.'
            if not(validDevice_Names):
                self.poly.Notices['Device_Names'] = 'Please populate the Device_Names parameter.'
            
            self.pushTextToDriver('GPV',ioxErrorMessage)

    '''
    This is called when the node is added to the interface module. It is
    run in a separate thread.  This is only run once so you should do any
    setup that needs to be run initially.  For example, if you need to
    start a thread to monitor device status, do it here.

    Here we load the custom parameter configuration document and push
    the profiles to the ISY.
    '''
    def start(self):
        # set the initlized flag to allow setDriver to work
        self._initialized = True
        
        self.poly.setCustomParamsDoc()
        # Not necessary to call this since profile_version is used from server.json
        self.poly.updateProfile()


    '''
    This is where the real work happens.  When we get a shortPoll, increment the
    count, report the current count in GV0 and the current count multiplied by
    the user defined value in GV1. Then display a notice on the dashboard.
    '''
    def poll(self, polltype):
        LOGGER.warning('\n\tPOLLTYPE: ' + polltype + ' received by ' + self.address + '.\n')
        if 'shortPoll' in polltype:
            nowEpoch = int(time.time())
            nowDT = datetime.datetime.fromtimestamp(nowEpoch)
            self.pushTextToDriver('GPV',"Last Short Poll Date / Time: " + nowDT.strftime("%m/%d/%Y %I:%M:%S %p"))
        
    '''
    Create the children nodes.  Since this will be called anytime the
    user changes the number of nodes and the new number may be less
    than the previous number, we need to make sure we create the right
    number of nodes.  Because this is just a simple example, we'll first
    delete any existing nodes then create the number requested.
    '''
    def createChildren(self):

        ipAddresses = self.Parameters['IP_Addresses']
        deviceNames = self.Parameters['Device_Names']

        listOfIPAddresses = ipAddresses.split(";")
        listOfDeviceNames = deviceNames.split(";")
        how_many = len(listOfIPAddresses)

        LOGGER.warning('\n\tCreating {} Govee Locally Controlled Devices...'.format(how_many))
        for i in range(0, how_many):
            address = 'gvld_{}'.format(i)
            current_IPaddress = listOfIPAddresses[i]
            current_DeviceName = listOfDeviceNames[i]
            
            try:
                LOGGER.warning('\n\t\t Device # {}: {} at {}...'.format(how_many,current_DeviceName,current_IPaddress))
                node = govee_local_device.GoveeLocalDevice(self.poly, self.address, address, current_DeviceName, current_IPaddress)
                self.poly.addNode(node)
                self.wait_for_node_done()
            except Exception as e:
                LOGGER.error('Failed to create {}: {}'.format(current_DeviceName, e))

        self.setDriver('GV0', how_many, True, True)

    '''
    Change all the child node status drivers to unknown
    '''
    def stop(self):

        nodes = self.poly.getNodes()
        for node in nodes:
            if node != 'controller':   # but not the controller node
                nodes[node].setDriver('ST', 101, True, True)

        self.poly.stop()

    '''
    Handling for <text /> attribute.
    Note that to be reported to IoX, the value has to change; this is why we flip from 0 to 1 or 1 to 0.
    -1 is reserved for initializing.
    '''
    def pushTextToDriver(self,driver,stringToPublish):
        if not(self._fullyCreated) or not(self._initialized):
            LOGGER.warning("\n\tPUSHING REPORT ERROR - self._fullyCreated = " + format(self._fullyCreated) + "; self._initialized = " + format(self._initialized) + ".\n")
            return
        stringToPublish = stringToPublish.replace('.','')
        if len(str(self.getDriver(driver))) <= 0:
            LOGGER.warning("\n\tPUSHING REPORT ERROR - a (correct) Driver was not passed for '" + self.address + "' trying to update driver " + driver + ".\n")
            return
            
        currentValue = int(self.getDriver(driver))
        newValue = -1
        encodedStringToPublish = urllib.parse.quote(stringToPublish, safe='')

        if currentValue != 1:
            newValue = 1
            message = {
                'set': [{
                    'address': self.address,
                    'driver': driver,
                    'value': 1,
                    'uom': 56,
                    'text': encodedStringToPublish
                }]
            }
            
        else:
            newValue = 0
            message = {
                'set': [{
                    'address': self.address,
                    'driver': driver,
                    'value': 0,
                    'uom': 56,
                    'text': encodedStringToPublish
                }]
            }

        self.setDriver(driver, newValue, False)

        if 'isPG3x' in self.poly.pg3init and self.poly.pg3init['isPG3x'] is True:
            #PG3x can use this, but PG3 doesn't have the necessary 'text' handling within message, set above, so we have the 'else' below
            LOGGER.debug("\n\tPUSHING REPORT TO '" + self.address + "' for driver " + driver + ", with PG3x via self.poly.send('" + encodedStringToPublish + "','status') with a value of '" + str(newValue) + "'.\n")
            self.poly.send(message, 'status')
        elif not(self.ISY.unauthorized):
            userpassword = self.ISY._isy_user + ":" + self.ISY._isy_pass
            userpasswordAsBytes = userpassword.encode("ascii")
            userpasswordAsBase64Bytes = base64.b64encode(userpasswordAsBytes)
            userpasswordAsBase64String = userpasswordAsBase64Bytes.decode("ascii")

            if len(self.ISY._isy_ip) > 0 and len(userpasswordAsBase64String) > 3:
                localConnection = http.client.HTTPConnection(self.ISY._isy_ip, self.ISY._isy_port)
                payload = ''
                headers = {
                    "Authorization": "Basic " + userpasswordAsBase64String
                }
                
                LOGGER.debug("\n\tPUSHING REPORT TO '" + self.address + "' for driver " + driver + ", with PG3 via " + self.ISY._isy_ip + ":" + str(self.ISY._isy_port) + ", with a value of " + str(newValue) + ", and a text attribute (encoded) of '" + encodedStringToPublish + "'.\n")
        
                prefixN = str(self.poly.profileNum)
                if len(prefixN) < 2:
                    prefixN = 'n00' + prefixN + '_'
                elif len(prefixN) < 3:
                    prefixN = 'n0' + prefixN + '_'
                
                suffixURL = '/rest/ns/' + str(self.poly.profileNum) + '/nodes/' + prefixN + self.address + '/report/status/' + driver + '/' + str(newValue) + '/56/text/' + encodedStringToPublish
                
                LOGGER.debug("\n\t\tPUSHING REPORT Details - this is the 'suffixURL':\n\t\t\t" + suffixURL + "\n")

                try:
                    localConnection.request("GET", suffixURL, payload, headers)
                    localResponse = localConnection.getresponse()

                    localResponseData = localResponse.read()
                    localResponseData = localResponseData.decode("utf-8")
                
                    if '<status>200</status>' not in localResponseData:
                        LOGGER.warning("\n\t\tPUSHING REPORT ERROR on '" + self.address + "' for driver " + driver + ": RESPONSE from report was not '<status>200</status>' as expected:\n\t\t\t" + localResponseData + "\n")
                    else:
                        LOGGER.debug("\n\t\tPUSHING REPORT on '" + self.address + "' for driver " + driver + ": RESPONSE from report:\n\t\t\t" + localResponseData + "\n")
                except http.client.HTTPException:
                    LOGGER.error("\n\t\tPUSHING REPORT ERROR on '" + self.address + "' for driver " + driver + " had an ERROR.\n")
                except:
                    LOGGER.error("\n\t\tPUSHING REPORT ERROR on '" + self.address + "' for driver " + driver + " had an ERROR.\n")
                finally:
                    localConnection.close()  
        else:
            LOGGER.warning("\n\t\PUSHING REPORT ERROR on '" + self.address + "' for driver " + driver + ": looks like this is a PG3 install but the ISY authorization state seems to currently be 'Unauthorized': 'True'.\n")


    '''
    Just to show how commands are implemented. The commands here need to
    match what is in the nodedef profile file. 
    '''
    def noop(self):
        LOGGER.info('Discover not implemented')

    commands = {'DISCOVER': noop}
