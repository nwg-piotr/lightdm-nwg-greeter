#!/usr/bin/env python3
#
# Simple LightDM greeter, based on GTK 3.
#
# The code is based on the example greeter written and explained by
# Matt Fischer:
# http://www.mattfischer.com/blog/archives/5

import argparse
import configparser
import json
import locale
from datetime import datetime

import gi
import os
import sys
from pathlib import Path

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("LightDM", "1")

try:
    gi.require_version('GtkLayerShell', '0.1')
except ValueError:

    raise RuntimeError('\n\n' +
                       'If you haven\'t installed GTK Layer Shell, you need to point Python to the\n' +
                       'library by setting GI_TYPELIB_PATH and LD_LIBRARY_PATH to <build-dir>/src/.\n' +
                       'For example you might need to run:\n\n' +
                       'GI_TYPELIB_PATH=build/src LD_LIBRARY_PATH=build/src python3 ' + ' '.join(sys.argv))

from gi.repository import GLib, GtkLayerShell
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import LightDM

DEFAULT_SESSION = "sway"
UI_FILE_LOCATION = "/usr/local/share/nwg-greeter/nwg-greeter.ui"
BACKGROUND_FILE_LOCATION = "/usr/local/share/nwg-greeter/img/nwg.jpg"
ICONS_LOCATION = "/usr/share/nwg-greeter/img/"
LANG_FILES_LOCATION = "/usr/share/nwg-greeter/lang/"

# read the cache
cache_dir = (Path.home() / ".cache" / "nwg-greeter")
cache_dir.mkdir(parents=True, exist_ok=True)
state_file = (cache_dir / "state")
state_file.touch()
cache = configparser.ConfigParser()
cache.read(str(state_file))
if not cache.has_section("greeter"):
    cache.add_section("greeter")

greeter = None
password_entry = None
message_label = None
usernames_box = None
password_label = None
sessions_box = None
sleep_button = None
reboot_button = None
poweroff_button = None
login_clicked = False
voc = {}


def set_password_visibility(visible):
    """Show or hide the password entry field."""
    password_entry.set_sensitive(visible)
    password_label.set_sensitive(visible)
    if visible:
        password_entry.show()
        password_label.show()
    else:
        password_entry.hide()
        password_label.hide()


def read_config(gtk_settings, config_file="/etc/lightdm/nwg-greeter.conf"):
    """Read the configuration from the file."""
    if not os.path.isfile(config_file):
        return

    config = configparser.ConfigParser()
    config.read(config_file)
    if "GTK" in config:
        # every setting in the GTK section starting with 'gtk-' is applied directly
        for key in config["GTK"]:
            if key.startswith("gtk-"):
                value = config["GTK"][key]
                gtk_settings.set_property(key, value)

    if "Greeter" in config:
        global DEFAULT_SESSION, UI_FILE_LOCATION, BACKGROUND_FILE_LOCATION, ICONS_LOCATION, LANG_FILES_LOCATION
        DEFAULT_SESSION = config["Greeter"].get("default-session", DEFAULT_SESSION)
        UI_FILE_LOCATION = config["Greeter"].get("ui-file-location", UI_FILE_LOCATION)
        BACKGROUND_FILE_LOCATION = config["Greeter"].get("background-file-location", BACKGROUND_FILE_LOCATION)
        ICONS_LOCATION = config["Greeter"].get("icons-location", ICONS_LOCATION)
        LANG_FILES_LOCATION = config["Greeter"].get("lang-files-location", LANG_FILES_LOCATION)


def write_cache():
    """Write the current cache to file."""
    with open(str(state_file), "w") as file_:
        cache.write(file_)


def auto_select_user_session(username):
    """Automatically select the user's preferred session."""
    users = LightDM.UserList().get_users()
    users = [u for u in users if u.get_name() == username] + [None]
    user = users[0]

    if user is not None:
        session_index = 0
        if user.get_session() is not None:
            # find the index of the user's session in the combobox
            session_index = [row[0] for row in sessions_box.get_model()].index(user.get_session())

        sessions_box.set_active(session_index)


