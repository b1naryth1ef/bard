from datetime import timedelta, datetime

from peewee import CharField, DateTimeField

from bard.models import BaseModel


@BaseModel.register
class Task(BaseModel):
    name = CharField(unique=True)
    last_run = DateTimeField()

    @classmethod
    def get_next_run(cls, name, cadence):
        try:
            task = Task.get(name=name)
            return task.last_run + timedelta(seconds=cadence)
        except Task.DoesNotExist:
            return datetime.utcnow()

    @classmethod
    def save_run(cls, name):
        Task.replace(name=name, last_run=datetime.utcnow()).execute()
