#!/usr/bin/env python3
"""
Polyglot v3 node server Example 3
Copyright (C) 2021 Robert Paauwe

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

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

ISY = udi_interface.ISY

'''
Device node
'''
class GoveeLocalDevice(udi_interface.Node):
    id = 'govee_local_device'
    drivers = [
            {'driver': 'ST', 'value': 101, 'uom': 78},
            {'driver': 'OL', 'value': 101, 'uom': 78},
            {'driver': 'FREQ', 'value': -1, 'uom': 56},
            {'driver': 'PULSCNT', 'value': -1, 'uom': 56},
            {'driver': 'GV0', 'value': -1, 'uom': 26},
            {'driver': 'GV1', 'value': -1, 'uom': 56},
            {'driver': 'GV2', 'value': -1, 'uom': 56},
            {'driver': 'GV3', 'value': -1, 'uom': 56},
            {'driver': 'TIME', 'value': -1, 'uom': 56},
            {'driver': 'GPV', 'value': -1, 'uom': 56}
            ]

    def __init__(self, polyglot, parent, address, name, ipAddress):
        super(GoveeLocalDevice, self).__init__(polyglot, parent, address, name)
        
        # set a flag to short circuit setDriver() until the node has been fully
        # setup in the Polyglot DB and the ISY (as indicated by START event)
        self._initialized: bool = False

        self._fullyCreated: bool = False
        
        self.poly = polyglot
        self.ipAddress = ipAddress

        self.Parameters = Custom(polyglot, 'customparams')
        
        self.ISY = ISY(self.poly)
        self.parent = parent

        # subscribe to the events we want
        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.ADDNODEDONE, self.node_queue)

    '''
    node_queue() and wait_for_node_event() create a simple way to wait
    for a node to be created.  The nodeAdd() API call is asynchronous and
    will return before the node is fully created. Using this, we can wait
    until it is fully created before we try to use it.
    '''
    def node_queue(self, data):
        if self.address == data['address']:
            
            self._fullyCreated = True
        
            self.setDriver('ST', -1, True, True)
            self.setDriver('OL', -1, True, True)
            self.setDriver('FREQ', -1, True, True)
            self.setDriver('PULSCNT', -1, True, True)
            self.setDriver('GV0', -1, True, True)
            self.setDriver('GV1', -1, True, True)
            self.setDriver('GV2', -1, True, True)            
            self.setDriver('GV3', -1, True, True)

            self.setDriver('TIME', -1, True, True)
            self.setDriver('GPV', -1, True, True)
            
            self.pushTextToDriver('FREQ',self.ipAddress.replace('.','-'))

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    # called by the interface after the node data has been put in the Polyglot DB
    # and the node created/updated in the ISY
    def start(self):
        # set the initlized flag to allow setDriver to work
        self._initialized = True
        self.setDriver('GPV', -1, True, True)

    '''
    Read the user entered custom parameters.  
    '''
    def parameterHandler(self, params):
        self.Parameters.load(params)

    '''
    This is where the real work happens.  When we get a shortPoll, increment the
    count, report the current count in GV0 and the current count multiplied by
    the user defined value in GV1. Then display a notice on the dashboard.
    '''
    def poll(self, polltype):
        LOGGER.info('\n\tPOLLTYPE: ' + polltype + ' received by ' + self.address + '.\n')

    '''
    Handling for <text /> attribute.
    Note that to be reported to IoX, the value has to change; this is why we flip from 0 to 1 or 1 to 0.
    -1 is reserved for initializing.
    '''
    def pushTextToDriver(self,driver,stringToPublish):
        if not(self._fullyCreated) or not(self._initialized):
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

