import os
import pytz
import time
import dotenv
import pymongo
import datetime
import requests
from flask import Flask
from flask import jsonify
from flask import request
from flask import render_template
from celery import Celery
from celery.contrib.abortable import AbortableTask

app = Flask(__name__)
dotenv.load_dotenv()
print(os.getenv('API_KEYS', '').split(','))
MONGO_URI = os.getenv('MONGO_URI')
CELERY_TASKMETA = pymongo.MongoClient(MONGO_URI)['celery']['celery_taskmeta']
API_ACCOUNTS = [
    {
        'api_key': key
    } for key in os.getenv('API_KEYS', '').split(',')
]

celery = Celery(
    app.name, 
    broker=os.getenv('REDIS_BROKER_URI'), 
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


@celery.task(bind=True, base=AbortableTask)
def trigger_webhook(self, url, security_code, payload, api_key):
    for _ in range(5):
        try:
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
            return f"{api_key}|||{response.status_code}"
        except:
            pass
    raise RuntimeError('Maximum retries occured')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/read', methods=['POST', 'GET'])
@app.route('/read/<string:task_id>', methods=['POST', 'GET'])
def read(task_id=None):
    for api_account in API_ACCOUNTS:
        if api_account['api_key'] == request.headers.get('Authorization') or api_account['api_key'] == request.args.get('Authorization'):
            if task_id is None:
                tasks = list(CELERY_TASKMETA.find({
                    'result': { 
                        '$regex': f"^{api_account['api_key']}|||"
                    } 
                }))
            else:
                tasks = dict(CELERY_TASKMETA.find_one({'_id': task_id}) or {})
                if tasks == dict():
                    my_task = trigger_webhook.AsyncResult(task_id)
                    tasks = {
                        '_id': task_id,
                        'status': my_task.status
                    }
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
            my_task = trigger_webhook.apply_async(
                args=(url, security_code, payload, api_account['api_key']), 
                eta=schedule_time
            )
            my_task.api_key = api_account['api_key']
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
            task_id = request.json.get('task_id', None)
            if task_id is None:
                return jsonify({
                    'success': False,
                    'message': 'task_id is not passed and it is a required parameter'
                })
            my_task = trigger_webhook.AsyncResult(task_id)
            my_task.abort()
            return jsonify({
                'success': True,
                'task_id': task_id
            })
    return jsonify({
        'success': False,
        'message': 'Invalid api_key is provided'
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5022)
