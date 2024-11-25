[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

# announcement
i gave up on this repo, i started afresh in the notsosmartthings repo.

# SmartThings Custom
A fork of a fork of the Home Assistant SmartThings Integration. This adds better support for Samsung OCF Devices.

## Installation:
### HACS
- Remove your original smartthings integration if you have one set up (optional)
- Add `https://github.com/alrassia/smartthings` as a Custom Repository
- Install `SmartThings Custom` from the HACS Integrations tab
- Restart Home Assistant
- Install `SmartThings` from the HA Integrations tab
- Enjoy!

### Manually
- Remove your original smartthings integration if you have one set up (optional)
- Copy the smartthings folder to custom_components
- Restart Home Assistant
- Install `SmartThings` from the HA Integrations tab
- Enjoy!

## Notes:
- This code is based on the initial fork of veistas which was modified by beschoenen, I tried to add the pull request to add components to the code based on https://github.com/home-assistant/core/pull/107868
- I cant guarantee that anything you find here will work. so thread lightly.
