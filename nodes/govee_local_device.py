#!/usr/bin/env python3
"""
Polyglot v3 node server Example 3
Copyright (C) 2021 Robert Paauwe

MIT License
"""
import udi_interface
import sys

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

'''
Device node
'''
class GoveeLocalDevice(udi_interface.Node):
    id = 'govee_local_device'
    drivers = [
            {'driver': 'ST', 'value': 101, 'uom': 78},
            {'driver': 'OL', 'value': 101, 'uom': 78},
            {'driver': 'FREQ', 'value': -1, 'uom': 56},
            {'driver': 'PULSCNT', 'value': -1, 'uom': 2},
            {'driver': 'GV0', 'value': -1, 'uom': 26},
            {'driver': 'GV1', 'value': -1, 'uom': 56},
            {'driver': 'GV2', 'value': -1, 'uom': 56},
            {'driver': 'GV3', 'value': -1, 'uom': 56},
            {'driver': 'TIME', 'value': -1, 'uom': 56},
            {'driver': 'GPV', 'value': -1, 'uom': 56}
            ]

    def __init__(self, polyglot, parent, address, name):
        super(CounterNode, self).__init__(polyglot, parent, address, name)

        self.poly = polyglot

        self.Parameters = Custom(polyglot, 'customparams')

        # subscribe to the events we want
        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        polyglot.subscribe(polyglot.POLL, self.poll)

    '''
    Read the user entered custom parameters. In this case, it is just
    the 'multiplier' value that we want.  
    '''
    def parameterHandler(self, params):
        self.Parameters.load(params)

    '''
    This is where the real work happens.  When we get a shortPoll, increment the
    count, report the current count in GV0 and the current count multiplied by
    the user defined value in GV1. Then display a notice on the dashboard.
    '''
    def poll(self, polltype):
        LOGGER.info('\n\tPOLLTYPE: ' + polltype + '.\n')
