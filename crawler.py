import requests
from bs4 import BeautifulSoup
import concurrent.futures
import multiprocessing
import re
import os
from dotenv import load_dotenv
from supabase import Client, create_client
from parsetomd import main as parse_to_md

multiprocessing.set_start_method('spawn', True)
load_dotenv()

class Crawler:
    
    def __init__(self, url):
        if not re.match('http(s)?://', url):
            raise Exception("provided URL doesn't begin with http(s)://, please provide a url with this format")

        supabase_url = os.environ.get('PENGUINAI_SUPABASE_URL')
        supabase_key = os.environ.get('PENGUINAI_SUPABASE_KEY')

        self.mp_manager = None
        self.visited = None
        self.to_visit = None
        self.lock = None
        self.base_url = url
        self.mpexecutor = None
        self.executor = None 
        self.futures = []
        # self.supabase = create_client(supabase_url, supabase_key)

    def remove_done_future(self, future):
        print('done future found?:', self.futures.index(future) > -1)
        self.futures.remove(future)
        print('length of self.futures after removal', len(self.futures))
        
    def prepend_base_url(self, path):
        if re.match('^/', path):
            return f'{self.base_url}{path}' 
        elif re.match('^https?://', path):
            return path

    def start_crawling(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            with concurrent.futures.ProcessPoolExecutor(max_workers=8) as mpexecutor:
                with multiprocessing.Manager() as mp_manager:
                    self.executor = executor
                    self.mpexecutor = mpexecutor
                    self.mp_manager = mp_manager
                    self.to_visit = mp_manager.list([self.base_url])
                    self.visited = mp_manager.list([])
                    self.lock = mp_manager.Lock()
                    i = 0
                    while len(self.to_visit) or len(self.executor._threads) > 0 or self.executor._work_queue.qsize() > 0:
                        if len(self.futures) > 0:
                            print("loop iteration")
                            print('current number of threads:', len(self.futures))
                        # To prevent us from making an excessive number of requests while testing
                        # if i <= (len(self.to_visit) - 1):
                        if i <= (len(self.to_visit) - 1) and i < 10:
                            url = self.to_visit[i]
                            url_with_base = self.prepend_base_url(url)
                            fut = executor.submit(self.crawl, url_with_base)
                            self.visited.append(url)
                            self.futures.append(fut)
                            fut.add_done_callback(self.remove_done_future)
                            i += 1
                            print('visited length:', len(self.visited))
                            print('to_visit length', len(self.to_visit))

    def write_to_supabase(markdown, baseurl, path):
        # supabase.table('markdown').insert({ 'markdown': markdown, 'baseurl': baseurl, 'path': path }).execute()
        with open(f'{path.replace("/", "_")}', "r+") as f:
            print('writing file')
            f.write(str(markdown.prettify()))
            print('file written')

    def transform_to_markdown(self, response, url):
        lock, executor, mpexecutor = self['lock', 'executor', 'mpexecutor']
        parsed_response = BeautifulSoup(response.text, 'html.parser')
        links = parsed_response('a', href=re.compile(rf'^(/|{url})'))
        for link in links:
            potential_new_link = link['href']
            if potential_new_link not in self.to_visit:
                lock.acquire()
                self.to_visit.append(potential_new_link)
                lock.release()

        return parse_to_md(parsed_response)
        
    def crawl(self, url):
        response = requests.get(url)
        # executor, mpexecutor = self['executor', 'mpexecutor']
        markdown_future = self.mpexecutor.submit(self.transform_to_markdown, response, url)
        match_protocol = re.match('^https?://')
        if match_protocol:
            url_for_file = url[match_protocol.end:len(url)-1]
        else:
            url_for_file = url
        
        # when writing to file
        persistence_future = self.executor.submit(self.write_to_supabase, markdown_future.result(), "", url_for_file)

        # when writing to supabase
        # persistence_future = executor.submit(self.write_to_supabase, markdown_future.result(), "", url_for_file)

def main(url=None):
    crawler = Crawler("https://www.brex.com")
    crawler.start_crawling()

if __name__ == "__main__":
    main()
