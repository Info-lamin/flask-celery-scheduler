from flask import Flask, request, abort, render_template, jsonify
from celery.result import AsyncResult
from celery import Celery
import requests
import datetime
import pymongo
import pytz
import time

app = Flask(__name__)
MONGO_URI = 'mongodb://host.docker.internal:27017/'
MONGO_URI = 'mongodb://127.0.0.1:27017/'
CELERY_TASKMETA = pymongo.MongoClient(MONGO_URI)['celery']['celery_taskmeta']
API_ACCOUNTS = [
    {
        'api_key': 'qwerty'
    }
]

celery = Celery(
    app.name, 
    broker='redis://host.docker.internal:6379/0', 
    backend='celery.backends.mongodb.MongoDBBackend',
    broker_pool_limit=None
)
celery.conf.update(
    app.config,
    result_backend=MONGO_URI,
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


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/read', methods=['POST', 'GET'])
def read():
    for api_account in API_ACCOUNTS:
        if api_account['api_key'] == request.headers.get('Authorization') or api_account['api_key'] == request.args.get('Authorization'):
            tasks = list(CELERY_TASKMETA.find())
            return jsonify(tasks)
    return jsonify({
        'success': False,
        'message': 'Invalid api_key is provided'
    })


@app.route('/create', methods=['POST'])
def create_task():
    for api_account in API_ACCOUNTS:
        if api_account['api_key'] == request.headers.get('Authorization'):
            timestamp = request.json.get('timestamp', datetime.datetime.now().timestamp())
            url = request.json.get('url', None)
            if url is None:
                return jsonify({
                    'success': False,
                    'message': 'url is not passed and it is a required parameter'
                })
            payload = request.json.get('payload', {})
            security_code = request.json.get('security_code', None)
            if security_code is None:
                return jsonify({
                    'success': False,
                    'message': 'security_code is not passed and it is a required parameter'
                })
            schedule_time = datetime.datetime.fromtimestamp(float(timestamp), pytz.timezone('Asia/Kolkata')).isoformat()
            my_task = trigger_webhook.apply_async(args=(url, payload, security_code), eta=schedule_time)
            return jsonify({
                'success': True,
                'task_id': my_task.id
            })
    return jsonify({
        'success': False,
        'message': 'Invalid api_key is provided'
    })


@app.route('/delete', methods=['POST'])
def delete_task():
    for api_account in API_ACCOUNTS:
        if api_account['api_key'] == request.headers.get('Authorization'):
            task_id = request.json.get()
            my_task = AsyncResult(task_id, app=celery)
            my_task.revoke(terminate=True)
    return jsonify({
        'success': False,
        'message': 'Invalid api_key is provided'
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5022)
