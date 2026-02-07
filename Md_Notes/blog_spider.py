from unittest import result
import requests
from bs4 import BeautifulSoup

urls = [
    f"https://www.cnblogs.com/#p{page}"
    for page in range(1, 50 + 1)
]

def craw(url):
    r = requests.get(url)
    # print(url,len(r.text))
    return r.text

def parse(html):
    soup = BeautifulSoup(html,"html.parser")
    links = soup.find_all("a",class_="post-item-title")
    return [(link["href"],link.get_text()) for link in links]


# try:
#     [craw(url) for url in urls] 
# except KeyboardInterrupt:
#     print(f'异常退出')

# craw(urls[0])  

if __name__ == "__main__":
    for result in parse(craw(urls[2])):
        print(result)