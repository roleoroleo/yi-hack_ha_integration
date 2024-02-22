# yi-hack Home Assistant integration
<p align="center">
<img src="https://github.com/roleoroleo/yi-hack_ha_integration/raw/main/images/icon.png">
</p>

## Overview
yi-hack Home Assistant is a custom integration for Yi cameras (or Sonoff camera) with one of the following custom firmwares:
- yi-hack-MStar - https://github.com/roleoroleo/yi-hack-MStar
- yi-hack-Allwinner - https://github.com/roleoroleo/yi-hack-Allwinner
- yi-hack-Allwinner-v2 - https://github.com/roleoroleo/yi-hack-Allwinner-v2
- yi-hack-v5 (partial support) - https://github.com/alienatedsec/yi-hack-v5 (seems like full support with 0.4.1j release)
- sonoff-hack - https://github.com/roleoroleo/sonoff-hack
<br>
And make sure you have the latest version.
<br>

This integration is available from the Lovelace frontend without the need to configure the devices in the file configuration.yaml
The wizard will connect to your cam and will install the following entities:
- ffmpeg cam with stream and snapshot capabilities
- mqtt cam with the last frame saved during a motion detection event
- mqtt binary sensor for status (connection)
- mqtt binary sensor for motion detections: human, animal, vehicle, ... (*)
- mqtt binary sensor for sound detection (*)
- mqtt binary sensor for baby crying detection (*)
- media player entity useful to play Home Assistant standard tts service (*)
- switches and selects to enable/disable some cam configuration
- ptz service (*)
- speak service (only available if you install the internal tts engine from here https://github.com/roleoroleo/yi-hack-utils)

(*) available only if your cam supports it.

If you configure motion detection in your camera and media source in your home assistant installation, you will be able to view the videos in the "Media" section (left panel of the main page).

## Dependencies
1. Home Assistant
   - [MQTT Integration](https://www.home-assistant.io/integrations/mqtt) installed
   - [Mosquitto broker](https://github.com/home-assistant/addons/tree/master/mosquitto) add-on installed and connected to MQTT
2. Camera
   - MQTT enabled
   - Configured with MQTT Broker credentials
   - Default Topics configuration

## Installation
**(1)** Copy the  `custom_components` folder your configuration directory.
It should look similar to this:
```
<config directory>/
|-- custom_components/
|   |-- yi_hack/
|       |-- translations/
|       |-- __init__.py
|       |-- binary_sensor.py
|       |-- camera.py
|       |-- config.py
|       |-- config_flow.py
|       |-- const.py
|       |-- manifest.json
|       |-- media_player.py
|       |-- media_source.py
|       |-- select.py
|       |-- services.yaml
|       |-- strings.json
|       |-- switch.py
|       |-- views.py
```
**(2)** Restart Home Assistant

**(3)** Configure device and entities:
- Go to Settings -> Integrations
- Click "Add Integration" in the lower-right corner
- Select "Yi Cam with yi-hack" integration
<p align="center">
<img src="https://user-images.githubusercontent.com/39277388/118390725-eadd7700-b630-11eb-87f9-9b03b1e587f4.png" width="400">
</p>

- Enter the settings to connect to the web interface of your cam: host, port, username, password and ffmpeg parameters
<p align="center">
<img src="https://user-images.githubusercontent.com/39277388/118390634-67bc2100-b630-11eb-8f73-008cad6b2b3d.png" width="400">
</p>

- Confirm and wait for the wizard completion
- Set the "Area" if you need it
- Enjoy your cam
<br><br>

## Add the stream to lovelace
If you want to add your live stream to lovelace, use this custom components: https://github.com/AlexxIT/WebRTC/

And add a simple configuration like this:
```
type: 'custom:webrtc-camera'
entity: camera.yi_hack_m_XXXXXX_cam
ui: true
```
If you have the camer setup in the motionEye Addon you can display the stream with the following:
```
type: picture-entity
entity: camera.camera1
```
_The Adress to add the Cam to motionEye is visible on the "Home" webinterface page. In my case it was: rtsp://192.168.178.243/ch0_0.h264_

## Add PTZ-Buttons to Dashboard _(only if supported by the camera)_
Example for left movement
```
type: button
tap_action:
  action: call-service
  service: yi_hack.ptz
  target: {}
  data:
    movement: left
    entity_id: camera.yi_hack_v5_abb....
icon: mdi:arrow-left-bold-circle-outline
name: yicam_ptz_left
```

## Requirements
This component requires MQTT integration to be installed.
Please be sure you added MQTT to you Home Assistant configuration.

If you want to browse mp4 files saved on your cam, add media source component to your home assistant installation.
Add the linw below to your configuration file:
```
# Example configuration.yaml entry
media_source:
```

---

### DISCLAIMER
**I AM NOT RESPONSIBLE FOR ANY USE OR DAMAGE THIS SOFTWARE MAY CAUSE. THIS IS INTENDED FOR EDUCATIONAL PURPOSES ONLY. USE AT YOUR OWN RISK.**

## Donation
If you like this project, you can buy me a beer :) 

Click [here](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=JBYXDMR24FW7U&currency_code=EUR&source=url) or use the below QR code to donate via PayPal
<p align="center">
  <img src="https://github.com/roleoroleo/yi-hack_ha_integration/assets/39277388/196e34bf-8a72-4ed9-92ce-59010cd81b37"/>
</p>
