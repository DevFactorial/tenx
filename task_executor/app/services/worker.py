import json
import subprocess
from app.core.celery_app import celery_app
from app.integrations.api_publisher import APIPublisher
from app.schemas.task import WorkflowTaskUpdate, TaskStatus
import structlog

logger = structlog.get_logger()

@celery_app.task(bind=True, name="worker.execute_script",
                 autoretry_for=(Exception,), 
                 retry_kwargs={'max_retries': 3},
                 retry_backoff=True)
def execute_python_script(self, script_path: str, params: dict, execution_id: str, task_id: str):
    # This runs inside the worker process, not the API process
    result_status = TaskStatus.FAILED
    output_data = None
    error_message = None
    process = None
    log = logger.bind(
            workflow_execution_id = execution_id, 
            workflow_task_id = task_id
        )
    try:
        log.info("Starting script execution")
        process = subprocess.Popen(
            ["python3", script_path, json.dumps(params)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Set a hard timeout (e.g., 5 minutes) to prevent hanging tasks
        stdout, stderr = process.communicate(timeout=300)
        log.info(f"Completed script execution {process.returncode}")
        
        if process.returncode == 0:
            result_status = TaskStatus.COMPLETED
            try:
                output_data = json.loads(stdout.strip())
            except json.JSONDecodeError:
                result_status = TaskStatus.FAILED
                error_message = "Script output was not valid JSON."
        else:
            error_message = stderr.strip() or "Process exited with non-zero code."

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
            process.wait()
        error_message = "Task timed out after 300 seconds."
    except Exception as e:
        error_message = f"Internal Worker Error: {str(e)}"
        # If it's a transient system error, we trigger a Celery retry
        raise self.retry(exc=e)
    finally:
        log.info(f"Completed script execution code: {process.returncode} error_message {error_message} status {result_status}")
        # 2. Construct the Callback Payload
        callback_payload = WorkflowTaskUpdate(
                           status= result_status, 
                           output = output_data,
                           error = error_message)
        
        callback_client = APIPublisher()

        # Invoke the API
        try:
            callback_client.send_callback(
                    workflow_execution_id=execution_id,
                    workflow_task_id=task_id,
                    payload=callback_payload
                    )
            logger.info("callback_sent", execution_id=execution_id, status=result_status)
        except Exception as e:
            logger.error("callback_failed", error=str(e), execution_id=execution_id)
            # Optional: Retry the task specifically if the callback fails
            raise self.retry(exc=e)
        
    #Serialize to json, so that celery will save to redis
    return callback_payload.model_dump(mode='json')
    