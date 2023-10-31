# LightDM nwg greater
This greeter is based on the [LightDM Elephant Greeter](https://github.com/max-moser/lightdm-elephant-greeter) by 
Maximilian Moser, and has been preconfigured for use with [nwg-iso](https://github.com/nwg-piotr/nwg-iso). This is a part of the nwg-shell 
project. Please check the [project website](https://nwg-piotr.github.io/nwg-shell).

LightDM Elephant Greeter is a small and simple [LightDM](https://github.com/canonical/lightdm) greeter, using Python and GTK, that doesn't require 
an X11 server, based on [Matt ~~Shultz's~~ Fischer's example LightDM greeter](http://www.mattfischer.com/blog/archives/5).

## Screenshot

![Screenshot](./screenshot.png?raw=true "Screenshot")

## Original Elephant greeter features

- optionally uses Wayland, via [Cage](https://www.hjdskes.nl/projects/cage/) (instead of X11);
- remembers the last authenticated user;
- automatically selects the last used session per user.

**Note**: The last authenticated user is stored in a cache file in the LightDM user's home directory (e.g. `/var/lib/lightdm/.cache/nwg-greeter/state`), similar to [Slick Greeter](https://github.com/linuxmint/slick-greeter/blob/ae927483c5dcf3ae898b3f0849e3770cfa04afa1/src/user-list.vala#L1026).

## Changes implemented in nwg greeter

- always opens on screen 0;
- supports multiple languages;
- supports background image;
- uses a different layout, inspired by [Sugar Candy SDDM theme](https://framagit.org/MarianArlt/sddm-sugar-candy) by Marian Arlt;
- provides the "Show password" check button;
- supports command line arguments (mostly for testing purposes):

```text
❯ nwg-greeter.py -h
usage: nwg-greeter.py [-h] [-v] [-t] [-l LANG]

options:
  -h, --help            show this help message and exit
  -v, --version         display Version information
  -t, --test            Testing mode - do not connect to greater daemon
  -l LANG, --lang LANG  force a certain Language, e.g. 'pl_PL' for Polish
```

## Dependencies

* LightDM
* Python 3.8+
* [PyGObject](https://pygobject.readthedocs.io/en/latest/index.html): GObject bindings for Python
* [Cage](https://www.hjdskes.nl/projects/cage/): small wayland compositor for the greeter

**Note**: Please make sure you have all requirements installed, as having a LightDM greeter constantly failing isn't as 
much fun as it sounds.

## Installation

The greeter can be installed by copying the files to the right places (`make install`) and updating LightDM's 
configuration file to register the greeter (`/etc/lightdm/lightdm.conf`):

```ini
[LightDM]
sessions-directory=/usr/share/lightdm/sessions:/usr/share/wayland-sessions:/usr/share/xsessions
greeters-directory=/usr/share/lightdm/greeters:/usr/share/xgreeters

[Seat:*]
greeter-session=lightdm-nwg-greeter
```

**Note**: If you wish to install the files somewhere else, specify them in the `make` command.  
For instance, to install the files into subdirectories of `/usr/local` instead of `/usr`, call `make INSTALL_PATH=/usr/local install`.
The `CONFIG_PATH` (default: `/etc`) can be overridden in the same fashion.

## Configuration

The greeter's configuration file (`/etc/lightdm/nwg-greeter.conf`) contains the sections `Greeter` and `GTK`.  
The former are basic configuration values that can determine the behavior of the greeter (e.g. override file locations), 
while the latter are passed directly to GTK (and can be used to e.g. set the GTK theme).

Example configuration file:
```ini
[GTK]
gtk-theme-name=Adwaita
gtk-application-prefer-dark-theme=true
gtk-cursor-theme-name=Adwaita

[Greeter]
ui-file-location=/usr/share/nwg-greeter/nwg-greeter.ui
background-file-location=/usr/share/nwg-greeter/img/nwg.jpg
icons-location=/usr/share/nwg-greeter/img/
lang-files-location=/usr/share/nwg-greeter/lang/
```

## Credits

- background image by [@edskeye](https://github.com/edskeye), licensed under the terms of the 
[Creative Commons Zero v1.0 Universal license](https://github.com/nwg-piotr/nwg-shell-wallpapers/blob/main/LICENSE).