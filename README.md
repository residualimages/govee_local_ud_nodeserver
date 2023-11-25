# Integration for Local Network-Based Control of Govee Lights - Polyglot v3 NodeServer for Universal Devices Controllers
#             (c) 2023 Matt Burke

A simple node server that issues commands to Govee lights which support the Local Network API (eliminates need for cloud API key).

This node server updates the values at every shortPoll() interval.

## Installation

### Node Settings
The settings for this node are:

#### Short Poll
   * How often to poll the Govee lights
#### Long Poll
   * Not used

#### IP Address(es)
   * ;-delimited list of IP address(es) of the Govee Lights

#### Device Name(s)
   * ;-delimited list of Device Names for the corresponding Govee Light IP address(es)
     
## Requirements

1. Polyglot V3.
2. ISY firmware 5.6.4 or later (due to String-type Statuses in IoX)

## NodeServer Drivers / Status Types (for Variable Substitution etc)
    • Root NodeServer Controller ('Govee Local Network NodeServer Controller'):
      º ST = If NodeServer is Active (boolean)
      º GV0 = Number of Govee lights configured for the NodeServer
      º GPV = Message from NodeServer - value will be between -1 (Initializing) and then flip between 0/1 (no meaning)
              The 'text' subattribute is what is shown in IoX (and why the required version of IoX is 5.6.4+)

    • Govee Device
      º ST = On/Off State of Light
      º OL = On Level (Brightness) of Device (1-100)
      º FREQ = IP Address of Device
      º PULSCNT = MAC Address of Device
      º GV0 = Color Temperature in Kelvins (2000-9000)
      º GV1 = Color value for "R" (0-255)
      º GV2 = Color value for "G" (0-255)
      º GV3 = Color value for "B" (0-255)
      º TIME = Last Successful Query
      º GPV = Message from NodeServer - value will be between -1 (Initializing) and then flip between 0/1 (no meaning)
              The 'text' subattribute is what is shown in IoX (and why the required version of IoX is 5.6.4+)

# Release Notes
  
- 1.0.0 11/25/2023

  º Initial version copied from Example 3 Node Server (https://github.com/UniversalDevicesInc/udi-example3-poly)
