# SoundCloud reposts webscraper for Sour_Cream_Pringles@soundcloud.com
from random import random, uniform
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
import time
import os
import pyautogui as pag
import math
from collections import namedtuple
from typing import NamedTuple

Point = NamedTuple('Point', [('x',float),('y',float)])

def extract(url: str):
    elem = None
    # uncomment for headless
    # fireFoxOptions = webdriver.FirefoxOptions()
    # fireFoxOptions.set_headless()
    # driver = webdriver.Firefox(firefox_options=fireFoxOptions)
    driver = webdriver.Firefox()
    driver.implicitly_wait(10)
    driver.get(url)
    
    global windowLocation
    windowLocation = driver.get_window_position()
    windowLocation = Point(float(windowLocation["x"]),
                            float(windowLocation["y"]))
    print(f"window location is {windowLocation}")
    
    global windowSize
    windowSize = driver.get_window_size()
    print(f"window size is {windowSize}")

    global windowNames
    windowNames = driver.window_handles

    # Expand to fullscreen so absolute coordinates will not require
    #  compensation for window position, browser toolbar, tabs bar, etc.
    
    windowLocation = Point(windowLocation.x+1, windowLocation.y+1)
    pag.moveTo(windowLocation.x,windowLocation.y)
    
    pag.click()
    pag.press('F11')

    pag.moveTo(windowSize['width']/2,windowSize['height']/2)
    global viewPort
    viewPort = driver.find_element(By.TAG_NAME, "body")

    try:
        getReposts(driver)

        # Make a copy of relevant data, because Selenium will throw if
        # you try to access the properties after the driver quit
        elem = {
            "text": ""
        }
    finally:
        driver.close()
        
    return elem

def getReposts(driver: webdriver):
    # delimiter of reposts page, signals bottom of reposts list
    css_selector = ".paging-eof"
    # <div class="paging-eof sc-border-light-top" title=""></div>
    condition = True
    while condition:
        pag.press('pagedown')
        time.sleep(1)
        # WebDriverWait(driver, 10).until(
        pagingEOF = EC.visibility_of_all_elements_located(
            EC.visibility_of(
                driver.find_element(By.CSS_SELECTOR, css_selector)            
            )
        )
        if pagingEOF != None:
            condition = False

def transform(elem):
    return elem["text"]

if __name__ == "__main__":
    # debug: test with random profile
    url = "https://soundcloud.com/notsorhody/reposts"

    # debug: test with Zonz's profile
    # url = "https://soundcloud.com/user-636779687/reposts"

    elem = extract(url)
    if elem is not None:
        text = transform(elem)
        print(text)
    else:
        print("Sorry, could not extract data")