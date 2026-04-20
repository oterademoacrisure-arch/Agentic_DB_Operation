import requests
import json

url = 'http://localhost:8000/api/chat'
data = {'message': "SELECT * FROM sales_data WHERE product_code = 'PROD-250';"}

try:
    response = requests.post(url, json=data, stream=True)
    print('Status Code:', response.status_code)
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))
    else:
        print('Error:', response.text)
except Exception as e:
    print('Exception:', e)