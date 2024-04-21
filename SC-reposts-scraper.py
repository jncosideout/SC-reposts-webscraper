# SoundCloud reposts webscraper for Sour_Cream_Pringles@soundcloud.com
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
from os import path as Path
from os import system, getenv
from pathlib import PurePath
from bs4 import BeautifulSoup
import argparse
from random import uniform
from signal import signal, SIGINT, SIGTERM, SIGQUIT
from time import sleep
import traceback

from dotenv import load_dotenv, find_dotenv
# Load the .env file using find_dotenv(), which searches for the .env file starting from the current directory
load_dotenv(dotenv_path=find_dotenv(),  # Or BASE_DIR/'.env',
            verbose=True,               # Print verbose output for debugging purposes
            override=True)              # Override system environment variables with values from .env

# By using override=True, the system environment variables will be overridden by the values from the .env file
# This ensures that you access the latest values from the .env file every time you run the script

# Globals
driver: Firefox
page_source: str
continue_scrolling = True
scrolling_started = False

def handleInterrupt(signal, frame):
    '''Intended to stop scrolling the page early so page_source can be captured
    and processed when the user sends a keyboard interrupt Ctrl+C for SIGINT or Ctrl+\ for SIGQUIT

    WARNING: Sending SIGINT to the parent process (e.g. shell when invoking SC-reposts-scraper.py
    or when running this script in a vscode debug session) will also kill the webdriver marionette process
    causing the webdriver to throw several errors, such as urllib3.exceptions.MaxRetryError
    or selenium-specific errors when accessing webdriver properties

    Therefore, only send SIGINT to the python process running the script itself.
    You can do this by using sh -c and exec to get the command's PID even before it runs.
    `sh -c 'echo $$; exec python SC-reposts-scraper.py'`
    This starts a new shell, prints the PID of that shell, and then uses the exec builtin to replace
    the shell with your command (running this python script), ensuring it has the same PID.
    Of course, you can add '&' to the end of this command to run it in the background. 
    When you are ready to terminate the script early, run the kill command:
    `kill [-TERM|-INT|-QUIT] $PID` where $PID is the process ID echoed from the last command.
    For convenience, you can save $$ to a file called MYPID instead of echoing it,
    then run ./kill-TERM_MYPID with bash which reads MYPID from that file.
    '''
    signal_name = ''
    match signal:
        case 2:
            signal_name = 'SIGINT'
        case 3:
            signal_name = 'SIGQUIT'
        case 15:
            signal_name = 'SIGTERM'
        case _:
            signal_name = 'Unknown: {}'.format(str(signal))
            
    global continue_scrolling
    print(f'{signal_name} System signal captured')
    if scrolling_started == True:
        print('scrolling will not continue')
        continue_scrolling = False

signal(SIGINT, handleInterrupt)
signal(SIGTERM, handleInterrupt)
signal(SIGQUIT, handleInterrupt)

def scrapeReposts(url: str):
    global page_source, driver
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.add_argument("-profile")
    profile=getenv("FF_PROFILE")
    fireFoxOptions.add_argument(profile)    
    # uncomment for headless
    # fireFoxOptions.add_argument("-headless")

    driver = webdriver.Firefox(options=fireFoxOptions)

    driver.get(url)    
    print("loaded page")

    try:
        # pause to avoid bot detection
        pause = 3.0
        sleep(pause)
        scrollReposts(driver)
    finally:
        # # Make a copy of relevant data, because Selenium will throw if
        # # you try to access the properties after the driver quit
        page_source = driver.page_source
        driver.close()
        driver.quit()