def start_session():
    global sessions_box
    session = sessions_box.get_active_text() or DEFAULT_SESSION
    write_cache()
    if not greeter.start_session_sync(session):
        print("failed to start session", file=sys.stderr)
        message_label.set_text("Failed to start Session")


def dm_show_prompt_cb(greeter, text, prompt_type=None, **kwargs):
    """Respond to the password request sent by LightDM."""
    # this event is sent by LightDM after user authentication
    # started, if a password is required
    if login_clicked:
        greeter.respond(password_entry.get_text())
        password_entry.set_text("")

    if "password" not in text.lower():
        print(f"LightDM requested prompt: {text}", file=sys.stderr)


def dm_show_message_cb(greeter, text, message_type=None, **kwargs):
    """Show the message from LightDM to the user."""
    print(f"message from LightDM: {text}", file=sys.stderr)
    message_label.set_text(text)


def dm_authentication_complete_cb(greeter):
    """Handle the notification that the authentication is completed."""
    if not login_clicked:
        # if this callback is executed before we clicked the login button,
        # this means that this user doesn't require a password
        # - in this case, we hide the password entry
        set_password_visibility(False)

    else:
        if greeter.get_is_authenticated():
            # the user authenticated successfully:
            # try to start the session
            start_session()
        else:
            # autentication complete, but unsucessful:
            # likely, the password was wrong
            message_label.set_text("Login failed")
            print("login failed", file=sys.stderr)


def user_change_handler(widget, data=None):
    """Event handler for selecting a different username in the ComboBox."""
    global login_clicked
    login_clicked = False

    if greeter.get_in_authentication():
        greeter.cancel_authentication()

    username = usernames_box.get_active_text()
    greeter.authenticate(username)
    auto_select_user_session(username)

    set_password_visibility(True)
    password_entry.set_text("")
    cache.set("greeter", "last-user", username)


def login_click_handler(widget, data=None):
    """Event handler for clicking the Login button."""
    global login_clicked
    login_clicked = True

    if greeter.get_is_authenticated():
        # the user is already authenticated:
        # this is likely the case when the user doesn't require a password
        start_session()

    if greeter.get_in_authentication():
        # if we're in the middle of an authentication, let's cancel it
        greeter.cancel_authentication()

    # (re-)start the authentication for the selected user
    # this should trigger LightDM to send a 'show-prompt' signal
    # (note that this time, login_clicked is True, however)
    username = usernames_box.get_active_text()
    greeter.authenticate(username)


def sleep_click_handler(widget, data=None):
    if LightDM.get_can_suspend():
        LightDM.suspend()


def reboot_click_handler(widget, data=None):
    if LightDM.get_can_restart():
        LightDM.restart()


def poweroff_click_handler(widget, data=None):
    if LightDM.get_can_shutdown():
        LightDM.shutdown()


def update_time(hour_label, date_label):
    now = datetime.now()
    time = now.strftime("%H:%M")
    date = now.strftime("%A, %d. %B")
    hour_label.set_label(time)
    date_label.set_label(date)
    return True


