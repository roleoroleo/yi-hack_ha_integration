# yi-hack Home Assistant integration

## Overview
yi-hack Home assistant is a custom integration for Yi cameras with one of the following custom firmwares:
- yi-hack-MStar - https://github.com/roleoroleo/yi-hack-MStar
- yi-hack-Allwinner - https://github.com/roleoroleo/yi-hack-Allwinner
- yi-hack-Allwinner-v2 - https://github.com/roleoroleo/yi-hack-Allwinner-v2
<br>

This integration is available from the Lovelace frontend without the need to configure the devices in the file configuration.yaml
The wizard will connect to your cam and will install the following entities:
- ffmpeg cam with stream and snapshot capabilities
- mqtt cam with the last frame saved during a motion detection event
- mqtt binary sensor for status
- mqtt binary sensor for motion detection
- mqtt binary sensor for ai human detection (there are known issues when enabling ai human detection)
- mqtt binary sensor for sound detection
- mqtt binary sensor for baby crying detection
- ptz service (if your cam supports it)

## Installation
**(1)** Place the `custom_components` folder in your configuration directory.
It should look similar to this:
```
<config directory>/
|-- custom_components/
|   |-- yi-hack/
|       |-- translations/
|       |-- __init__.py
|       |-- binary_sensor.py
|       |-- camera.py
|       |-- config.py
|       |-- config_flow.py
|       |-- const.py
|       |-- manifest.json
|       |-- services.yaml
|       |-- strings.json
```
**(2)** Restart Home Assistant

**(3)** Configure device and entities:
- Go to Settings -> Integrations
- Click "Add Integration" in the lower-right corner
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