def scrollReposts(driver: webdriver):
    global continue_scrolling, scrolling_started
    scrolling_started = True
    print("Scrolling started")
    startTime = datetime.now()
    scrollCount = 0
    # delimiter of reposts page, signals bottom of reposts list
    # <div class="paging-eof sc-border-light-top" title=""></div>
    css_selector_name = "paging-eof"
    css_selector = "." + css_selector_name

    while continue_scrolling:
        if scrollLimit > 0 and scrollCount > scrollLimit:
            print(f"scroll limit hit, scrolled {scrollCount} times")
            break
        scrollCount += 1
        # Progress display of scrolling, with message that updates on one line
        # (rather than printing newlines, it writes over the last line of output using '\r' carriage return)
        print(f"scrolled {scrollCount} times", end='\r')

        actions = ActionChains(driver)
        actions.send_keys(Keys.END)
        actions.perform()
        # randomize the wait time to avoid bot detection
        pause = uniform(1, 4.0)
        try:
            try:
                captcha_url='geo.captcha-delivery.com'
                xpath_to_captcha=f"//iframe[contains(@src, '{captcha_url}')]"
                # (X path) ^^ to iframe for captcha_url 

                # if we see this iframe, we were redirected to a bot detection webpage with a captcha
                bot_dectection_iframe = driver.find_element(By.XPATH, xpath_to_captcha)
            except NoSuchElementException:
                # keep scrolling, have not been detected yet
                pass
            else:
                isFound = captcha_url in bot_dectection_iframe.get_attribute("src")
                if isFound:
                    AUDIO_ALERT = getenv('AUDIO_ALERT')
                    if AUDIO_ALERT != '' and Path.isfile(AUDIO_ALERT):
                        system(f'mpv {AUDIO_ALERT}')
                    print(f"\nEncountered bot detection page from {captcha_url}!")
                print('Pausing for user intervention (webdriver was caught by bot detection)')
                # read from keyboard to continue (allow human user to pass the captcha and to continue webscraping)
                user_input = input("Enter 'y' after you beat the captcha. Enter anything else or nothing to finish scrolling and process page")
                if user_input == 'y':
                    print('User beat captcha, continue scrolling')
                    continue
                else:
                    print('User did not beat captcha, quit scrolling, process the page early')
                    break

            try:
                # keep scrolling until the EOF element is found, signaling the end of the page has been reached
                eof_element = WebDriverWait(driver, timeout=pause).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, css_selector)
                    )
                )
            except TimeoutException:
                # a Timeout means we haven't reached the EOF element yet
                continue
            else:
                isFound = css_selector_name in eof_element.get_attribute("class")
                continue_scrolling = not isFound
                if isFound:
                    print(f"\nFinished scrolling to {css_selector_name}")
        except Exception as ex:
            print('\nEncountered exception type ({}) while scrolling'.format(type(ex)))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            traceback.print_tb(ex.__traceback__)
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            # stop scrolling because of unexpected exception
            break
    
    endTime = datetime.now()
    execution = endTime - startTime
    print(f"\nscrolling execution time was {execution}")

def save(text, dir):
    file_name = PurePath(url).name + '.html'
    file_path = Path.join(dir, file_name)
        
    with open(file_path, 'w') as fh:
        fh.write(text)
    
    # debug
    print("~~~~~~~~~~~~~downloaded html~~~~~~~~~~~~~")
    print(f"saved to {file_path}")
    return(file_path)
    
def parse_html():
    return BeautifulSoup(page_source, 'html.parser')

def transform(soup: BeautifulSoup):
    print("processing soup")
    songs = []
    if soup is None:
        return
    div_repost_lazyList = soup.find("div", class_="userReposts lazyLoadingList")
    try:
        ul_repost_list = div_repost_lazyList.contents[0]
    except Exception as ex:
        print('Encountered exception type ({}) while transforming soup'.format(type(ex)))
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        traceback.print_tb(ex.__traceback__)
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        return

    for repost_item in ul_repost_list.children:
        if repost_item is not None:
            coverArt_link = repost_item.find("a", class_="sound__coverArt")
            song = coverArt_link.get('href')
            songs.append(song)
    print("done")            
    return songs


def run():
    startTime = datetime.now()
    soup = parse_html()
    content = transform(soup)
    songs_list = []
    if content is None:
        return
    for song in content:
        stripped_song = song.strip() if song is not None else ''
        full_url = "https://soundcloud.com" + stripped_song
        songs_list.append(full_url)

    endTime = datetime.now()
    execution = endTime - startTime
    print(f"parsing execution time was {execution}")
    return songs_list

if __name__ == "__main__":
    SC_PROFILE=getenv('SC_PROFILE')
    url = f"https://soundcloud.com/{SC_PROFILE}/reposts"

    startTime = datetime.now()

    parser = argparse.ArgumentParser("SC-reposts-scraper", argument_default=argparse.SUPPRESS)
    parser.add_argument("saved_page_path",
                        metavar="path/to/reposts.html",
                        nargs='?',                        
                        help="path to html file of saved reposts webpage to parse")
    parser.add_argument("--scroll-limit",
                        nargs='?',
                        help="limit for number of times webdriver scrolls with pageDown",
                        type=int)
    args = parser.parse_args()

    pathToHtml = ''
    if hasattr(args, "saved_page_path"):
        pathToHtml = args.saved_page_path
    scrollLimit = 0
    if hasattr(args, "scroll_limit"):
        scrollLimit = args.scroll_limit
    
    if pathToHtml != '':
        try:
            print(f'parsing local html {pathToHtml}')
            with open(pathToHtml, 'r') as fh:
                page_source = fh.read()
        except (FileNotFoundError, OSError) as e:
            print(f'{pathToHtml} could not be opened')
            print(e)
            quit()
    else:
        scrapeReposts(url)
    
    songs_array = run()
    songList = ''

    if songs_array is not None:
        try:
            for song in songs_array:
                songList = songList + song + '\n'
            with open('reposts-1.txt', 'w') as fh:
                fh.write(songList)
            print("wrote songs to reposts-1.txt")
        except Exception as ex:
            print('Error writing songs to file {}'.format(type(ex)))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            traceback.print_tb(ex.__traceback__)
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            if pathToHtml == '':
                save(page_source, '.')
    else:
        print("Sorry, could not extract data")
        if pathToHtml == '':
            save(page_source, '.')

    endTime = datetime.now()
    execution = endTime - startTime
    print(f"total exectution time was {execution}")