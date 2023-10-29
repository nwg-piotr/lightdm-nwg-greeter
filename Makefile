INSTALL_PATH=/usr
CONFIG_PATH=/etc
PKG_PREFIX=

nwg-greeter.conf: nwg-greeter.conf.base
	sed -e "s|INSTALL_PATH|$(INSTALL_PATH)|" nwg-greeter.conf.base > nwg-greeter.conf

clean:
	rm nwg-greeter.conf

install: nwg-greeter.conf
	install -D -m 644 -t $(PKG_PREFIX)$(CONFIG_PATH)/lightdm/ nwg-greeter.conf
	install -D -m 755 -t $(PKG_PREFIX)$(INSTALL_PATH)/bin nwg-greeter.py
	install -D -m 644 -t $(PKG_PREFIX)$(INSTALL_PATH)/share/lightdm/greeters lightdm-nwg-greeter.desktop lightdm-nwg-greeter-x11.desktop
	install -D -m 644 -t $(PKG_PREFIX)$(INSTALL_PATH)/share/nwg-greeter nwg-greeter.ui
	install -D -m 644 -t $(PKG_PREFIX)$(INSTALL_PATH)/share/nwg-greeter/img img/*

uninstall:
	rm $(INSTALL_PATH)/bin/nwg-greeter.py
	rm -r $(INSTALL_PATH)/share/nwg-greeter/
	rm $(INSTALL_PATH)/share/lightdm/greeters/lightdm-nwg-greeter.desktop
	rm $(INSTALL_PATH)/share/lightdm/greeters/lightdm-nwg-greeter-x11.desktop
	rm $(CONFIG_PATH)/lightdm/nwg-greeter.conf

