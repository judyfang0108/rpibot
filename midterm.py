import time
import threading
import re
import os
import sys
import socket
import struct
import timeit
import time
from ckiptagger import data_utils, WS, POS, NER
from gtts import gTTS
from subprocess import call
from enum import Enum, unique
from traceback import print_exc
from aiy.board import Board
from aiy.voice.audio import AudioFormat, play_wav, record_file, Recorder

import RPi.GPIO as GPIO
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import Adafruit_SSD1306
global HOST_TTS
global PORT_TTS
Lab = AudioFormat(sample_rate_hz=16000, num_channels=1, bytes_per_sample=2)

#GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

#set GPIO Pins
GPIO_TRIGGER = 25
GPIO_ECHO = 24

#set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

STEPS_PER_REVOLUTION = 32 * 64
SEQUENCE = [[1, 0, 0, 0], 
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 1]]


STEPPER_PINS = [17,18,27,22]
for pin in STEPPER_PINS:
    GPIO.setup(pin,GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

SEQUENCE_COUNT = len(SEQUENCE)
PINS_COUNT = len(STEPPER_PINS)

global reply_key
global reply_ans
reply_key=['醫學','食','交通','再見','打開','拍開',
            '藥仔','發燒','高血壓','流血','手術','發炎','喙齒','注射','頭殼','目睭',
            '公車','火車頭','公園','車票','美術館','一百','換車','臺中','機場','捷運',
            '咖啡廳','日本','飲料','有名','牛肉','美國','菜','韓國','學校','健康',]
reply_ans=['歡迎提問醫療問題','歡迎提問食問題','歡迎提問交通問題','再見','風扇','風扇',
            '早晚睡前各一次就可以了','我幫你開點退燒藥','你先不要緊張放鬆情緒','你別亂動我會幫你止血','大概是明天下午三點喔',
            '我請護士趕快幫你處理\n一下','你蛀牙了我幫你補一下','要記得多喝水多休息喔','請去吃點普拿疼','你近視了要戴眼鏡',
            '有喔你搭十號公車就可\n以了','前面直走右轉就到了','大概十分鐘左右','老人優待票六十元','搭計程車過去最方便喔',
            '可以喔','要在中正紀念堂換車喔','十一點三十發車喔','建議搭機場捷運最快喔','有喔在後驛站',
            '有喔大學路就有兩間','推薦你勝博殿豬排喔','芋頭西米露少糖少冰','那間就是鼎富發','六千和文章都不錯喔',
            '夢時代五樓有很多喔','可以根據你的習慣調整\n辣度','那我幫你點一份韓國辣\n炒年糕','你可以到育樂街上看看','我們的都是少油少鹽喔']
def record():
        with Board() as board:
                print('請按下按鈕開始錄音.')
                board.button.wait_for_press()
                done = threading.Event()
                board.button.when_pressed = done.set

                def wait():
                        start = time.monotonic()
                        while not done.is_set():
                                duration = time.monotonic() - start
                                print('錄音中: %.02f 秒 [按下按鈕停止錄音]' % duration)
                                time.sleep(0.5)

                record_file(Lab, filename='recording.wav', wait=wait, filetype='wav')
def record_voice():
        count = 1
        while count>0:
                record()
                count -=1
                #print("播放音檔...")
                #play_wav("recording.wav")
def extract_chinese(string):
   # string_split=''
    string_chinese=""
    for char in string:
        if not '\u4e00' <= char <= '\u9fa5':
            string_chinese=string_chinese+""
        else:
            string_chinese=string_chinese+char
    return string_chinese

def askForService(token, data):
    # HOST, PORT 記得修改
    HOST = "140.116.245.149"
    PORT = 2802
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    model = "Minnan"
    #model = "dnn_S06"
    #model = "Chi_base"
    try:
        sock.connect((HOST, PORT))
        msg = bytes(token + "@@@", "utf-8") + struct.pack("8s",bytes(model, encoding="utf8")) + b"P" + data
        msg = struct.pack(">I", len(msg)) + msg  # msglen
        sock.sendall(msg)
        received = str(sock.recv(1024), "utf-8", errors='ignore')
    finally:
        sock.close()

    return received

def process(token, data):
    # 可在此做預處理
    # 送出
    result = askForService(token, data)
    # 可在此做後處理
    return result

def askForTTS(token, data, model="F14"):
    # HOST, PORT 記得修改
    global HOST_TTS
    global PORT_TTS
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    received = ""
    try:
        sock.connect((HOST_TTS, PORT_TTS))
        msg = bytes(token+"@@@"+data+"@@@"+model, "utf-8")
        msg = struct.pack(">I", len(msg)) + msg
        sock.sendall(msg)

        with open('output.wav','wb') as f:
            while True:
                # print("True, wait for 15sec")
                # time.sleep(15)

                l = sock.recv(8192)
                # print('Received')
                if not l: break
                f.write(l)
        print("File received complete")
    finally:
        sock.close()
    return "OK"
### Don't touch

def processTTS(token,data):
    # 可在此做預處理
    # 送出
    result = askForTTS(token,data)
    # 可在此做後處理
    return result

def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    StartTime = time.time()
    StopTime = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()

    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2

    return distance
def reply(input):
    # Download data
    #data_utils.download_data("./")
    ws = WS("./data")
    #print(input)
    # Run WS-POS-NER pipeline
    sentence_list = [input,]
    word_sentence_list = ws(sentence_list)

    # Release model
    del ws
    print(word_sentence_list)
    reply_word=''
    for i, sentence in enumerate(sentence_list):
        for [word] in zip(word_sentence_list[i]):
            if word in reply_key:
                reply_word =word
                break
    
    if reply_word!='':
        place=reply_key.index(reply_word)  
        answer=reply_ans[place]
        return(answer)
    else:
        answer="聽不懂你的問題請再問\n一次"
        return(answer)

def motor(*args):
    
    STEPS_PER_REVOLUTION = 32 * 64
    SEQUENCE = [[1, 0, 0, 0], 
                [1, 1, 0, 0],
                [0, 1, 1, 0],
                [0, 0, 1, 1]]


    STEPPER_PINS = [17,18,27,22]
    for pin in STEPPER_PINS:
        GPIO.setup(pin,GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    
    SEQUENCE_COUNT = len(SEQUENCE)
    PINS_COUNT = len(STEPPER_PINS)
    
    sequence_index = 0
    direction = 1
    steps = 0
    
    if len(sys.argv)>1:
        wait_time = int(sys.argv[1])/float(1000)
    else:
        wait_time = 10/float(1000)
    
    try:
        print('按下 Ctrl-C 可停止程式')
        while True:
            for pin in range(0, PINS_COUNT):
                GPIO.output(STEPPER_PINS[pin], SEQUENCE[sequence_index][pin])
    
            steps += direction
            if steps >= STEPS_PER_REVOLUTION:
                direction = -1
            elif steps < 0:
                direction = 1
    
            sequence_index += direction
            sequence_index %= SEQUENCE_COUNT
    
            #print('index={}, direction={}'.format(sequence_index, direction))
            time.sleep(wait_time)
    except KeyboardInterrupt:
        print('關閉程式')
    finally:
        GPIO.cleanup()


def display_text(text, *args):
    #disp.clear()
    if len(args) < 2:
        FONT_SIZE = 12
    elif len(args) == 2:
        FONT_SIZE = 10
    else:
        FONT_SIZE = 8

    disp = Adafruit_SSD1306.SSD1306_128_32(rst = 0)

    disp.begin()
    disp.clear()
    disp.display()

    width = disp.width
    height = disp.height

    # 1 bit pixel
    image = Image.new('1', (width, height))
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype("./ARIALUNI.TTF", FONT_SIZE)
    #font = ImageFont.load_default()

    draw.rectangle((0, 0, width-1, height-1), outline = 0, fill = 0)

    draw.text((0, 0), text, font = font, fill = 255)

    if len(args) > 0:
        for i, item in enumerate(args):
            draw.text((0, (i + 1) * FONT_SIZE-1), item, font = font, fill = 255)

    disp.image(image)
    disp.display()
    time.sleep(1)
    #disp.clear()
    #disp.display()
def clear_text(*args):
    disp = Adafruit_SSD1306.SSD1306_128_32(rst = 0)
    disp.begin()
    disp.clear()
if __name__ == "__main__":
    #GPIO.cleanup()
    HOST_TTS, PORT_TTS = "140.116.245.146", 10012
    token_tts = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3OTEyOTMxMzMsImlhdCI6MTYzMzYxMzEzMywic3ViIjoiIiwiYXVkIjoid21ta3MuY3NpZS5lZHUudHciLCJpc3MiOiJKV1QiLCJ1c2VyX2lkIjoiMjkwIiwibmJmIjoxNjMzNjEzMTMzLCJ2ZXIiOjAuMSwic2VydmljZV9pZCI6IjI0IiwiaWQiOjM5Niwic2NvcGVzIjoiMCJ9.XtqCCNnmc6tiNIOvcCsY6_vX-IjQFreYQWeU3BqXAvhZYCnjRUZvkcQcRLo-FjUikviipwRRYZhBGXK2Pd2xK8gfNu7LKRGh9V3sPvHIHn4MxC-YzV0tjQItGyIDW2w708YJQffx3v4A7wxnj3sjkxDxHIS8LApRcgk7Cd3Rdig"
    dist = distance()
    print(dist)
    time.sleep(1)
    GPIO.cleanup()
    
    
    if len(sys.argv)>1:
        wait_time = int(sys.argv[1])/float(1000)
    else:
        wait_time = 10/float(1000)
    answer ="你好，請問今天要問什麼問題呢"
    
    if (dist<=300):
        print (dist)
        display_text("哩賀")
        for i in range(1):
            print("Client : ",processTTS(token_tts,answer))
            os.system("aplay output.wav")
        while True:
            record_voice()
            token = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NDkxNjUxNTgsImlhdCI6MTYzMzYxMzE1OCwic3ViIjoiIiwiYXVkIjoid21ta3MuY3NpZS5lZHUudHciLCJpc3MiOiJKV1QiLCJ1c2VyX2lkIjoiMjkwIiwibmJmIjoxNjMzNjEzMTU4LCJ2ZXIiOjAuMSwic2VydmljZV9pZCI6IjMiLCJpZCI6Mzk3LCJzY29wZXMiOiIwIn0.V5H83lIze4RNTf6AGZUf34e6XVtlnVlpUHBLbdJUhL4KK4KPUWDQ3jcallP676OxRVZFn9ExcfxVPhnIZWyVIoxJr09Nothe16_gtLVQVxFNWtbPm5qCaWEEQZeY9vcvQwkI9wMzf_z-xWi0v7bkkqhaAK59qtQZDgYF7r5ztyM" # 需要申請
            file_name = "recording.wav"
            file = open(r"./{}".format(file_name), 'rb')
            data = file.read()
            total_time = 0
            count = 0.0
            speech_to_text=process(token, data)
            input_sentence=extract_chinese(speech_to_text)
            print(input_sentence)
            answer_ques = reply(input_sentence)
            if(answer_ques=="再見"):
                display_text("再見")
                display_text(" ")
                GPIO.cleanup()
                break
            elif (answer_ques=="風扇"):   # 開風扇的answer question
                display_text("稍等，馬上為您開風扇\n按下鍵盤關閉風扇")
                motor()
                display_text("歡迎繼續提問問題")
            else:
                display_text(answer_ques)
                print (answer_ques)
            for i in range(1):
                print("Client : ",processTTS(token_tts,answer_ques))
                os.system("aplay output.wav")
        

     
 
 
