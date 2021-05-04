# yi-hack Home Assistant integration
<p align="center">
<img src="https://github.com/roleoroleo/yi-hack_ha_integration/raw/main/images/icon.png">
</p>

## Overview
yi-hack Home Assistant is a custom integration for Yi cameras (or Sonoff camera) with one of the following custom firmwares:
- yi-hack-MStar - https://github.com/roleoroleo/yi-hack-MStar
- yi-hack-Allwinner - https://github.com/roleoroleo/yi-hack-Allwinner
- yi-hack-Allwinner-v2 - https://github.com/roleoroleo/yi-hack-Allwinner-v2
- yi-hack-v5 - https://github.com/alienatedsec/yi-hack-v5
- sonoff-hack - https://github.com/roleoroleo/sonoff-hack
<br>

This integration is available from the Lovelace frontend without the need to configure the devices in the file configuration.yaml
The wizard will connect to your cam and will install the following entities:
- ffmpeg cam with stream and snapshot capabilities
- mqtt cam with the last frame saved during a motion detection event
- mqtt binary sensor for status
- mqtt binary sensor for motion detection
- mqtt binary sensor for ai human detection (there are known issues when enabling ai human detection) (*)
- mqtt binary sensor for sound detection (*)
- mqtt binary sensor for baby crying detection (*)
- media player entity useful to play Home Assistant standard tts service (*)
- ptz service (*)
- speak service (only available if you install the internal tts engine from here https://github.com/roleoroleo/yi-hack-utils)

(*) available only if your cam supports it.

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
|       |-- services.yaml
|       |-- strings.json
```
**(2)** Restart Home Assistant

**(3)** Configure device and entities:
- Go to Settings -> Integrations
- Click "Add Integration" in the lower-right corner
- Select "Yi Cam with yi-hack" integration
- Enter the settings for your cam: host, port, username, password and ffmpeg parameters
- Confirm and wait for the wizard completion
- Set the "Area" if you need it
- Enjoy your cam
<br><br>

## Donation
If you like this project, you can buy me a beer :) 
[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=JBYXDMR24FW7U&currency_code=EUR&source=url)

---
### DISCLAIMER
**I AM NOT RESPONSIBLE FOR ANY USE OR DAMAGE THIS SOFTWARE MAY CAUSE. THIS IS INTENDED FOR EDUCATIONAL PURPOSES ONLY. USE AT YOUR OWN RISK.**
