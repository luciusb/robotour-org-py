from requests import post
uri='http://localhost:8888/results'
uri='http://192.168.43.1:8888/results'
h = post(uri, data=open('results.txt','rb'))
print(h)

