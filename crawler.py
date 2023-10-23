import requests
import concurrent.futures
import multiprocessing
import re
import os
from operator import itemgetter
from time import sleep
from dotenv import load_dotenv
from supabase import Client, create_client
from html_to_md import parse_to_markdown as subroutine
from Queue_with_qsize import MyQueue

load_dotenv()

class Test:
    def __init__(self, url):
        if not re.match('http(s)?://', url):
            raise Exception("provided URL doesn't begin with http(s)://, please provide a url with this format")

        supabase_url = os.environ.get('PENGUINAI_SUPABASE_URL')
        supabase_key = os.environ.get('PENGUINAI_SUPABASE_KEY')

        self.mp_manager = multiprocessing.Manager()
        self.urls_lock = self.mp_manager.Lock()
        self.markup_lock = self.mp_manager.Lock()
        self.mpexecutor = None
        self.executor = None 
        self.thread_futures = {}
        self.process_futures = {}
        self.markup_queue = MyQueue()
        self.base_url = url
        self.urls_to_visit = self.mp_manager.list([url])

        # self.supabase = create_client(supabase_url, supabase_key)

    def remove_done_future(self, future):
        print('done future found?:', self.futures.index(future) > -1)
        self.futures.remove(future)
        print('length of self.futures after removal', len(self.futures))
        
    def start(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            with concurrent.futures.ProcessPoolExecutor(max_workers=8) as mpexecutor:
                self.executor = executor
                self.mpexecutor = mpexecutor
                i = 0
                while (i <= (len(self.urls_to_visit) - 1) or
                        len(self.thread_futures) > 0 or
                        len(self.process_futures) > 0 or
                        self.markup_queue.qsize() > 0):
                    if (i <= (len(self.urls_to_visit) - 1)):
                        for path in self.urls_to_visit[i::]:
                            i += 1
                            thread_future = self.executor.submit(self.get_markup, path)
                            self.thread_futures[thread_future] = {'future': thread_future, 'path': path}

                    done_threads, not_done_threads = concurrent.futures.wait(self.thread_futures, .1, concurrent.futures.FIRST_COMPLETED)
                    for future in done_threads:
                        path = self.thread_futures[future]['path']
                        process_future = self.mpexecutor.submit(subroutine, self.base_url, path, self.markup_queue.get(), self.urls_to_visit, self.urls_lock, [])
                        self.process_futures[process_future] = {'future': process_future, 'path': path}
                        del self.thread_futures[future]

                    done_processes, not_done_processes = concurrent.futures.wait(self.process_futures, .1, concurrent.futures.FIRST_COMPLETED)
                    for future in done_processes:
                        print('finished inner processing loop iteration')
                        del self.process_futures[future]


    def prepend_base_url(self, path):
        if re.match('^/', path):
            return f'{self.base_url}{path}' 
        elif re.match('^https?://', path):
            return path

    def get_markup(self, url):
        print(f'START: request {url}', flush=True)
        response = requests.get(self.prepend_base_url(url))
        self.markup_lock.acquire()
        self.markup_queue.put(response)
        self.markup_lock.release()
        print(f'END: request {url}', flush=True)

def main(url=None):
    test_spawner = Test('https://www.brex.com')
    test_spawner.start()

if __name__ == "__main__":
    main()