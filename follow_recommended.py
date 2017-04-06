import time
import sys
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import random

sample_num = 10

num = "0"
if (len(sys.argv) == 2):
	num = sys.argv[1]
else:
	print ("Usage: python follow_recommended.py [botnum]")
	exit()

url = "https://twitter.com/who_to_follow/suggestions"
usr = "springIWthc"
pwd = "louisasimpson"

# LOG INTO TWITTER
browser = webdriver.Firefox()
time.sleep(1)

browser.get(url)
time.sleep(4)
login1 = browser.find_element_by_class_name("js-username-field")
time.sleep(1)
login2 = browser.find_element_by_class_name("js-password-field")
time.sleep(1)
login1.send_keys(usr + num)
time.sleep(1)
login2.send_keys(pwd)
time.sleep(1)
browser.find_element_by_css_selector("button.submit.btn.primary-btn").click()
time.sleep(3)

# SCROLL DOWN TO LOAD ENTIRE FEED
body = browser.find_element_by_tag_name('body')
for _ in range(4):
	body.send_keys(Keys.PAGE_DOWN)
	time.sleep(0.3)

# get the follow buttons and click the first sample_num of them
buttons = browser.find_elements_by_class_name('user-actions-follow-button.js-follow-btn.follow-button.btn')
i = 0
while (i < sample_num):
	buttons[i].click()
	time.sleep(1.0)
	i += 1
