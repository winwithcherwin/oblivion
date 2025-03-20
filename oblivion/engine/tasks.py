#from oblivion.celery_app import app
from celery import shared_task

@shared_task
def add(x, y):
  return x + y

@shared_task
def subtract(x, y):
  return x - y

@shared_task
def aggregate_results(results):
  return sum(results)
