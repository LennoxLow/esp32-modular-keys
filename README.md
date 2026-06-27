# ESP32 MODULAR HOTKEY SYSTEM 🔘✨
*"A physical button that can trigger anything. The first thing I used it for was generating meme compilations."*

---

## 🎬 As Seen In
This project appeared in my YouTube video:
[![I automated making meme compilations so I never have to watch Reddit again](https://img.youtube.com/vi/LXZIZYsod2A/hqdefault.jpg)](https://www.youtube.com/watch?v=LXZIZYsod2A) 

And yes — it's also on Instructables 👀
[[Happy Modular HotKeys](https://www.instructables.com/Happy-Modular-HotKeys-ESP32/)]


---

## ⚠️ What Is This?

Running a script from a terminal works fine.

But I wanted a physical button. Something that felt like I was actually doing something rather than typing `python main.py` and pressing enter like some kind of person who uses a computer normally.

So I built one. And then it got a bit out of hand.

Each module is an ESP32 with a button, an OLED display, and a 20-frame animation that plays when a trigger fires. The interesting part is what happens when you connect more than one — they negotiate master and slave roles automatically with no configuration, communicate over a serial bus, and broadcast triggers over WiFi UDP so everything connected hears every press.

Press any button on any module. Everything reacts.

---

## 🧠 Features

- Auto master/slave role negotiation via shared flag pin — no configuration needed
- Serial bus communication between modules (daisy-chainable)
- WiFi UDP broadcast so triggers reach anything on the network
- Automatic master promotion if master module is powered off
- GUID-based device identity — every module knows who sent what
- 20-frame OLED animation stored in PROGMEM — no SD card needed
- 25ms debounce on button input
- Periodic slave keepalive announcements
- Serial listener on PC side triggers any script on button press
- Modular — add as many buttons as you want

---

## 🧰 Parts List

| Part | Notes |
|------|-------|
| ESP32 (any variant) | One per module |
| Tactile push button | Wired to GPIO6 and GND |
| 0.66 Inch OLED  | I²C, address 0x3C |
| Jumper wires | For the bus between modules |
| USB cable | Flashing and power |
| 3D printed enclosure | Optional but satisfying |
| Arduino IDE | Where bugs are born |

---

## 🗺️ GPIO Map

| Pin | Function |
|-----|----------|
| GPIO 4 | I²C SDA → OLED |
| GPIO 5 | I²C SCL → OLED |
| GPIO 6 | Button (INPUT_PULLUP — wire to GND) |
| GPIO 7 | Master/slave flag pin |
| GPIO 20 | Serial RX (swapped on slave) |
| GPIO 21 | Serial TX (swapped on slave) |

**Button wiring:** One leg to GPIO6, other leg to GND. The internal pullup holds the pin HIGH. Press pulls it LOW — that's your trigger.

**Flag pin wiring:** Connect GPIO7 on all modules together with a single shared wire. This is how they negotiate roles on boot.

**Serial bus wiring:** TX of one module to RX of the next. Daisy chain as many as you want.

---

## 🧠 How the Master/Slave Negotiation Works

On boot, every module checks the shared flag pin (GPIO7):

- **Pin is LOW** — nobody has claimed master yet. This module sets the pin HIGH, declares itself master, and connects to WiFi.
- **Pin is HIGH** — a master already exists. This module becomes a slave, announces itself over the serial bus, and waits.

Power off the master mid-session — the slave detects the flag pin going LOW, waits 2 seconds to confirm it's not a glitch, then promotes itself to master.

No configuration. No pre-assignment. They just figure it out.

---

## 📡 Trigger Flow

**Master button pressed:**
```
Master button → broadcastMessage() → WiFi UDP + Serial bus → all modules react
```

**Slave button pressed:**
```
Slave button → busSend() to master → master forwards via broadcastMessage() → all modules react
```

Every trigger message includes the sending module's GUID so you always know which button fired.

---

## 🖥️ PC Serial Listener

A Python script on the PC side watches the serial port. When it receives a `TRIGGER` message from the master module it fires whatever script you point it at.

```python
import serial
import subprocess

ser = serial.Serial('COM3', 115200)  # Change to your port

while True:
    if ser.in_waiting:
        line = ser.readline().decode('utf-8').strip()
        if 'TRIGGER' in line:
            subprocess.call(['python', 'main.py'])
```

Change `COM3` to your actual port. Change `main.py` to whatever you want the button to run. That's the entire bridge between hardware and software.

---

## 🚀 Setup

**1. Install Arduino IDE**

Download from arduino.cc.

**2. Add ESP32 board support**

In Arduino IDE preferences, add this to Additional Board Manager URLs:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Then install `esp32` via Board Manager.

**3. Install libraries**

In Library Manager, install:
- `Adafruit SSD1306`
- `Adafruit GFX`

**4. Configure WiFi credentials**

In the firmware, find and update:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

**5. Flash each module**

- Connect via USB
- Select your ESP32 board
- Upload the sketch
- Repeat for each module

**6. Wire the modules together**

- Connect all GPIO7 pins together (flag bus)
- Connect TX/RX in daisy chain for serial bus
- Power all modules

**7. Run the serial listener**

```bash
python listener.py
```

**8. Press the button**

---

## ✨ The OLED Animation

When any trigger fires, all connected OLED screens play a 20-frame bounce animation.

The animation frames are stored as raw bitmaps in PROGMEM — meaning they live in flash memory on the microcontroller itself. No SD card, no external storage, no loading time. It just plays.

Each frame is 46×46 pixels. The animation plays forward then reverses in a loop until the next trigger.

---

## 🛠️ Troubleshooting

**OLED is blank**
- Check I²C wiring — SDA to GPIO4, SCL to GPIO5
- Confirm I²C address is `0x3C`
- Check common ground between ESP32 and OLED

**Modules not negotiating roles correctly**
- Make sure GPIO7 is connected between all modules with a shared wire
- Check that GPIO7 is not connected to anything else
- Power modules on one at a time to observe negotiation

**Slave not receiving triggers from master**
- Check TX/RX wiring — master TX to slave TX pin (firmware swaps it internally)
- Confirm both modules share a common ground
- Check baud rate is 115200 on both

**WiFi not connecting**
- Check SSID and password in firmware
- Master only connects to WiFi — slaves use serial bus only
- If WiFi fails, the master falls back to serial bus automatically

**Serial listener not receiving triggers**
- Check COM port — use Device Manager on Windows to find it
- Confirm baud rate is 115200
- Make sure the master module is connected to the PC, not a slave

**Button not triggering**
- Check wiring: one leg to GPIO6, other leg to GND
- Confirm `INPUT_PULLUP` is set in firmware
- Trigger fires on LOW — pressing should pull the pin to GND

---

## 🚀 Future Shenanigans

- Different trigger types per button (long press, double press)
- Battery power + wireless only mode
- Per-module custom animations
- Web interface for trigger configuration
- More modules obviously

---

## 🔗 Companion Project

The button was built to trigger this:
👉 [LennoxLow/Automatic-Meme-Compilation-Creator]((https://github.com/LennoxLow/Automatic-Meme-Compilation-Creator))

But it can trigger anything that runs from a command line.

I haven't decided what to make it do next.

---

## 🖤 License

Do whatever.
Attribute me if you feel polite.



-readme was generated, instructables is a good source for any additional information-
