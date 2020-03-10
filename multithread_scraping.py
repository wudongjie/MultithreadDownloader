#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from queue import Queue
import threading
import sys
import os
import pandas as pd
import shutil
import time
import gc
import argparse


def parse_command_line(argv):
    """Parse command line argument."""
    parser = argparse.ArgumentParser(description="Multithread downloader with selenium")
    parser.add_argument('csv_path', help="add the CSV files containing addresses of the pages")
    parser.add_argument("-n", "--name", help="add the name of the argument")
    parser.add_argument("-x", "--xpath", help="add the xpath of the argument")
    parser.add_argument("-i", "--id", help="add the id name of the argument")
    parser.add_argument("-t", "--tag", help="add the tag of the argument")
    parser.add_argument("-c", "--class_name", help="add the class of the argument")
    parser.add_argument("-s", "--css_selector", help="add the css selector of the argument")
    parser.add_argument("-m", "--multithread", default=10, help="set number of threads (default is 10)")
    parser.add_argument("-o", "--output_dir", default="data", help="set output directory (default is data)")
    arguments = parser.parse_args(argv[1:])
    return arguments



def enable_download_headless(browser,download_dir):
    """ save downloading file to download_dir """
    browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd':'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
    browser.execute("send_command", params)

def chrome_downloader():
    """
    instantiate a chrome options object so you can set the size and headless preference
    some of these chrome options might be uncessary but I just used a boilerplate
    change the <path_to_download_default_directory> to whatever your default download folder is located
    """
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--verbose')
    chrome_options.add_argument('--user-agent=%s' % user_agent)
    chrome_options.add_experimental_option("prefs", {
            "download.default_directory": "<path_to_download_default_directory>",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing_for_trusted_sources_enabled": False,
            "safebrowsing.enabled": False
    })
    chrome_options.add_argument("-js-flags=--expose-gc");
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    return chrome_options


def run_driver(url, args, download_dir, chrome_options):
    # initialize driver object and change the <path_to_chrome_driver> depending on your directory where your chromedriver should be
    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=r'chromedriver.exe')
    # function to handle setting up headless download
    enable_download_headless(driver, download_dir)
    driver.set_page_load_timeout(10)
    driver.get(url)
    # initialize an object to the location on the html page and click on it to download
    search_input = find_element(args, driver)
    search_input.click()
    time.sleep(1)
    print("Downloaded!")
    driver.quit()


def find_element(args, driver):
    """
    Use Arguments to specify the element to identify the download click in the page
    """
    if args.name:
        search_input = driver.find_element_by_name(args.name)
    elif args.xpath:
        search_input = driver.find_element_by_xpath(args.xpath)
    elif args.id:
        search_input = driver.find_element_by_id(args.id)
    elif args.tag:
        search_input = driver.find_element_by_tag_name(args.tag)
    elif args.class_name:
        search_input = driver.find_element_by_class_name(args.class_name)
    elif args.css_selector:
        search_input = driver.find_element_by_css_selector(args.css_selector)
    else:
        sys.exit('Please specify the type of element')
    return search_input


def run_scrapy(q, args, chrome_option, output_dir):
    while not q.empty():
        url, fname = q.get() # Load the queue
        # Files first downloaded into temporary folders to prevent file names overlapping
        download_dir = os.path.join(os.path.dirname(__file__), threading.current_thread().name)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        new_path = output_dir + "/" + str(fname) + ".csv"
        try:
            run_driver(url, args, download_dir, chrome_option)
            file_name = os.listdir(download_dir)[-1]
            origin_path = download_dir + "/" + file_name 
            if (os.path.isfile(origin_path)):
                # Move the file from temporary folders to output folders
                shutil.move(origin_path, new_path) 
            gc.collect()
        except TimeoutException as ex:
            print("Exception has been thrown. " + str(ex))
        except NoSuchElementException as se:
            print("Exception has been thrown. " + str(se))
        q.task_done()
    return True


def main():
    arguments = parse_command_line(sys.argv) #read the arguments
    q = Queue(maxsize=0) # open a queue
    num_threads= arguments.multithread
    output_dir = arguments.output_dir
    chrome_option = chrome_downloader() # Initialize the downloader
    df_url = pd.read_csv(arguments.csv_path) # Read url list from a csv file
    print("{0} websites are loaded".format(df_url.shape[0]))
    download_list = df_url["url"].tolist()
    name_list =df_url["file_name"].tolist()
    zipped_list = zip(download_list, name_list)
    [q.put((url, fname) ) for url, fname in zipped_list]
    print("Queue done! {0}".format(q.qsize()))
    for i in range(num_threads):
        worker = threading.Thread(target=run_scrapy, name='Temp{0}'.format(i), args=(q, arguments, chrome_option, output_dir))
        worker.start()
    q.join()
        

if __name__ == "__main__":
    main()
        

