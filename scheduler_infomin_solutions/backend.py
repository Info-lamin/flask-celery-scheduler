import connection
from celery.backends.base import BaseBackend

class MyResultBackend(BaseBackend):
    def __init__(self, *args, **kwargs):
        # Your custom backend initialization code here
        self.Session = connection.Session
        self.thread_safe = True
        self.url = ''

    def store_result(self, task_id, result, state, *args, **kwargs):
        # Your result storage logic here
        with self.Session() as session:
            try:
                api_key = kwargs['request'].args[3]
                api_account = session.query(connection.ApiAccount).filter_by(api_key=api_key).first()
                result_obj = connection.Task(task_id=task_id, result=str(result), state=state, api_account=api_account)
                session.add(result_obj)
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

    def get_result(self, task_id, *args, **kwargs):
        # Your result retrieval logic here
        with self.Session() as session:
            result = session.query(connection.Task.result).filter_by(task_id=task_id).first()
            return result[0] if result else None
