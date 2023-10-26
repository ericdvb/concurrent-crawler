import requests
import concurrent.futures
import multiprocessing
import re
import os
import queue
import functools
from dotenv import load_dotenv
from supabase import create_client
from html_to_md import parse_to_markdown as subroutine
from Queue_with_qsize import MyQueue

load_dotenv()

supabase_url = os.environ.get('CRAWLER_SUPABASE_URL')
supabase_key = os.environ.get('CRAWLER_SUPABASE_KEY')
supabase_table_name = os.environ.get('CRAWLER_SUPABASE_TABLE')
supabase_username = os.environ.get('CRAWLER_SUPABASE_USER_EMAIL')
supabase_password = os.environ.get('CRAWLER_SUPABASE_USER_PASSWORD')
supabase = create_client(supabase_url, supabase_key)
supabase.auth.sign_in_with_password(credentials={ 'email': supabase_username, 'password': supabase_password })

def write_to_supabase(base_url, path, markdown):
    try:
        supabase.table(supabase_table_name).upsert(markdown).execute()
    except Exception as e:
        print('error writing to supabase table', e)

class Test:
    def __init__(self, url):
        if not re.match('http(s)?://', url):
            raise Exception("provided URL doesn't begin with http(s)://, please provide a url with this format")

        self.mp_manager = multiprocessing.Manager()
        self.urls_lock = self.mp_manager.Lock()
        self.markup_lock = self.mp_manager.Lock()
        self.markdown_lock = self.mp_manager.Lock()
        self.mpexecutor = None
        self.executor = None 
        self.thread_futures = {}
        self.process_futures = {}
        self.supabase_futures = {}
        self.markup_queue = MyQueue()
        self.markdown_queue = self.mp_manager.Queue()
        self.base_url = url
        self.urls_to_visit = self.mp_manager.list([url])

    def remove_done_future(self, futures_list, future):
        del futures_list[future]
        
    def start(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            with concurrent.futures.ProcessPoolExecutor(max_workers=8) as mpexecutor:
                self.executor = executor
                self.mpexecutor = mpexecutor
                i = 0
                ### Change this condition to <= 5 so we're not spamming sites while testing this
                ### Change it back if you really want to crawl the whole site
                # while (i <= (len(self.urls_to_visit) - 1) or
                while ((i <=5 ) or
                        len(self.thread_futures) > 0 or
                        len(self.process_futures) > 0 or
                        len(self.supabase_futures) > 0 or
                        self.markup_queue.qsize() > 0 or
                        self.markdown_queue.qsize() > 0):
                    ### Change this condition to <= 5 so we're not spamming sites while testing this
                    ### Change it back if you really want to crawl the whole site
                    # if (i <= (len(self.urls_to_visit) - 1)):
                    if (i <= 5):
                        ### Change this condition to [i:6:] so we're not spamming sites while testing this
                        ### Change it back if you really want to crawl the whole site
                        # for path in self.urls_to_visit[i::]:
                        for path in self.urls_to_visit[i:6:]:
                            i += 1
                            thread_future = self.executor.submit(self.get_markup, path)
                            self.thread_futures[thread_future] = {'future': thread_future, 'path': path}

                    done_threads, not_done_threads = concurrent.futures.wait(self.thread_futures, .1, concurrent.futures.FIRST_COMPLETED)
                    for future in done_threads:
                        path = self.thread_futures[future]['path']
                        process_future = self.mpexecutor.submit(
                            subroutine,
                            self.base_url,
                            path,
                            self.markup_queue.get(),
                            self.urls_to_visit,
                            self.urls_lock,
                            self.markdown_queue,
                            self.markdown_lock,
                            [])
                        self.process_futures[process_future] = {'future': process_future, 'path': path}
                        process_future.add_done_callback(functools.partial(self.remove_done_future, self.process_futures))
                        del self.thread_futures[future]

                    if not self.markdown_queue.empty():
                        try:
                            self.markdown_lock.acquire()
                            markdown_list = list()
                            try:
                                while (markdown := self.markdown_queue.get(timeout=.00001)) is not None:
                                    markdown_list.append(markdown)
                            except queue.Empty:
                                pass
                            self.markdown_lock.release()
                            supabase_future = self.executor.submit(write_to_supabase, self.base_url, path, markdown_list)
                            supabase_future.add_done_callback(functools.partial(self.remove_done_future, self.supabase_futures))
                            self.supabase_futures[supabase_future] = {'future': supabase_future, 'path': path}
                            print('finished writing to supabase')
                        except Exception as e:
                            print ('error spawning supabase write thread', e)
        
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