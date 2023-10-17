import requests
import concurrent.futures
import multiprocessing
import re
import os
from operator import itemgetter
from time import sleep
from dotenv import load_dotenv
from supabase import Client, create_client
from testmodule import parse_to_markdown as subroutine

load_dotenv()

class Test:
    def __init__(self, url):
        if not re.match('http(s)?://', url):
            raise Exception("provided URL doesn't begin with http(s)://, please provide a url with this format")

        supabase_url = os.environ.get('PENGUINAI_SUPABASE_URL')
        supabase_key = os.environ.get('PENGUINAI_SUPABASE_KEY')

        self.mp_manager = None
        self.lock = None
        self.mpexecutor = None
        self.executor = None 
        self.thread_futures = []
        self.process_futures = []
        self.base_url = url
        self.urls_to_visit = [url]
        # self.supabase = create_client(supabase_url, supabase_key)

    def remove_done_future(self, future):
        print('done future found?:', self.futures.index(future) > -1)
        self.futures.remove(future)
        print('length of self.futures after removal', len(self.futures))
        
    def start(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            with concurrent.futures.ProcessPoolExecutor(max_workers=8) as mpexecutor:
                with multiprocessing.Manager() as mp_manager:
                    self.executor = executor
                    self.mpexecutor = mpexecutor
                    self.mp_manager = mp_manager
                    self.lock = mp_manager.Lock()
                    self.urls_to_visit = mp_manager.list()
                    i = 0
                    while (i <= (len(self.urls_to_visit) - 1) or
                           len(self.thread_futures) > 0 or
                           len(self.process_futures) > 0):
                        iteration_url = self.urls_to_visit[i]
                        i += 1
                        thread_future = self.executor.submit(self.get_markup, iteration_url)
                        self.thread_futures.append(thread_future)
                        response = thread_future.result()
                        process_future = self.mpexecutor.submit(subroutine, self.base_url, iteration_url, response)
                        self.process_futures.append(process_future)
                        links, markdown = process_future.result()
                        for link in links:
                            if link not in self.urls_to_visit:
                                self.urls_to_visit.append(link)
                        print('finished loop', markdown)

    def prepend_base_url(self, path):
        if re.match('^/', path):
            return f'{self.base_url}{path}' 
        elif re.match('^https?://', path):
            return path

    def get_markup(self, url):
        print(f'START: request {url}')
        response = requests.get(self.prepend_base_url(url))
        print(f'END: request {url}')
        return response

def main(url=None):
    test_spawner = Test('https://www.brex.com')
    test_spawner.start()

if __name__ == "__main__":
    main()