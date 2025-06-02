# SoundCloud reposts webscraper for Sour_Cream_Pringles@soundcloud.com
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver import Firefox, Chrome
from selenium.webdriver import FirefoxOptions, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
from os import path as Path
from os import system, getenv
from bs4 import BeautifulSoup
import argparse
from random import uniform
from signal import signal, SIGINT, SIGTERM, SIGQUIT
from time import sleep
import traceback
from sys import stderr

from dotenv import load_dotenv, find_dotenv
# Load the .env file using find_dotenv(), which searches for the .env file starting from the current directory
load_dotenv(dotenv_path=find_dotenv(),  # Or BASE_DIR/'.env',
            verbose=True,               # Print verbose output for debugging purposes
            override=True)              # Override system environment variables with values from .env

# By using override=True, the system environment variables will be overridden by the values from the .env file
# This ensures that you access the latest values from the .env file every time you run the script

# Globals
driver: WebDriver
page_source: str
continue_scrolling = True
scrolling_started = False

def print_err(*args, **kwargs):
    print(*args, file=stderr, **kwargs)

def handleInterrupt(signal, frame):
    '''Intended to stop scrolling the page early so page_source can be captured
    and processed when the user sends a keyboard interrupt Ctrl+C for SIGINT or Ctrl+\ for SIGQUIT

    WARNING: Sending SIGINT to the parent process (e.g. shell when invoking SC-reposts-scraper.py,
    or the executable 'code' when running this script in a vscode debug session) will also kill the webdriver marionette process
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

    if use_chrome:
        chromeOptions = ChromeOptions()
        # potential workaround for SessionNotCreatedException: ... DevToolsActivePort file doesn't exist (CONSIDERED UNSECURE)
        #chromeOptions.add_argument("--no-sandbox") 
        # current workaround for SessionNotCreatedException: ... DevToolsActivePort file doesn't exist
        chromeOptions.add_argument("--remote-debugging-pipe")
        if headless:
            chromeOptions.add_argument("--headless")
        driver = Chrome(options=chromeOptions)
    else:
        fireFoxOptions = FirefoxOptions()
        fireFoxOptions.add_argument("-profile")
        profile=getenv("FF_PROFILE") # path to custom firefox profile dir. Custom profiles can increase memory limits
        fireFoxOptions.add_argument(profile)
        if headless:
            fireFoxOptions.add_argument("-headless")
        driver = Firefox(options=fireFoxOptions)
    driver.get(url)    
    print("loaded page")

    global LONG_TIMEOUT
    LONG_TIMEOUT = 3.5
    cookies_banner_xpath = '//*[@id="onetrust-reject-all-handler"]'
    try:
        reject_cookies_button = WebDriverWait(driver, timeout=LONG_TIMEOUT, poll_frequency=0.2).until(
            EC.visibility_of_element_located(
                (By.XPATH, cookies_banner_xpath)
            )
        )
    except TimeoutException:
        pass
    else:
        # click Reject All cookies button
        try:
            click_reject_chain = ActionChains(driver)
            click_reject_chain.click(reject_cookies_button)
            click_reject_chain.perform()
            print("Clicked Reject All button on cookies banner")
            sleep(2.5) # to make it more realistic
        except Exception as ex:
            print("~~~~~~~~~~~~~~~~~~~")
            traceback.print_tb(ex.__traceback__)
            print("~~~~~~~~~~~~~~~~~~~")
            print("Error when clicking Reject All button on cookies banner")
            pass


    try:
        # grab first song album art for starting reference point to scroll on page
        first_art = WebDriverWait(driver, timeout=LONG_TIMEOUT, poll_frequency=0.2).until(
                        EC.visibility_of_element_located(
                            (By.CLASS_NAME, "sound__artwork")            
                        )
                    )
        art_size = first_art.rect

        # https://stackoverflow.com/questions/44777053/selenium-movetargetoutofboundsexception-with-firefox
        # Browsers other than Firefox treat Webdrivers move_to_element action as scroll to part
        # of page with element, then hover over it. Firefox seems to have taken a hardline stance
        # that move_to_element is just "hover over" and we are waiting for a scroll action to fix this.
        # For now you have to workaround this bug using javascript
        driver.execute_script("arguments[0].scrollIntoView();", first_art)

        actions = ActionChains(driver)
        actions.move_to_element_with_offset(first_art,
                                            art_size["width"] + 1,
                                             art_size["height"] + 1)
        actions.send_keys(Keys.PAGE_DOWN)
        actions.perform()
        print("got first art cover and did first scroll down")
    except Exception as ex:
        print('\nEncountered exception type: ({}) while trying to grab first song album art')
        print("Error message: " + str(ex))
     
    try:
        scrollReposts(driver)
    except Exception as ex:
        print('\nEncountered exception type: ({}) in scrollReposts'.format(type(ex)))
        print("Error message: " + str(ex))
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        traceback.print_tb(ex.__traceback__)
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    finally:
        try:
            # # Make a copy of relevant data, because Selenium will throw if
            # # you try to access the properties after the driver quit
            page_source = driver.page_source
            driver.close()
            driver.quit()
        except Exception as ex:
            print('\nEncountered exception type: ({}) after scrollReposts'.format(type(ex)))
            print("Error message: " + str(ex))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            traceback.print_tb(ex.__traceback__)
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

def scrollReposts(driver: WebDriver):
    global continue_scrolling, scrolling_started
    scrolling_started = True
    print("Scrolling started")
    startTime = datetime.now()
    scrollCount = 0
    # delimiter of reposts page, signals bottom of reposts list
    # <div class="paging-eof sc-border-light-top" title=""></div>
    eof_css_selector_name = "paging-eof"
    eof_css_selector = "." + eof_css_selector_name
    SHORT_TIMEOUT  = 0.3
    # variables for checking whether song list loading has stalled
    base_pause = 1.0
    songs_list_total = 0
    ul_song_list_xpath = f"//div[contains(@class,'userReposts')]/ul[contains(@class, 'soundList')]"
    song_count_checkpoints = {10}
    checkpoint_retries = 0
    maximum_checkpoint_retries = 10
    scroll_key=Keys.PAGE_DOWN # Keys.END

    while continue_scrolling:
        if scrollLimit > 0 and scrollCount > scrollLimit:
            print(f"scroll limit hit, scrolled {scrollCount} times")
            break
        scrollCount += 1
        # Progress display of scrolling, with message that updates on one line
        # (rather than printing newlines, it writes over the last line of output using '\r' carriage return)
        print(f"scrolled {scrollCount} times", end='\r') # comment out when debugging, since this clobbers other stdout messages

        # randomize the wait time to avoid bot detection
        pause = uniform(0.01, 1.0) + base_pause
        sleep(pause)

        actions = ActionChains(driver)
        actions.send_keys(scroll_key)
        actions.perform()
        try: # wrap all selenium calls that can throw in an outer try block
            try: # check for bot detection
                captcha_url='geo.captcha-delivery.com'
                xpath_to_captcha=f"//iframe[contains(@src, '{captcha_url}')]"
                # (X path) ^^ to iframe for captcha_url 

                # if we see this iframe, we were redirected to a bot detection webpage with a captcha
                bot_dectection_iframe = WebDriverWait(driver, timeout=SHORT_TIMEOUT, poll_frequency=0.1).until(
                    EC.frame_to_be_available_and_switch_to_it(
                        (By.XPATH, xpath_to_captcha)
                    )
                )
            except TimeoutException:
                # keep scrolling, have not been detected yet
                pass
            else:
                isFound = captcha_url in bot_dectection_iframe.get_attribute("src") and bot_dectection_iframe.is_displayed
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

            # # Previous strategy to wait for the loading spinner to appear and disappear 
            # # is invalid because the loading spinner never disappears (see 4c1be3d)
            # # So instead we'll count the number of songs in the lazy loading list after certain scroll checkpoints
            # # to see if it has not increased before we reach the end of the page, since that could mean
            # # the server has timed out or another error has occurred that caused the lazy loading list to
            # # stop loading songs. 
            if scrollCount in song_count_checkpoints:
                try:
                    # pause before counting all song elements. 
                    # There is a chance the page will freeze as the page load times progress
                    sleep(LONG_TIMEOUT)
                    checkpoint_songs_list=driver.find_element(By.XPATH, ul_song_list_xpath)
                    songs_list_new_count=int(checkpoint_songs_list.get_attribute("childElementCount"))
                    if not songs_list_total < songs_list_new_count:
                        print_err("count of songs in list has not changed since last check")
                        if checkpoint_retries > maximum_checkpoint_retries:
                            print_err("page is likely frozen and won't continue to load")
                            # stop scrolling and save the page
                            continue_scrolling = False
                            continue
                        else:
                            checkpoint_retries += 1
                            print_err(f"checkpoint fail with count: {songs_list_new_count} at scrollCount {scrollCount}. Retries: {checkpoint_retries}") 
                            # add more time to the pause between scrolls to allow SoundCloud time to load
                            base_pause += LONG_TIMEOUT
                            # force another checkpoint to occur on an upcoming loop relatively soon
                            song_count_checkpoints.add(scrollCount + 5)
                    else:
                        # lazy list is performing well, update song total
                        print_err(f"checkpoint passed with song_count: {songs_list_new_count} at scrollCount {scrollCount}") 
                        # update song total
                        songs_list_total=songs_list_new_count
                        # reset checkpoint_retries 
                        checkpoint_retries=0
                        # increase pause between scroll cycles. Even though the list loading hasn't frozen yet,
                        # over time the page load times always increase and memory usage grows, so the time buffer
                        # should increase gradually no matter what. It increases more in a failure case, however (See above)
                        base_pause += SHORT_TIMEOUT
                        # force another checkpoint to occur on an upcoming loop in the future
                        newCheckpointInterval=10
                        if scrollCount >= 100:
                            newCheckpointInterval=20
                        if scrollCount >= 500:
                            newCheckpointInterval=50
                        if scrollCount >= 1000:
                            newCheckpointInterval=100
                            base_pause += SHORT_TIMEOUT
                        if scrollCount >= 1500:
                            newCheckpointInterval=150
                            base_pause += SHORT_TIMEOUT
                        if scrollCount >= 2000:
                            newCheckpointInterval=200
                            base_pause += SHORT_TIMEOUT
                        if scrollCount >= 3000:
                            newCheckpointInterval=250
                            base_pause += SHORT_TIMEOUT
                        if scrollCount >= 4000:
                            base_pause += SHORT_TIMEOUT/2
                        if scrollCount >= 5000:
                            base_pause += SHORT_TIMEOUT/2
                        if scrollCount >= 6000:
                            base_pause += SHORT_TIMEOUT/2
                        if scrollCount >= 7000:
                            base_pause += SHORT_TIMEOUT/2
                        if scrollCount >= 8000:
                            base_pause += SHORT_TIMEOUT/2
                        if scrollCount >= 9000:
                            base_pause += SHORT_TIMEOUT/2
                        if scrollCount >= 10000:
                            base_pause += SHORT_TIMEOUT/2
                        song_count_checkpoints.add(scrollCount + newCheckpointInterval)

                        if scrollCount % 1000 == 0:
                            text=checkpoint_songs_list.get_attribute("outerHTML")
                            save(f"<html>{text}</html>", ".", "checkpoint_reposts")
                except Exception as ex:
                    print('\nEncountered exception type: ({}) while checking song list count'.format(type(ex)))
                    print("Error message: " + str(ex))
                    raise ex


            try: # keep scrolling until the EOF element is found, signaling the end of the page has been reached
                eof_element = WebDriverWait(driver, timeout=SHORT_TIMEOUT, poll_frequency=0.1).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, eof_css_selector)
                    )
                )
            except TimeoutException:
                # a Timeout means we haven't reached the EOF element yet
                continue
            else:
                isFound = eof_css_selector_name in eof_element.get_attribute("class") and eof_element.is_displayed
                continue_scrolling = not isFound
                if isFound:
                    print(f"\nFinished scrolling to {eof_css_selector_name}")
        except Exception as ex:
            print('\nEncountered exception type: ({}) while scrolling'.format(type(ex)))
            print("Error message: " + str(ex))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            traceback.print_tb(ex.__traceback__)
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            # stop scrolling because of unexpected exception
            break
    
    endTime = datetime.now()
    execution = endTime - startTime
    print(f"\nscrolling execution time was {execution}")
    print(f"scrolled {scrollCount} times with song count {songs_list_total}")

def save(text, dir, filename):
    file_name = filename + '.html'
    file_path = Path.join(dir, file_name)
        
    with open(file_path, 'w') as fh:
        fh.write(text)
    
    # debug
    print("~~~~~~~~~~~~~downloaded html~~~~~~~~~~~~~")
    print(f"saved to {file_path}")
    return(file_path)
    
def parse_html():
    print("parsing html into soup")
    return BeautifulSoup(page_source, 'html.parser')

def transform(soup: BeautifulSoup):
    print("processing soup")
    songs = []
    if soup is None:
        return
    try:
        # if soup comes from whole page_source or checkpoint_songs_list
        ul_repost_list = soup.find("ul", class_="soundList sc-list-nostyle")
        if ul_repost_list is None:
            return
    except Exception as ex:
        print('\nEncountered exception type: ({}) while transforming soup'.format(type(ex)))
        print("Error message: " + str(ex))
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
    parser.add_argument("--chrome",
                        help="run with Chrome (default Firefox)",
                        action='store_true')
    parser.add_argument("--headless",
                        help="run webdriver in headless mode",
                        action='store_true')
    args = parser.parse_args()

    pathToHtml = ''
    if hasattr(args, "saved_page_path"):
        pathToHtml = args.saved_page_path
    scrollLimit = 0
    if hasattr(args, "scroll_limit"):
        scrollLimit = args.scroll_limit
    use_chrome = False
    if hasattr(args, "chrome"):
        use_chrome =  args.chrome
    headless = False
    if hasattr(args, "headless"):
        headless = args.headless
    
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
        repostsFileName="reposts-1"
        try:
            for song in songs_array:
                if not song.endswith("https://soundcloud.com"):
                    songList = songList + song + '\n'
            if songList != '':
                with open(f"{repostsFileName}.txt", 'x') as fh:
                    fh.write(songList)
                print(f"wrote songs to {repostsFileName}.txt")
        except FileExistsError:
            print(f"{repostsFileName}.txt already exists. Attempting to write to a new file: {repostsFileName}1.txt")
            with open(f"{repostsFileName}1.txt", 'x') as fh:
                fh.write(songList)
            print(f"wrote songs to {repostsFileName}1.txt")
        except Exception as ex:
            print('Error writing songs to file {}'.format(type(ex)))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            traceback.print_tb(ex.__traceback__)
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            if pathToHtml == '':
                save(page_source, '.', "raw_reposts")
            else:
                pathToHtmlBackup = pathToHtml + '_bak'
                save(page_source, '.', pathToHtmlBackup)
                
    else:
        print("Sorry, could not extract data")
        if pathToHtml == '':
            save(page_source, '.', "raw_reposts")
        else:
            pathToHtmlBackup = pathToHtml + '_bak'
            save(page_source, '.', pathToHtmlBackup)

    endTime = datetime.now()
    execution = endTime - startTime
    print(f"total exectution time was {execution}")
