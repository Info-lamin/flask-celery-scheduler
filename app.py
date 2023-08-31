from flask import Flask, request, abort
from celery import Celery
import requests
import datetime
import pytz
import time

app = Flask(__name__)

celery = Celery(
    app.name, 
    broker='redis://host.docker.internal:6379/0', 
    backend='celery.backends.mongodb.MongoDBBackend',
    broker_pool_limit=None
)
celery.conf.update(
    app.config,
    result_backend='mongodb://host.docker.internal:27017/',
    # result_backend_options={
    #     'database': 'celery_scheduler',      # not working
    #     'taskmeta_collection': 'taskmeta_collection',
    # }
)
celery.conf.timezone = 'Asia/Kolkata'


@celery.task
def trigger_webhook(url, security_code, payload):
    for i in range(5):
        response = requests.post(
            url = url,
            headers = {
                'Authorization': security_code
            },
            json = payload,
            verify=False
        )
        if response.status_code != 200:
            time.sleep(30)
            continue
        return response.status_code
    raise RuntimeError('Maximum retries occured')


@app.route('/webhook', methods=['POST'])
def receive_webhook():
    # Header Authorization abcdefgh
    # Body security_code, url, timestamp, (payload, headers)
    if request.headers.get('Authorization') == 'abcdefgh':
        try:
            timestamp = request.json.get('timestamp', datetime.datetime.now().timestamp())
            url = request.json.get('url', None)
            security_code = request.json.get('security_code', None)
            payload = request.json.get('payload', {})
            if url is not None and security_code is not None:
                schedule_time = datetime.datetime.fromtimestamp(float(timestamp), pytz.timezone('Asia/Kolkata')).isoformat()
                trigger_webhook.apply_async(args=(url, security_code, payload), eta=schedule_time)
                return 'ok'
        except:
            pass
    abort(404)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5022)
