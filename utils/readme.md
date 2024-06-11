# How to run

`pip install -r requirements.txt`

`uvicorn main:app`

# How to use

http://127.0.0.1:8000/docs

## new thread
Use `/v1/threads` to create a new thread

```commandline
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/threads' \
  -H 'accept: application/json' \
  -d ''
```

There will be new id like `thread_lx6SUUrWTIb9PjiT7fmPlzXX` in response

## send message with incomplete information

```commandline
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/threads/thread_lx6SUUrWTIb9PjiT7fmPlzQj/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "What weather will it be tomorrow?",
  "just_one_more_field": "test"
}'
```

You should get a response like "Please, provide a city"

## Send message with complete information:
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/threads/thread_lx6SUUrWTIb9PjiT7fmPlzQj/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "What weather is it now in New York?",
  "just_one_more_field": "test"
}'
