import blog_spider
import threading
import time

def single_thread():
    print("multi_thread begin")
    for url in blog_spider.urls:
        blog_spider.craw(url)

    print("multi_thread end")

def multi_thread():
    print("multi_thread begin")
    threads = []
    for url in blog_spider.urls:
        threads.append(
            threading.Thread(target=blog_spider.craw,args=(url,))
        )

    for thread in threads:
        thread.start(
        )

    for thread in threads:
        thread.join()

    print("multi_thread end")

if __name__ == "__main__":
    start_time = time.time()
    single_thread()
    end_time = time.time()
    print('single thread cost :', end_time - start_time, 'seconds')

    start_time = time.time()
    multi_thread()
    end_time = time.time()
    print('multi thread cost :', end_time - start_time, 'seconds')
