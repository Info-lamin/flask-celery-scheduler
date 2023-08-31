# flask-celery-scheduler

### *IMPORTANT
- MongoDB instance should be running in port 27017
- Redis instance should be running in port 6379

---

**flask-celery-scheduler** is a Flask REST API website that enables scheduling HTTP requests at specific times using Celery.

---

There are 3 endpoints in the application:

- **/** (root) - This endpoint provides a simple documentation of the application.

- **/create** - This endpoint is used to create and schedule a task. It requires the following JSON payload:

  ```json
  {
      "api_key": "<API_KEY>",
      "timestamp": "1234567890",  // Task will be scheduled to this timestamp.
      "url": "https://www.example.com",  // This url will get a POST request when triggered.
      "payload": {},  // This will the json data sent to the POST request.
      "security_code": "abcde"  // used to verify request. It will be received in headers Authorization .
  }
   ```
  Response:

  ```json
  {
      "success": <status>  // true or false (boolean)
      "task_id": "<task_id>"
  }
   ```
  **Note :**
  - If timestamp is not provided then the task will be added to queue and executed imediately.
  - payload is an optional parameter
  - timestamp and security_code is a required parameter
  - security_code will be passed to the url when triggered in its headers as Authorization

- **/delete** - This endpoint is used to create and schedule a task. It requires the following JSON payload:

  ```json
  {
      "api_key": "<API_KEY>",
      "task_id": "<task_id>"
  }
   ```
  Response:

  ```json
  {
      "success": <status>  // true or false (boolean)
      "task_id": "<task_id>"
  }
   ```