def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print("Error loading json: {}".format(e))
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t",
                        "--test",
                        action="store_true",
                        help="Testing mode - do not connect to greater daemon")

    parser.add_argument("-l",
                        "--lang",
                        type=str,
                        default="",
                        help="force a certain Language, e.g. 'pl_PL' for Polish")

    parser.parse_args()
    args = parser.parse_args()

    # load basic vocabulary
    global voc
    voc = load_json(os.path.join(LANG_FILES_LOCATION, "en_US"))
    user_locale = locale.getlocale()[0] if not args.lang else args.lang
    # translate if necessary and possible
    if user_locale != "en_US" and user_locale in os.listdir(LANG_FILES_LOCATION):
        # translated phrases
        loc = load_json(os.path.join(LANG_FILES_LOCATION, user_locale))
        for key in voc:
            if key in loc:
                voc[key] = loc[key]

    global greeter
    greeter = LightDM.Greeter()
    settings = Gtk.Settings.get_default()
    read_config(settings)
    cursor = Gdk.Cursor(Gdk.CursorType.LEFT_PTR)
    greeter_session_type = os.environ.get("XDG_SESSION_TYPE", None)

    # connect signal handlers to LightDM
    # signals: http://people.ubuntu.com/~robert-ancell/lightdm/reference/LightDMGreeter.html#LightDMGreeter-authentication-complete
    greeter.connect("authentication-complete", dm_authentication_complete_cb)
    greeter.connect("show-message", dm_show_message_cb)
    greeter.connect("show-prompt", dm_show_prompt_cb)

    # connect builder and widgets
    ui_file_path = UI_FILE_LOCATION
    # builder.add_from_file(ui_file_path)

    display = Gdk.Display.get_default()
    builder = Gtk.Builder()
    # ui_file_path = os.path.join(dir_name, "nwg-greeter.ui")
    builder.add_from_file(ui_file_path)
    monitor = display.get_monitor(0)
    rect = monitor.get_geometry()

    login_window = builder.get_object("login_window")
    global password_entry
    password_entry = builder.get_object("password_entry")
    password_entry.set_property("name", "form-field")
    global password_label
    password_label = builder.get_object("password_label")
    password_label.set_text(f'{voc["password"]}:')
    global message_label
    message_label = builder.get_object("message_label")
    message_label.set_property("name", "message_label")
    hour_label = builder.get_object("hour_label")
    hour_label.set_property("name", "hour_label")
    date_label = builder.get_object("date_label")
    date_label.set_property("name", "date_label")
    session_label = builder.get_object("session_label")
    session_label.set_text(f'{voc["session"]}:')
    user_label = builder.get_object("user_label")
    user_label.set_text(f'{voc["user"]}:')
    left_box = builder.get_object("left_box")
    left_box.set_property("name", "left-box")
    vertical_box = builder.get_object("vertical_box")
    global usernames_box
    usernames_box = builder.get_object("usernames_cb")
    usernames_box.set_property("name", "form-field")
    global sessions_box
    sessions_box = builder.get_object("sessions_cb")
    sessions_box.set_property("name", "form-field")
    login_button = builder.get_object("login_button")
    login_button.set_label(f'{voc["login"]}')
    login_button.set_property("name", "login-button")

    global sleep_button
    sleep_button = builder.get_object("sleep_button")
    sleep_button.set_label(f'{voc["sleep"]}')
    sleep_button.set_property("name", "bottom-button")
    sleep_button.set_image_position(Gtk.PositionType.TOP)
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(ICONS_LOCATION, "sleep.svg"), 64, 64)
    img = Gtk.Image()
    img.set_from_pixbuf(pixbuf)
    sleep_button.set_image(img)
    sleep_button.set_always_show_image(True)

    global reboot_button
    reboot_button = builder.get_object("reboot_button")
    reboot_button.set_label(f'{voc["reboot"]}')
    reboot_button.set_property("name", "bottom-button")
    reboot_button.set_image_position(Gtk.PositionType.TOP)
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(ICONS_LOCATION, "reboot.svg"), 64, 64)
    img = Gtk.Image()
    img.set_from_pixbuf(pixbuf)
    reboot_button.set_image(img)
    reboot_button.set_always_show_image(True)

    global poweroff_button
    poweroff_button = builder.get_object("poweroff_button")
    poweroff_button.set_label(f'{voc["power-off"]}')
    poweroff_button.set_property("name", "bottom-button")
    poweroff_button.set_image_position(Gtk.PositionType.TOP)
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(ICONS_LOCATION, "poweroff.svg"), 64, 64)
    img = Gtk.Image()
    img.set_from_pixbuf(pixbuf)
    poweroff_button.set_image(img)
    poweroff_button.set_always_show_image(True)

    GtkLayerShell.init_for_window(login_window)
    GtkLayerShell.set_monitor(login_window, monitor)
    GtkLayerShell.set_anchor(login_window, GtkLayerShell.Edge.TOP, 1)
    GtkLayerShell.set_anchor(login_window, GtkLayerShell.Edge.BOTTOM, 1)
    GtkLayerShell.set_anchor(login_window, GtkLayerShell.Edge.LEFT, 1)
    GtkLayerShell.set_anchor(login_window, GtkLayerShell.Edge.RIGHT, 1)

    # connect to greeter
    if not args.test:
        greeter.connect_to_daemon_sync()

    # set up the GUI
    # login_window.get_root_window().set_cursor(cursor)
    password_entry.set_text("")
    password_entry.set_sensitive(True)
    password_entry.set_visibility(False)
    if greeter_session_type is not None:
        print(f"greeter session type: {greeter_session_type}", file=sys.stderr)
        message_label.set_text(f'{voc["welcome"]}')

    # register handlers for our UI elements
    sleep_button.connect("clicked", sleep_click_handler)
    reboot_button.connect("clicked", reboot_click_handler)
    poweroff_button.connect("clicked", poweroff_click_handler)
    usernames_box.connect("changed", user_change_handler)
    password_entry.connect("activate", login_click_handler)
    login_button.connect("clicked", login_click_handler)
    # login_window.set_default(login_button)

    # make the greeter "fullscreen"
    screen = login_window.get_screen()
    screen.get_root_window().set_cursor(cursor)
    login_window.resize(rect.width, rect.height)
    left_box.set_size_request(rect.width * 0.4, 0)
    vertical_box.set_size_request(rect.width * 0.3, 0)

    # populate the combo boxes
    user_idx = 0
    last_user = cache.get("greeter", "last-user", fallback=None)
    for idx, user in enumerate(LightDM.UserList().get_users()):
        usernames_box.append_text(user.get_name())
        if last_user == user.get_name():
            user_idx = idx

    for session in LightDM.get_sessions():
        sessions_box.append_text(session.get_key())

    sessions_box.set_active(0)
    usernames_box.set_active(user_idx)

    # if the selected user requires a password, (i.e the password entry
    # is visible), focus the password entry -- otherwise, focus the
    # user selection box
    if password_entry.get_sensitive():
        password_entry.grab_focus()
    else:
        usernames_box.grab_focus()

    login_window.show_all()
    # login_window.fullscreen()
    login_window.fullscreen_on_monitor(screen, 0)

    provider = Gtk.CssProvider()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    css = provider.to_string().encode('utf-8')
    win_style = f'\nwindow {{ background-image: url("{BACKGROUND_FILE_LOCATION}"); background-size: 100% 100% }}'.encode('utf-8')
    css += b""" 
        combobox button {
            border-radius: 15px;
            background: none;
            background-color: rgba (255, 255, 255, 0.2);
            border-color: #ccc;
            padding: 10px
        }
        combobox window menu {
            background-color: rgba (0, 0, 0, 0.8)
        }
        entry { 
            background-color: rgba (255, 255, 255, 0.1); 
            border-radius: 15px; 
            padding: 10px; 
            border-color: #ccc; 
            color: #f00 
        } 
        #login-button { 
            background: none;
            background-color: rgba (255, 255, 255, 0.3);
            border: solid 1px;
            border-color: #ccc;
            padding: 15px;
            border-radius: 15px; 
        }
        #login-button:hover { background-color: rgba (255, 255, 255, 0.5); }
        #bottom-button { background: none; padding: 6px; border: none }
        #bottom-button:hover {
            background-color: rgba (255, 255, 255, 0.3);
            border-radius: 15px; 
        }
        #left-box { background-color: rgba (0, 0, 0, 0.3) }
        #message_label { font-size: 36px }
        #hour_label { font-size: 36px}
        #date_label { font-size: 18px; }"""
    css += win_style
    provider.load_from_data(css)

    update_time(hour_label, date_label)
    GLib.timeout_add_seconds(1, update_time, hour_label, date_label)

    Gtk.main()


if __name__ == "__main__":
    sys.exit(main())
