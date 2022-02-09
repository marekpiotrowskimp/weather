#!/usr/bin/env python
import json
from collections import namedtuple
import Tkinter as tk
import tkMessageBox
import sys
import threading
import time
import socket
import sqlite3


class WeatherStation:
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        try:
            self.sock.settimeout(10)
            self.sock.connect((host, port))
            return True
        except:
            return False

    def send(self, msg):
        totalsent = 0
        msg_len = len(msg)
        while totalsent < msg_len:
            sent = self.sock.send(msg[totalsent:])
            if sent != 0:
               totalsent = totalsent + sent
            else:
               totalsent = msg_len

    def receive(self):
        chunks = []
        chunk = b'D'
        bytes_recd = 0
        self.sock.settimeout(10)
        try:
            while chunk != b'':
                chunk = self.sock.recv(min(2048 - bytes_recd, 2048))
                chunks.append(chunk)
                bytes_recd = bytes_recd + len(chunk)
            return b''.join(chunks)
        except socket.timeout as e:
            return None

    def disconnect(self):
        self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


root = tk.Tk()
root.overrideredirect(True)
root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))

bg_image = tk.PhotoImage(file = "weather2.png")
canvas = tk.Canvas(root, width = 480, height = 320,)
canvas.pack(fill="both", expand=True)

image_canvas = canvas.create_image(0, 0, image=bg_image, anchor="nw")

label_time = canvas.create_text(10, 20, text="---", anchor='w', font=("Courier", 10), fill="white")
label_preasure = canvas.create_text(10, 35, text="---", anchor='w', font=("Courier", 10), fill="white")
label_humidity = canvas.create_text(10, 50, text="---", anchor='w', font=("Courier", 10), fill="white")
label_temp = canvas.create_text(10, 65, text="---", anchor='w', font=("Courier", 10), fill="white")
label_pm1 = canvas.create_text(10, 80, text="---", anchor='w', font=("Courier", 10), fill="white")
label_pm25 = canvas.create_text(10, 95, text="---", anchor='w', font=("Courier", 10), fill="white")
label_pm10 = canvas.create_text(10, 110, text="---", anchor='w', font=("Courier", 10), fill="white")

endApp = False
def exit():
	endApp = True
	root.destroy()

B1 = tk.Button(root, text = "X", fg="White", bg="Black", command = exit)
B1.place(x=440, y=2)

weather = WeatherStation()

def _json_object_hook(d):
   return namedtuple('X', d.keys())(*d.values())

def json2obj(data):
   return json.loads(data, object_hook=_json_object_hook)


con = sqlite3.connect('weather.db')
cur = con.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS weather (datetime text, sensor text, json text)''')

lines = []

def remove_lines():
   for line in lines:
       canvas.delete(line)

def draw(x, y, width, height, type):
   lines.append(canvas.create_line(x, y, x, y + height, width = 4, fill='white'))
   lines.append(canvas.create_line(x, y + height, width, y + height, width = 4, fill='white'))
   index = 1
   for row in cur.execute('SELECT datetime, sensor, json FROM weather ORDER BY datetime DESC LIMIT 50'):
       obj = json2obj(row[2])
       if obj != None and obj.pms != None and obj.pms.PM2_5 != None and obj.pms.PM10_0 != None:
          field = obj.pms.PM2_5 if type == 'PM2_5' else obj.pms.PM10_0
          color = 'green' if field < 80 else 'orange' if field < 120 else 'red'
          field_normalized = (field / 2) if (field / 2) < (height - 2) else (height - 2)
          lines.append(canvas.create_line(x + index * 4, y + height - 2, x + index * 4, y + height - 2 - field_normalized, width = 4, fill = color))
          index += 1


def printit():
   canvas.itemconfig(image_canvas, image = bg_image)
   if not(endApp):
      root.after(60000, printit)

   if weather.connect("192.168.22.188", 80):
      weather.send(b'state')
      data = weather.receive()

      if data != None:
         cur.execute("INSERT INTO weather (datetime, sensor, json) VALUES (datetime('now', 'localtime'),'1',\'" + str(data) + "\')")
         con.commit()
         obj = json2obj(data)

         temp =     "Temperature: " + str(obj.temperature) + "C"
         humidity = "Humidity:    " + str(obj.humidity) + "%"
         preasure = "Preasure:    " + str(obj.preasure) + " hPa"
         time =     "Date Time:   " + str(obj.date) + " | " + str(obj.time)
         pm1  =     "PM1_0        " + str(obj.pms.PM1_0)
         pm25 =     "PM2_5        " + str(obj.pms.PM2_5)
         pm10 =     "PM10_0       " + str(obj.pms.PM10_0)
         canvas.itemconfig(label_temp, text=temp)
         canvas.itemconfig(label_humidity, text=humidity)
         canvas.itemconfig(label_preasure, text=preasure)
         canvas.itemconfig(label_time, text=time)
         canvas.itemconfig(label_pm1, text=pm1)
         canvas.itemconfig(label_pm25, text=pm25)
         canvas.itemconfig(label_pm10, text=pm10)
   weather.disconnect()
   remove_lines()
   draw(10, 120, 220, 80, 'PM2_5')
   draw(10, 220, 220, 80, 'PM10_0')

printit()

root.after(60000, printit)
root.mainloop()

for row in cur.execute('SELECT datetime, sensor, json FROM weather ORDER BY datetime DESC LIMIT 1'):
   print(row[2])

con.close()


