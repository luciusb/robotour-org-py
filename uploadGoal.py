from requests import post
uri='http://localhost:8888/results'
uri='http://192.168.43.1:8888/rounds'
h = post(uri, data=open('rounds.txt','rb'))
print(h)

