# Use the official AWS Lambda Python image
FROM public.ecr.aws/lambda/python:3.11

# Copy the WORKER specific requirements
COPY requirements-worker.txt ${LAMBDA_TASK_ROOT}/requirements.txt

# Install dependencies (This will be super fast now)
RUN pip install -r requirements.txt

# Copy the code
COPY etl_worker.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "etl_worker.handler" ]